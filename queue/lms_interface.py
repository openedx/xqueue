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
                s3_keys = dict()  # For internal Xqueue use
                s3_urls = dict()  # For external grader use
                for filename in request.FILES.keys():
                    s3_key = make_hashkey(xqueue_header + filename)
                    s3_url = _upload_to_s3(request.FILES[filename], queue_name, s3_key)
                    s3_keys.update({filename: s3_key})
                    s3_urls.update({filename: s3_url})

                s3_urls_json = json.dumps(s3_urls)
                s3_keys_json = json.dumps(s3_keys)

                if len(s3_urls_json) > CHARFIELD_LEN_LARGE:
                    s3_key = make_hashkey(xqueue_header + json.dumps(request.FILES.keys()))
                    s3_url = _upload_file_dict_to_s3(s3_urls, s3_keys, queue_name, s3_key)
                    s3_keys = {"KEY_FOR_EXTERNAL_DICTS": s3_key}
                    s3_urls = {"URL_FOR_EXTERNAL_DICTS": s3_url}
                    s3_urls_json = json.dumps(s3_urls)
                    s3_keys_json = json.dumps(s3_keys)

                # Track the submission in the Submission database
                submission = Submission(requester_id=get_request_ip(request),
                                        lms_callback_url=lms_callback_url[:128],
                                        queue_name=queue_name,
                                        xqueue_header=xqueue_header,
                                        xqueue_body=xqueue_body,
                                        s3_urls=s3_urls_json,
                                        s3_keys=s3_keys_json)
                submission.save()
                transaction.commit()  # Explicit commit to DB before inserting submission.id into queue

                qitem = str(submission.id)  # Submit the Submission pointer to queue
                qcount = queue.producer.push_to_queue(queue_name, qitem)

                # For a successful submission, return the count of prior items
                return HttpResponse(compose_reply(success=True, content="%d" % qcount))


@transaction.atomic
def _invalidate_prior_submissions(lms_callback_url):
    '''
    Check the Submission DB to invalidate prior submissions from the same
        (user, module-id). This function relies on the fact that lms_callback_url
        takes the form: /path/to/callback/<user>/<id>/...
    '''
    prior_submissions = Submission.objects.filter(lms_callback_url=lms_callback_url, retired=False)
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


def _upload_file_dict_to_s3(file_dict, key_dict, path, name):
    '''
    Upload dictionaries of filenames to S3 urls (and filenames to S3 keys)
    to S3 using provided keyname.
    This is useful because the s3_files column on submissions is currently too
    small.

    Returns:
        public_url: URL to access uploaded list
    '''
    conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
    bucketname = settings.S3_BUCKET
    bucket = conn.create_bucket(bucketname)

    data = {}
    data['files'] = file_dict
    data['keys'] = key_dict

    prefix = getattr(settings, 'S3_PATH_PREFIX')
    path = '{0}/{1}'.format(prefix, path)

    k = Key(bucket)
    k.key = '{path}/{name}'.format(path=path, name=name)
    k.set_contents_from_string(json.dumps(data))
    public_url = k.generate_url(60*60*24*365)  # URL timeout in seconds.

    return public_url


@statsd.timed('xqueue.lms_interface.s3_upload.time')
def _upload_to_s3(file_to_upload, path, name):
    '''
    Upload file to S3 using provided keyname.

    Returns:
        public_url: URL to access uploaded file
    '''
    conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
    bucketname = settings.S3_BUCKET
    bucket = conn.create_bucket(bucketname)

    prefix = getattr(settings, 'S3_PATH_PREFIX')
    path = '{0}/{1}'.format(prefix, path)

    k = Key(bucket)
    k.key = '{path}/{name}'.format(path=path, name=name)
    k.set_metadata('filename', file_to_upload.name)
    k.set_contents_from_file(file_to_upload)
    public_url = k.generate_url(60*60*24*365)  # URL timeout in seconds.

    return public_url
