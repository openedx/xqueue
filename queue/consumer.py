#!/usr/bin/env python
import json
import pika
import requests
import multiprocessing
import logging
import time

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from requests.exceptions import ConnectionError, Timeout
from statsd import statsd

from queue.producer import get_queue_length

from queue.models import Submission

log = logging.getLogger(__name__)


def clean_up_submission(submission):
    '''
    TODO: Delete files on S3
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
        credentials=credentials, host=settings.RABBIT_HOST))
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

    # This is the only part of the XQueue that assumes knowledge of the external
    #   grader message format. TODO: Make the notification message-format agnostic
    msg  = '<div class="capa_alert">'
    msg += 'Your submission could not be graded. '
    msg += 'Please recheck your submission and try again. '
    msg += 'If the problem persists, please notify the course staff.'
    msg += '</div>'
    failure_msg = { 'correct': None,
                    'score': 0,
                    'msg': msg }
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
        (success, lms_reply) = _http_post(lms_callback_url, payload, settings.REQUESTS_TIMEOUT)
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


class SingleChannel(multiprocessing.Process):
    '''
    Encapsulation of a single RabbitMQ listener that listens on multiple queues
    '''
    def __init__(self, worker_id, queues):
        super(self, SingleChannel).__init__(self)
        self.worker_id = worker_id
        self.queues = queues

    def run(self):
        log.info(" [{id}] Starting consumer for queues {queues}".format(
            id=self.worker_id,
            queues=self.queues,
        ))
        credentials = pika.PlainCredentials(settings.RABBITMQ_USER,
                                                settings.RABBITMQ_PASS)
        connection = pika.BlockingConnection(
                        pika.ConnectionParameters(heartbeat_interval=5,
                            credentials=credentials, host=settings.RABBIT_HOST))
        channel = connection.channel()
        channel.basic_qos(prefetch_count=1)
        for queue in self.queues:
            channel.queue_declare(queue=queue.queue_name, durable=True)
            channel.basic_consume(queue.consumer_callback,
                                  queue=queue.queue_name)
        channel.start_consuming()


class QueueConsumer(object):
    """
    Encapsulates a queue that work should be pulled from
    """
    def __init__(self, worker_url, queue_name):
        self.worker_url = worker_url
        self.queue_name = str(queue_name)

    # By default, Django wraps each view code as a DB transaction. We don't want this behavior for the
    #   consumer, since it may be the case that a queued ticket arrives at the consumer before the
    #   corresponding DB row has been written and closed. In such cases, we want the subsequent accesses
    #   to the DB (in the same view) to be sensitive to concurrent updates to the DB.
    #
    # We tried to get rid of this and ended up with something that worked on staging but not on prod.
    # SO BE VERY CAREFUL ABOUT TOUCHING THIS PART OF THE CODE...
    @transaction.commit_manually
    def consumer_callback(self, ch, method, properties, qitem):

        submission_id = int(qitem)

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

        if submission == None:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            statsd.increment('xqueue.consumer.consumer_callback.submission_does_not_exist',
                             tags=['queue:{0}'.format(self.queue_name)])

            log.error("Queued pointer refers to nonexistent entry in Submission DB: queue_name: {0}, submission_id: {1}".format(
                self.queue_name,
                submission_id
            ))
            # Don't leave without closing the transaction
            transaction.commit()
            return  # Just move on

        # If item has been retired, skip grading
        if not submission.retired:
            # Deliver job to worker
            payload = {'xqueue_body': submission.xqueue_body,
                       'xqueue_files': submission.s3_urls}

            submission.grader_id = self.worker_url
            submission.push_time = timezone.now()
            start = time.time()
            (grading_success, grader_reply) = _http_post(self.worker_url, json.dumps(payload), settings.GRADING_TIMEOUT)
            statsd.histogram('xqueue.consumer.consumer_callback.grading_time', time.time() - start,
                          tags=['queue:{0}'.format(self.queue_name)])

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
                log.error("Submission {} to grader {} failure: Reply: {}, ".format(submission_id, self.worker_url, grader_reply))
                submission.num_failures += 1
                submission.lms_ack = post_failure_to_lms(submission.xqueue_header)

            # NOTE: Retiring pushed submissions after one shot regardless of grading_success
            submission.retired = True

            submission.save()

        # Take item off of queue
        ch.basic_ack(delivery_tag=method.delivery_tag)

        # Close transaction
        transaction.commit()

    def __repr__(self):
        return "QueueConsumer(%r, %r)" % (self.worker_url, self.queue_name)
