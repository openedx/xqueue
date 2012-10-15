#!/usr/bin/env python

"""
Simple test script to connect to a queue and send a dummy request.
"""
import argparse
import datetime
import itertools
import json
import logging
import requests
import pprint
import sys
import threading
import time

now = datetime.datetime.now

QSERVER = 'http://127.0.0.1:3032'
PWD = 'abcd'

logger = logging.getLogger(__name__)


class XQueueClient(object):
    RUN = now().strftime("%Y%m%d%H%M%S")

    def __init__(self, server, pwd):
        self.s = requests.session()
        self.server = server
        self.pwd = pwd

    def login(self):
        logger.info("logging in...")
        r = self.s.post(self.server + '/xqueue/login/',  {'username': 'lms', 'password': self.pwd})
        r.raise_for_status()
        logger.debug("login response: %r", r.json)

    def make_request(self, uniqueid):
        request = {
            'xqueue_header': json.dumps({
                'lms_callback_url': 'http://httpbin.org/post',  # an actual mock http server online.
                'lms_key': 'qwerty',
                'queue_name': 'MITx-6.00x',
            }),
            'xqueue_body': json.dumps({
                'student_info': json.dumps({
                    'anonymous_student_id': "connect_py_%s_%s" % (self.RUN, uniqueid), 
                    'submission_time': now().strftime("%Y%m%d%H%M%S"),
                }),
                'grader_payload': json.dumps({
                    'grader': 'finger_exercises/L2/two_vars/grade_two_vars.py',
                }),
                'student_response': 
                    "if type(varA) == str or type(varB) == str:\n"
                    "    print('string not involved')\n"
                    "elif varA > varB:\n"
                    "    print('bigger')\n"
                    "elif varA == varB:\n"
                    "    print('equal')\n"
                    "else:\n"
                    "    # If none of the above conditions are true,\n"
                    "    # it must be the case that varA < varB\n"
                    "    print('smaller')\n",
            }), 
        }
        return request

    def submit_job(self, request):
        logger.info("submitting job...")
        r = self.s.post(self.server + '/xqueue/submit/', request)
        r.raise_for_status()
        logger.debug("submit response: %r", r.json)


def send_test_requests(qserver, pwd, threadid, rate=None):
    """Sent a number of XQueue requests."""
    xq = XQueueClient(qserver, pwd)
    xq.login()

    for student in itertools.count():
        request = xq.make_request("%03d_%05d" % (threadid, student))
        xq.submit_job(request)
        if not rate:
            break
        time.sleep(1.0/rate)


def main(args):
    parser = argparse.ArgumentParser(description="Send dummy requests to a qserver")
    parser.add_argument('server', nargs='?')
    parser.add_argument('password', nargs='?')
    parser.add_argument('--rate', help="How many requests per second per thread to send.", type=int)
    parser.add_argument('--threads', help="How many threads to run.", type=int)
    parser.add_argument('--quiet', help="Be chatty?", action='store_true')

    args = parser.parse_args()

    qserver = args.server or QSERVER
    pwd = args.password or PWD

    if qserver.endswith('/'):
        # strip off trailing /
        qserver = qserver[:-1]

    # Other components (like requests) spew log stuff we don't want to see.
    logging.basicConfig(
        level=logging.WARNING,
        format='%(message)s',
    )

    logger.setLevel(logging.WARNING if args.quiet else logging.DEBUG)

    if args.threads:
        for threadid in range(args.threads):
            t = threading.Thread(target=send_test_requests, args=(qserver, pwd, threadid, args.rate))
            t.daemon = True
            t.start()
        time.sleep(999999)  # 11 days should be long enough...
    else:
        send_test_requests(qserver, pwd, 0, args.rate)

    

if __name__ == '__main__':
    main(sys.argv[1:])
