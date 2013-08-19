import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from boto.s3.connection import S3Connection
from boto.s3.key import Key

from statsd import statsd

from queue.models import Submission, CHARFIELD_LEN_LARGE
from queue.views import compose_reply
from util import *

import queue.producer

log = logging.getLogger(__name__)

@csrf_exempt
@login_required
@statsd.timed('xqueue.lms_interface.submit.time')
@transaction.commit_manually # Needed to explicitly time the writes to DB and the queue
def submit(request):
    '''
    Handle submissions to Xqueue from the LMS
    '''
    if request.method != 'POST':
        transaction.commit()
        return HttpResponse(compose_reply(False, 'Queue requests should use HTTP POST'))
    else:
        # queue_name, xqueue_header, xqueue_body are all serialized
        (request_is_valid, lms_callback_url, queue_name, xqueue_header, xqueue_body) = _is_valid_request(request.POST)

        if not request_is_valid:
            log.error("Invalid queue submission from LMS: lms ip: {0}, request.POST: {1}".format(
                get_request_ip(request),
                request.POST,
            ))
            transaction.commit()
            return HttpResponse(compose_reply(False, 'Queue request has invalid format'))
        else:
            if queue_name not in settings.XQUEUES:
                transaction.commit()
                return HttpResponse(compose_reply(False, "Queue '%s' not found" % queue_name))
            else:
                # Limit DOS attacks by invalidating prior submissions from the
                #   same (user, module-id) pair as encoded in the lms_callback_url
                _invalidate_prior_submissions(lms_callback_url)

                # Check for file uploads
                s3_keys = dict() # For internal Xqueue use
                s3_urls = dict() # For external grader use
                if 'files' in json.loads(request.POST['xqueue_body']):
                    for key, url in json.loads(request.POST['xqueue_body'])['files'].items():
                        s3_keys[key] = key
                        s3_urls[key] = url

                # Track the submission in the Submission database
                submission = Submission(requester_id=get_request_ip(request),
                                        lms_callback_url=lms_callback_url,
                                        queue_name=queue_name,
                                        xqueue_header=xqueue_header,
                                        xqueue_body=xqueue_body,
                                        s3_urls=json.dumps(s3_urls),
                                        s3_keys=json.dumps(s3_keys))
                submission.save()
                transaction.commit() # Explicit commit to DB before inserting submission.id into queue

                qitem  = str(submission.id) # Submit the Submission pointer to queue
                qcount = queue.producer.push_to_queue(queue_name, qitem)

                # For a successful submission, return the count of prior items
                return HttpResponse(compose_reply(success=True, content="%d" % qcount))

@transaction.commit_manually
def _invalidate_prior_submissions(lms_callback_url):
    '''
    Check the Submission DB to invalidate prior submissions from the same
        (user, module-id). This function relies on the fact that lms_callback_url
        takes the form: /path/to/callback/<user>/<id>/...
    '''
    prior_submissions = Submission.objects.filter(lms_callback_url=lms_callback_url, retired=False)
    prior_submissions.update(retired=True)
    transaction.commit()


def _is_valid_request(xrequest):
    '''
    Check if xrequest is a valid request for Xqueue. Checks:
        1) Presence of 'xqueue_header' and 'xqueue_body'
        2) Presence of specific metadata in 'xqueue_header'
            ['lms_callback_url', 'lms_key', 'queue_name']

    Returns:
        is_valid:         Flag indicating success (Boolean)
        lms_callback_url: Full URL to which queued results should be delivered (string)
        queue_name:       Name of intended queue (string)
        header:           Header portion of xrequest (string)
        body:             Body portion of xrequest (string)
    '''
    fail = (False, '', '', '', '')
    try:
        header = xrequest['xqueue_header']
        body   = xrequest['xqueue_body']
    except (TypeError, KeyError):
        return fail

    try:
        header_dict = json.loads(header)
    except (TypeError, ValueError):
        return fail

    if not isinstance(header_dict, dict):
        return fail

    for tag in ['lms_callback_url', 'lms_key', 'queue_name']:
        if not header_dict.has_key(tag):
            return fail

    queue_name   = str(header_dict['queue_name']) # Important: Queue name must be str!
    lms_callback_url = header_dict['lms_callback_url']

    return (True, lms_callback_url, queue_name, header, body)

