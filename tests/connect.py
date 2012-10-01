#!/usr/bin/env python

"""
Simple test script to connect to a queue and send a dummy request.
"""
import json
import requests
import sys

qserver = 'http://127.0.0.1:3032'
pwd = 'abcd'

def send_test_requests():

    good_request = {'xqueue_header': json.dumps({'lms_callback_url':'/',
                                                 'lms_key':'qwerty',
                                                 'queue_name':'MITx-6.00x'}),
                                                 'xqueue_body': 'def square(x):\n    return n**2'}

    print "logging in..."
    s = requests.session()
    r = s.post(qserver + '/xqueue/login/',  {'username': 'lms', 'password': pwd})
    r.raise_for_status()
    print r.json

    print "sending job..."
    r = s.post(qserver + '/xqueue/submit/',  good_request)
    r.raise_for_status()
    print r.json


def main(args):
    global qserver
    global pwd
    n = len(args)
    if n > 2:
        print "Usage: test.py [http://some-q-server:port/ [pwd]]"
        sys.exit(1)

    if n > 0:
        qserver = args[0]
    if n > 1:
        pwd = args[1]

    if qserver.endswith('/'):
        # strip off trailing /
        qserver = qserver[:-1]

    send_test_requests()

if __name__ == '__main__':
    main(sys.argv[1:])
