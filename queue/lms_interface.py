import json
import logging
import os.path
import queue.producer
from queue.models import CHARFIELD_LEN_LARGE, Submission
from queue.util import get_request_ip, make_hashkey
from queue.views import compose_reply

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from statsd import statsd

log = logging.getLogger(__name__)


@transaction.non_atomic_requests
@csrf_exempt
@login_required
@statsd.timed('xqueue.lms_interface.submit.time')
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
                keys = dict()  # For internal Xqueue use
                urls = dict()  # For external grader use
                for filename in request.FILES.keys():
                    key = make_hashkey(xqueue_header + filename)
                    url = _upload(request.FILES[filename], queue_name, key)
                    keys.update({filename: key})
                    urls.update({filename: url})

                urls_json = json.dumps(urls)
                keys_json = json.dumps(keys)

                if len(urls_json) > CHARFIELD_LEN_LARGE:
                    key = make_hashkey(xqueue_header + json.dumps(request.FILES.keys()))
                    url = _upload_file_dict(urls, keys, queue_name, key)
                    keys = {"KEY_FOR_EXTERNAL_DICTS": key}
                    urls = {"URL_FOR_EXTERNAL_DICTS": url}
                    urls_json = json.dumps(urls)
                    keys_json = json.dumps(keys)

                # Track the submission in the Submission database
                submission = Submission(requester_id=get_request_ip(request),
                                        lms_callback_url=lms_callback_url[:128],
                                        queue_name=queue_name,
                                        xqueue_header=xqueue_header,
                                        xqueue_body=xqueue_body,
                                        s3_urls=urls_json,
                                        s3_keys=keys_json)
                submission.save()
                transaction.commit()  # Explicit commit to DB before inserting submission.id into queue

                qcount = queue.producer.get_queue_length(queue_name)

                # For a successful submission, return the count of prior items
                return HttpResponse(compose_reply(success=True, content="%d" % qcount))


@transaction.atomic
def _invalidate_prior_submissions(lms_callback_url):
    '''
    Check the Submission DB to invalidate prior submissions from the same
        (user, module-id). This function relies on the fact that lms_callback_url
        takes the form: /path/to/callback/<user>/<id>/...
    '''
    prior_submissions = Submission.objects.filter(lms_callback_url=lms_callback_url[:128], retired=False)
    prior_submissions.update(retired=True)


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
        body = xrequest['xqueue_body']
    except (TypeError, KeyError):
        return fail

    try:
        header_dict = json.loads(header)
    except (TypeError, ValueError):
        return fail

    if not isinstance(header_dict, dict):
        return fail

    for tag in ['lms_callback_url', 'lms_key', 'queue_name']:
        if tag not in header_dict:
            return fail

    queue_name = str(header_dict['queue_name'])  # Important: Queue name must be str!
    lms_callback_url = header_dict['lms_callback_url']

    return (True, lms_callback_url, queue_name, header, body)


def _upload_file_dict(file_dict, key_dict, path, name):
    '''
    Upload dictionaries of filenames to urls (and filenames to keys) using the
    provided keyname.
    This is useful because the s3_files column on submissions is currently too
    small.

    Returns:
        URL to access uploaded list
    '''
    data = {}
    data['files'] = file_dict
    data['keys'] = key_dict

    full_path = os.path.join(path, name)
    buff = ContentFile(json.dumps(data))
    default_storage.save(full_path, buff)
    return default_storage.url(full_path)


@statsd.timed('xqueue.lms_interface.upload.time')
def _upload(file_to_upload, path, name):
    '''
    Upload file using the provided keyname.

    Returns:
        URL to access uploaded file
    '''
    full_path = os.path.join(path, name)
    default_storage.save(full_path, file_to_upload)
    return default_storage.url(full_path)
