from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from statsd import statsd
import requests

import json
import logging

from queue.models import Submission
from queue.views import XQueueResponse
from util import *

import queue.producer
import queue.consumer

log = logging.getLogger(__name__)

# External pull interface
#    1) get_queuelen
#    2) get_submission
#    3) put_result
#--------------------------------------------------
@login_required
@statsd.timed('xqueue.ext_interface.get_queuelen.time')
def get_queuelen(request):
    '''
    Retrieves the length of queue named by GET['queue_name'].
    If queue_name is invalid or null, returns list of all queue names
    '''
    try:
        queue_name = request.GET['queue_name']
    except KeyError:
        return XQueueResponse(False, "'get_queuelen' must provide parameter 'queue_name'")

    if queue_name in settings.XQUEUES:
        job_count = queue.producer.get_queue_length(queue_name)
        return XQueueResponse(True, job_count)
    else:
        return XQueueResponse(False, 'Valid queue names are: ' + ', '.join(settings.XQUEUES.keys()))

@login_required
@statsd.timed('xqueue.ext_interface.get_submission.time')
def get_submission(request):
    '''
    Retrieve a single submission from queue named by GET['queue_name'].
    '''
    try:
        queue_name = request.GET['queue_name']
    except KeyError:
        return XQueueResponse(False, "'get_submission' must provide parameter 'queue_name'")

    if queue_name not in settings.XQUEUES:
        return XQueueResponse(False, "Queue '%s' not found" % queue_name)
    else:
        # Try to pull a single item from named queue
        blocking = request.GET.get('block') == 'true' and can_block(request)
        got_submission, submission = queue.consumer.get_single_unretired_submission(queue_name, blocking=blocking)

        if not got_submission:
            return XQueueResponse(False, "Queue '%s' is empty" % queue_name)
        else:
            # Collect info on pull event
            grader_id = get_request_ip(request)
            pull_time = timezone.now()

            pullkey = make_hashkey(str(pull_time)+str(submission.id))
            
            submission.grader_id = grader_id
            submission.pull_time = pull_time
            submission.pullkey   = pullkey 
            
            submission.save()

            # Prepare payload to external grader
            ext_header = {'submission_id':submission.id, 'submission_key':pullkey}
            s3_urls = json.loads(submission.s3_urls) if submission.s3_urls else {}

            if "URL_FOR_EXTERNAL_DICTS" in submission.s3_urls:
                url = s3_urls["URL_FOR_EXTERNAL_DICTS"]
                timeout = 2
                try:
                    r = requests.get(url, timeout=timeout)
                    success = True
                except (ConnectionError, Timeout):
                    success = False
                    log.error('Could not fetch uploaded files at %s in timeout=%f' % (url, timeout))
                    return XQueueResponse(False, "Error fetching submission. Please try again." % queue_name)

                if (r.status_code not in [200]) or (not success):
                    log.error('Could not fetch uploaded files at %s. Status code: %d' % (url, r.status_code))
                    return XQueueResponse(False, "Error fetching submission. Please try again." % queue_name)

                xqueue_files = json.dumps(json.loads(r.text)["files"])
            else:
                xqueue_files = submission.s3_urls

            payload = {'xqueue_header': json.dumps(ext_header),
                       'xqueue_body': submission.xqueue_body,
                       'xqueue_files': xqueue_files}

            return XQueueResponse(True,content=json.dumps(payload))

@csrf_exempt
@login_required
@statsd.timed('xqueue.ext_interface.put_result.time')
def put_result(request):
    '''
    Graders post their results here.
    '''
    if request.method != 'POST':
        return XQueueResponse(False, "'put_result' must use HTTP POST")
    else:
        (reply_is_valid, submission_id, submission_key, grader_reply) = _is_valid_reply(request.POST)

        if not reply_is_valid:
            log.error("Invalid reply from pull-grader: grader_id: {0} request.POST: {1}".format(
                get_request_ip(request),
                request.POST,
            ))
            return XQueueResponse(False, 'Incorrect reply format')
        else:
            try:
                submission = Submission.objects.select_for_update().get(id=submission_id)
            except Submission.DoesNotExist:
                log.error("Grader submission_id refers to nonexistent entry in Submission DB: grader: {0}, submission_id: {1}, submission_key: {2}, grader_reply: {3}".format(
                    get_request_ip(request), 
                    submission_id,
                    submission_key,
                    grader_reply
                ))
                return XQueueResponse(False,'Submission does not exist')

            if not submission.pullkey or submission_key != submission.pullkey:
                return XQueueResponse(False,'Incorrect key for submission')

            submission.return_time = timezone.now()
            submission.grader_reply = grader_reply

            # Deliver grading results to LMS
            submission.lms_ack = queue.consumer.post_grade_to_lms(submission.xqueue_header, grader_reply)
            submission.retired = submission.lms_ack

            submission.save()

            return XQueueResponse(success=True, content='')

def _is_valid_reply(external_reply):
    '''
    Check if external reply is in the right format
        1) Presence of 'xqueue_header' and 'xqueue_body'
        2) Presence of specific metadata in 'xqueue_header'
            ['submission_id', 'submission_key']

    Returns:
        is_valid:       Flag indicating success (Boolean)
        submission_id:  Graded submission's database ID in Xqueue (int)
        submission_key: Secret key to match against Xqueue database (string)
        score_msg:      Grading result from external grader (string)
    '''
    fail = (False,-1,'','')
    try:
        header    = external_reply['xqueue_header']
        score_msg = external_reply['xqueue_body']
    except KeyError:
        return fail

    try:
        header_dict = json.loads(header)
    except (TypeError, ValueError):
        return fail

    if not isinstance(header_dict,dict):
        return fail

    for tag in ['submission_id', 'submission_key']:
        if not header_dict.has_key(tag):
            return fail

    submission_id  = int(header_dict['submission_id'])
    submission_key = header_dict['submission_key']
    return (True, submission_id, submission_key, score_msg)
