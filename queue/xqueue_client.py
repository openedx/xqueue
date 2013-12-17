import datetime
import json
import logging
import requests

logger = logging.getLogger(__name__)


class XQueueClient(object):
    """
    Test client to simulate a hello world problem
    submission
    """
    def __init__(self, server, passwd, post_url):
        self.s = requests.session()
        self.server = server
        self.passwd = passwd
        self.post_url = post_url

    def login(self):
        logger.info("logging in...")
        r = self.s.post(self.server + '/xqueue/login/',
                        {'username': 'lms', 'password': self.passwd})
        r.raise_for_status()
        logger.debug("login response: %r", r.json)

    def submit_job(self, uniqueid='herpderp', queue_name='MITx-6.00x'):
        logger.info("submitting job...")
        run_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        request = {
            'xqueue_header': json.dumps({
                'lms_callback_url': self.post_url,
                'lms_key': 'qwerty',
                'queue_name': queue_name,
            }),
            'xqueue_body': json.dumps({
                'student_info': json.dumps({
                    'anonymous_student_id':
                    "connect_py_%s_%s" % (run_time, uniqueid),
                    'submission_time': run_time,
                }),
                'grader_payload': json.dumps({
                    'grader': 'finger_exercises/L2/hello_world/grade_hello.py',
                }),
                'student_response':
                "print 'hello world'\n",
            }),
        }

        r = self.s.post(self.server + '/xqueue/submit/', request)
        r.raise_for_status()
        logger.debug("submit response: %r", r.json)
