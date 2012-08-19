#!/usr/bin/env python
import json
import pika
import requests
import threading
import logging

from django.utils import timezone
from django.conf import settings

from queue.models import Submission

log = logging.getLogger(__name__)


def clean_up_submission(submission):
    '''
    TODO: Delete files on S3
    '''
    return


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
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=settings.RABBIT_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)

    # qitem is the item from the queue
    method, header, qitem = channel.basic_get(queue=queue_name)

    if method.NAME == 'Basic.GetEmpty':  # Got nothing
        connection.close()
        return (False, '')
    else:
        channel.basic_ack(method.delivery_tag)
        connection.close()
        return (True, qitem)


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
    (success, lms_reply) = _http_post(lms_callback_url, payload)

    if not success:
        log.error("Unable to return to LMS: lms_callback_url: {0}, payload: {1}, lms_reply: {2}".format(lms_callback_url, payload, lms_reply)) 

    return success


def _http_post(url, data):
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
        r = requests.post(url, data=data, auth=auth)
    except requests.exceptions.ConnectionError:
        return (False, 'cannot connect to server')

    if r.status_code not in [200]:
        return (False, 'unexpected HTTP status code [%d]' % r.status_code)
    return (True, r.text)


class SingleChannel(threading.Thread):
    '''
    Encapsulation of a single RabbitMQ queue listener
    '''
    def __init__(self, workerID, workerURL, queue_name):
        threading.Thread.__init__(self)
        self.workerID = workerID
        self.workerURL = workerURL
        self.queue_name = str(queue_name)  # Important, queue_name must be str, not unicode!

    def run(self):
        log.info(" [{id}-{qname}] Starting consumer for queue '{qname}' using {push_url}".format(
            id=self.workerID,
            qname=self.queue_name,
            push_url=self.workerURL
        ))
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=settings.RABBIT_HOST))
        channel = connection.channel()
        channel.queue_declare(queue=self.queue_name, durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(self.consumer_callback,
                              queue=self.queue_name)
        channel.start_consuming()

    def consumer_callback(self, ch, method, properties, qitem):

        submission_id = int(qitem)
        try:
            submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            log.error("Queued pointer refers to nonexistent entry in Submission DB: queue_name: {0}, submission_id: {1}".format(
                self.queue_name,
                submission_id
            ))
            return  # Just move on

        # Deliver job to worker
        payload = {'xqueue_body': submission.xqueue_body,
                   'xqueue_files': submission.s3_urls}

        submission.grader_id = self.workerURL
        submission.push_time = timezone.now()
        (grading_success, grader_reply) = _http_post(self.workerURL, json.dumps(payload))
        submission.return_time = timezone.now()

        if grading_success:
            submission.grader_reply = grader_reply
            submission.lms_ack = post_grade_to_lms(submission.xqueue_header, grader_reply)
        else:
            log.error("Submission {} to grader {} failure: Reply: {}, ".format(submission_id, self.workerURL, grader_reply))
            submission.num_failures += 1

        submission.save()

        # Take item off of queue.
        # TODO: Logic for resubmission when failed
        ch.basic_ack(delivery_tag=method.delivery_tag)
