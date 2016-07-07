"""
Run me with:
    python manage.py test --settings=xqueue.test_settings queue
"""
import json
import shutil

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test.client import Client
from django.test import SimpleTestCase, override_settings

from queue import lms_interface
from queue.models import Submission
from queue.util import make_hashkey


def parse_xreply(xreply):
    xreply = json.loads(xreply)
    return (xreply['return_code'], xreply['content'])


@override_settings(XQUEUES=['tmp'])
class lms_interface_test(SimpleTestCase):

    def setUp(self):
        self.credentials = {'username': 'LMS', 'password': 'CambridgeMA'}
        self.user = User.objects.create_user(**self.credentials)
        self.valid_payload = {
            'xqueue_header': json.dumps({'lms_callback_url': '/',
                                         'lms_key': 'qwerty',
                                         'queue_name': 'tmp'}),
            'xqueue_body': 'def square(x):\n    return n**2',
        }

    def tearDown(self):
        self.user.delete()
        shutil.rmtree('tmp', ignore_errors=True)

    def test_log_in(self):
        '''
        Test Xqueue login behavior. Particularly important is the response for GET (e.g. by redirect)
        '''
        c = Client()
        login_url = '/xqueue/login/'

        # 0) Attempt login with GET, must fail with message='login_required'
        #    The specific message is important, as it is used as a flag by LMS to reauthenticate!
        response = c.get(login_url)
        (error, msg) = parse_xreply(response.content)
        self.assertEqual(error, True)
        self.assertEqual(msg, 'login_required')

        # 1) Attempt login with POST, but no auth
        response = c.post(login_url)
        (error, _) = parse_xreply(response.content)
        self.assertEqual(error, True)

        # 2) Attempt login with POST, incorrect auth
        response = c.post(login_url,{'username':'LMS','password': 'PaloAltoCA'})
        (error, _) = parse_xreply(response.content)
        self.assertEqual(error, True)

        # 3) Login correctly
        response = c.post(login_url,{'username':'LMS','password':'CambridgeMA'})
        (error, _) = parse_xreply(response.content)
        self.assertEqual(error, False)

    def test_submit(self):
        '''
        The submit handler should return a success response and create a
        Submission instance.
        '''
        response = self._submit(self.valid_payload)
        self.assertEqual(response['return_code'], 0)  # success
        self.assertEqual(Submission.objects.count(), 1)

    @override_settings(XQUEUES=[])
    def test_submit_unknown_queue(self):
        '''
        The submit handler should return an error response if the requested
        queue is not found.
        '''
        response = self._submit(self.valid_payload)
        self.assertEqual(response['return_code'], 1)  # failure

    def test_submit_files(self):
        '''
        Submitted files should be uploaded to the storage backend.
        '''
        payload = self.valid_payload.copy()
        upload = ContentFile('TESTING', name='test')
        upload.seek(0)
        payload['upload'] = upload
        response = self._submit(payload)
        self.assertEqual(response['return_code'], 0)  # success

        # Check that the file was actually uploaded
        _, files = default_storage.listdir('tmp/')
        key = make_hashkey(payload['xqueue_header'] + 'upload')
        self.assertIn(key, files)

    def test_is_valid_request(self):
        '''
        Test Xqueue's ability to evaluate valid request format from LMS
            and its ability to gracefully reject
        '''
        (is_valid,_,_,_, _) = lms_interface._is_valid_request(self.valid_payload)
        self.assertEqual(is_valid, True)

        # 1) Header is missing
        bad_request1 = {'xqueue_body': 'def square(x):\n    return n**2'}
        # 2) Body is missing
        bad_request2 = {'xqueue_header': json.dumps({'lms_callback_url': '/',
                                                     'lms_key': 'qwerty',
                                                     'queue_name': 'python'})}
        # 3) Header not serialized
        bad_request3 = {'xqueue_header': {'lms_callback_url': '/',
                                          'lms_key': 'qwerty',
                                          'queue_name': 'python'},
                        'xqueue_body': 'def square(x):\n    return n**2'}
        # 4) 'lms_key' is missing in header
        bad_request4 = {'xqueue_header': json.dumps({'lms_callback_url': '/',
                                                     'queue_name': 'python'}),
                        'xqueue_body': 'def square(x):\n    return n**2'}
        # 5) Header is not a dict
        bad_request5 = {'xqueue_header': json.dumps(['MIT', 'Harvard', 'Berkeley']),
                        'xqueue_body': 'def square(x):\n    return n**2'}
        # 6) Arbitrary payload
        bad_request6 = 'The capital of Mongolia is Ulaanbaatar'

        bad_requests = [bad_request1, bad_request2, bad_request3, bad_request4, bad_request5, bad_request6]
        for bad_request in bad_requests:
            (is_valid,_,_,_, _) = lms_interface._is_valid_request(bad_request)
            self.assertEqual(is_valid, False)

    def _submit(self, *args, **kwargs):
        client = Client()
        client.login(**self.credentials)
        submit_url = '/xqueue/submit/'
        response = client.post(submit_url, *args, **kwargs)
        self.assertEqual(response.status_code, 200)
        return json.loads(response.content)
