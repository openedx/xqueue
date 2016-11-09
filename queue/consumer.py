#!/usr/bin/env python
import json
import logging
import requests
import multiprocessing
import threading
import time
import itertools

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.db import connection as db_connection

import pika
from pika.exceptions import AMQPConnectionError
from statsd import statsd
from requests.exceptions import ConnectionError, Timeout

from queue.producer import get_queue_length
from queue.models import Submission


log = logging.getLogger(__name__)


class FailOnDisconnectError(Exception):
    '''
    An error we intentionally throw when a disconnect happens, to force the
    worker to die and be respawned. Trying to manually reconnect the same
    process is somewhat strange according to Pika docs:

    https://pika.readthedocs.org/en/0.9.13/examples/asynchronous_consumer_example.html

    (Note the ioloop.start() inside other ioloop.start()).

    Instead of dealing with that, we let the worker die, and then let the
    monitor restart it.
    '''


def clean_up_submission(submission):
    '''
    TODO: Delete files on storage backend
    '''
    return


def get_single_unretired_submission(queue_name):
    '''
    Retrieve a single unretired queued item, if one exists, from the named queue

    Returns (success, submission):
        success:    Flag whether retrieval is successful (Boolean)
                    If no unretired item in the queue, return False
        submission: A single submission from the queue, guaranteed to be unretired
    '''
    items_in_queue = True
    while items_in_queue:
        # Try to pull out a single submission from the queue, which may or may not be retired
        (items_in_queue, qitem) = get_single_qitem(queue_name)
        if not items_in_queue: # No more submissions to consider
            return (False, '')

        submission_id = int(qitem)
        try:
            submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            log.error("Queued pointer refers to nonexistent entry in Submission DB: queue_name: {0}, submission_id: {1}".format(
                queue_name,
                submission_id
            ))
            continue # Just move on

        if not submission.retired:
            return (True, submission)


def get_single_qitem(queue_name):
    '''
    Retrieve a single queued item, if one exists, from the named queue

    Returns (success, qitem):
        success: Flag whether retrieval is successful (Boolean)
                 If no items in the queue, then return False
        qitem:   Retrieved item
    '''
    queue_name = str(queue_name)

    # Pull a single submission (if one exists) from the named queue
    credentials = pika.PlainCredentials(settings.RABBITMQ_USER,
                                        settings.RABBITMQ_PASS)

    connection = pika.BlockingConnection(pika.ConnectionParameters(
        heartbeat_interval=5,
        credentials=credentials,
        host=settings.RABBIT_HOST,
        port=settings.RABBIT_PORT,
        virtual_host=settings.RABBIT_VHOST,
        ssl=settings.RABBIT_TLS))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)

    # qitem is the item from the queue
    method, header, qitem = channel.basic_get(queue=queue_name)

    if method is None or method.NAME == 'Basic.GetEmpty':  # Got nothing
        connection.close()
        return (False, '')
    else:
        channel.basic_ack(method.delivery_tag)
        connection.close()
        statsd.increment('xqueue.consumer.get_single_qitem',
                         tags=['queue:{0}'.format(queue_name)])
        return (True, qitem)


def post_failure_to_lms(header):
    '''
    Send notification to the LMS (and the student) that the submission has failed,
        and that the problem should be resubmitted
    '''

    # This is the only part of the XQueue that assumes knowledge of
    # the external grader message format.
    # TODO: Make the notification message-format agnostic
    msg = '<div class="capa_alert">'
    msg += 'Your submission could not be graded. '
    msg += 'Please recheck your submission and try again. '
    msg += 'If the problem persists, please notify the course staff.'
    msg += '</div>'
    failure_msg = {'correct': None,
                   'score': 0,
                   'msg': msg}
    statsd.increment('xqueue.consumer.post_failure_to_lms')
    return post_grade_to_lms(header, json.dumps(failure_msg))


def post_grade_to_lms(header, body):
    '''
    Send grading results back to LMS
        header:  JSON-serialized xqueue_header (string)
        body:    grader reply (string)

    Returns:
        success: Flag indicating successful exchange (Boolean)
    '''
    header_dict = json.loads(header)
    lms_callback_url = header_dict['lms_callback_url']

    payload = {'xqueue_header': header, 'xqueue_body': body}

    # Quick kludge retries to fix prod problem with 6.00x push graders. We're
    # seeing abrupt disconnects when servers are taken out of the ELB, causing
    # in flight lms_ack requests to fail. This just tries five times before
    # giving up.
    attempts = 0
    success = False
    while (not success) and attempts < 5:
        (success, lms_reply) = _http_post(lms_callback_url,
                                          payload,
                                          settings.REQUESTS_TIMEOUT)
        attempts += 1

    if success:
        statsd.increment('xqueue.consumer.post_grade_to_lms.success')
    else:
        log.error("Unable to return to LMS: lms_callback_url: {0}, payload: {1}, lms_reply: {2}".format(lms_callback_url, payload, lms_reply))
        statsd.increment('xqueue.consumer.post_grade_to_lms.failure')

    return success


def _http_post(url, data, timeout):
    '''
    Contact external grader server, but fail gently.

    Returns (success, msg), where:
        success: Flag indicating successful exchange (Boolean)
        msg: Accompanying message; Grader reply when successful (string)
    '''
    if settings.REQUESTS_BASIC_AUTH is not None:
        auth = requests.auth.HTTPBasicAuth(*settings.REQUESTS_BASIC_AUTH)
    else:
        auth = None

    try:
        r = requests.post(url, data=data, auth=auth, timeout=timeout, verify=False)
    except (ConnectionError, Timeout):
        log.error('Could not connect to server at %s in timeout=%f' % (url, timeout))
        return (False, 'cannot connect to server')

    if r.status_code not in [200]:
        log.error('Server %s returned status_code=%d' % (url, r.status_code))
        return (False, 'unexpected HTTP status code [%d]' % r.status_code)

    return (True, r.text)


class Worker(multiprocessing.Process):
    """Encapsulation of a single RabbitMQ listener that listens on a queue
    """
    counter = itertools.count()

    def __init__(self, queue_name, worker_url):
        super(Worker, self).__init__()

        # there seems to be an issue with db connections and
        # multiprocessing. since we are not using the connection in
        # the main worker thread, lets close it hoping that it does
        # not get shared with the children threads.
        db_connection.close()

        self.retries = 0
        self.id = next(self.counter)
        self.queue_name = queue_name
        self.worker_url = worker_url

        credentials = pika.PlainCredentials(settings.RABBITMQ_USER,
                                            settings.RABBITMQ_PASS)

        self.parameters = pika.ConnectionParameters(heartbeat_interval=5,
                                                    credentials=credentials,
                                                    host=settings.RABBIT_HOST,
                                                    port=settings.RABBIT_PORT,
                                                    virtual_host=settings.RABBIT_VHOST,
                                                    ssl=settings.RABBIT_TLS)
        self.channel = None
        self.connection = None

    def connect(self):
        return pika.SelectConnection(self.parameters, self.on_connected)

    def on_connected(self, connection):
        # Register callback invoked when the connection is lost unexpectedly
        self.connection.add_on_close_callback(self.on_connection_closed)

        self.connection.channel(self.on_channel_open)

        # Set the retires attempts to Zero
        self.retries = 0

    def on_connection_closed(self, connection, reply_code, reply_text):
        """Invoked when the connection is closed unexpectedly."""

        log.warning('Connection closed, trying to reconnect: ({0}) {1}'.format(
            reply_code,
            reply_text,
        ))

        # Reconnect logic is odd with pika, and a simple self.connect() doesn't
        # seem to work here. So instead of that, we'll just throw an exception,
        # causing this worker process to end and the monitor will then spawn a
        # new process.
        raise FailOnDisconnectError(
            "Reply code: {}; Reply text: {}".format(reply_code, reply_text)
        )

    def on_channel_open(self, channel):
        self.channel = channel

        # The prefetch count determines how many messages will be
        # fetched by pika for processing. New messages will only be
        # fetched after the ones that are being processed have been
        # acknowledged. Because we are using a thread to process each
        # message, the prefecth count also determines the maximum
        # number of processing threads running at the same time.
        prefetch_count = settings.XQUEUE_WORKERS_PER_QUEUE
        channel.basic_qos(prefetch_count=prefetch_count)

        channel.queue_declare(queue=self.queue_name,
                              durable=True,
                              callback=self.on_queue_declared)

    def on_queue_declared(self, frame):
        self.channel.basic_consume(self._callback, queue=self.queue_name)

    def run(self):
        log.info(" [{id}] Starting consumer for queue {queue}".format(
            id=self.id,
            queue=self.queue_name,
        ))

        while True:
            try:
                log.info("[{id}] - Attempting to establish a connection for queue {queue}".format(
                    id=self.id,
                    queue=self.queue_name,
                ))
                self.connection = self.connect()
                self.connection.ioloop.start()
            except AMQPConnectionError as ex:
                self.retries += 1
                if self.retries >= settings.RETRY_MAX_ATTEMPTS:
                    log.error("[{id}] Consumer for queue {queue} connection error: {err}".format(
                        id=self.id,
                        queue=self.queue_name,
                        err=ex
                    ))
                    raise
                log.info("[{id}] - Retrying connection, attempt # {attempt} of {max_attempts} of MAX".format(
                    id=self.id,
                    attempt=self.retries,
                    max_attempts=settings.RETRY_MAX_ATTEMPTS
                ))
                if self.retries > 1:
                    time.sleep(settings.RETRY_TIMEOUT)
                continue
            else:
                # Log that the worker exited without an exception
                log.info(" [{id}] Consumer for queue {queue} is exiting normally...".format(
                    id=self.id,
                    queue=self.queue_name
                ))
                break
            finally:
                # Log that the worker stopped
                log.info(" [{id}] Consumer for queue {queue} stopped".format(
                    id=self.id,
                    queue=self.queue_name
                ))

        # TODO [rocha] make to to finish all  submissions before exiting

    def stop(self):
        '''
        Stop the worker from processing messages
        '''
        self.connection.close()

    def _callback(self, channel, method, properties, qitem):
        def on_done():
            # Acknowledge the delivery of the message in the ioloop of
            # the current connection. basic_ack is not thread safe,
            # and calling it outside of the ioloop thread will cause
            # an error, and the message will never be acknowledged.
            acknowledge = lambda: channel.basic_ack(delivery_tag=method.delivery_tag)
            self.connection.add_timeout(0, acknowledge)

            # close the db connection manually.
            db_connection.close()

        submission_id = int(qitem)

        # process the submission in a different thread to avoid
        # blocking pika's ioloop, which can cause disconnects and
        # other errors
        thread = threading.Thread(target=self._process, args=(submission_id,
                                                              on_done))
        thread.daemon = True
        thread.start()

    @transaction.atomic
    def _process(self, submission_id, on_done):
        log.info("Processing submission from queue_name: {0}, submission_id: {1}".format(self.queue_name, submission_id))
        try:
            with transaction.atomic():
                submission = self._get_submission(submission_id)

                if submission is None:
                    statsd.increment('xqueue.consumer.consumer_callback.submission_does_not_exist',
                                     tags=['queue:{0}'.format(self.queue_name)])
                    log.error("Queued pointer refers to nonexistent entry in Submission DB: queue_name: {0}, submission_id: {1}".format(
                        self.queue_name,
                        submission_id
                    ))

                # if item has been retired, skip grading
                if submission and not submission.retired:
                    self._deliver_submission(submission)

        except Exception as e:
            # catch and acknowledge the message if something goes wrong
            statsd.increment('xqueue.consumer.consumer_callback.unknown_error',
                             tags=['queue:{0}'.format(self.queue_name)])
            log.error("Error processing submission_id: {0} on queue_name: {1}, {2}" .format(
                submission_id,
                self.queue_name,
                e,
            ))
        finally:
            # acknowledge that the message was processed
            on_done()

    def _get_submission(self, submission_id):
        submission = None

        for i in range(settings.DB_RETRIES):
            try:
                submission = Submission.objects.get(id=submission_id)
            except Submission.DoesNotExist:
                # Need to terminate current transaction, allows next queryset to view fresh version of DB
                transaction.commit()
                log.info("Queued pointer refers to nonexistent entry in Submission DB on {0}-th lookup: queue_name: {1}, submission_id: {2}".format(
                    i, self.queue_name, submission_id))
                # Wait in case the DB hasn't been updated yet
                time.sleep(settings.DB_WAITTIME)
                continue
            else:
                break

        return submission

    def _deliver_submission(self, submission):
        payload = {'xqueue_body': submission.xqueue_body,
                   'xqueue_files': submission.urls}

        submission.grader_id = self.worker_url
        submission.push_time = timezone.now()
        start = time.time()
        (grading_success, grader_reply) = _http_post(self.worker_url, json.dumps(payload), settings.GRADING_TIMEOUT)
        grading_time = time.time() - start
        statsd.histogram('xqueue.consumer.consumer_callback.grading_time', grading_time,
                         tags=['queue:{0}'.format(self.queue_name)])

        if grading_time > settings.GRADING_TIMEOUT:
            log.error("Grading time above {} for submission. grading_time: {}s body: {} files: {}".format(settings.GRADING_TIMEOUT,
                      grading_time, submission.xqueue_body, submission.urls))

        job_count = get_queue_length(self.queue_name)
        statsd.gauge('xqueue.consumer.consumer_callback.queue_length', job_count,
                     tags=['queue:{0}'.format(self.queue_name)])

        submission.return_time = timezone.now()

        # TODO: For the time being, a submission in a push interface gets one chance at grading,
        #       with no requeuing logic
        if grading_success:
            submission.grader_reply = grader_reply
            submission.lms_ack = post_grade_to_lms(submission.xqueue_header, grader_reply)
        else:
            log.error("Submission {} to grader {} failure: Reply: {}, ".format(submission.id, self.worker_url, grader_reply))
            submission.num_failures += 1
            submission.lms_ack = post_failure_to_lms(submission.xqueue_header)

        # NOTE: retiring pushed submissions after one shot regardless of grading_success
        submission.retired = True

        submission.save()

    def __repr__(self):
        return "Worker (%r, %r)" % (self.worker_url, self.queue_name)
