import json

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TransactionTestCase, override_settings
from django.test.client import Client
from unittest.mock import patch

from submission_queue import ext_interface
from submission_queue.models import Submission


def parse_xreply(xreply):
    xreply = json.loads(xreply.decode('utf-8'))
    return (xreply['return_code'], xreply['content'])


@override_settings(XQUEUES={'tmp': None})
class TestExtInterface(TransactionTestCase):

    def setUp(self):
        self.credentials = {'username': 'LMS', 'password': 'CambridgeMA'}
        self.user = User.objects.create_user(**self.credentials)
        self.valid_reply = {
            'xqueue_header': json.dumps({'submission_id': 3,
                                         'submission_key': 'qwerty'}),
            'xqueue_body': json.dumps({'msg': "I graded it",
                                       'score': 1,
                                       'correct': True})
        }

    # get_queuelen
    def test_queue_length_invalid_queue_name(self):
        """
        An invalid queue but a login will tell you all the valid queues
        """
        client = Client()
        client.login(**self.credentials)
        response = client.get('/xqueue/get_queuelen/', {'queue_name': 'MIA'})
        assert response.status_code == 200
        error, message = parse_xreply(response.content)
        assert error
        assert 'Valid queue names are: ' in message

    def test_queue_length_missing_queue_name(self):
        """
        Confirm the error message when you don't specify a queue name for the length
        """
        client = Client()
        client.login(**self.credentials)
        response = client.get('/xqueue/get_queuelen/')
        assert response.status_code == 200
        error, message = parse_xreply(response.content)
        assert error
        assert message == "'get_queuelen' must provide parameter 'queue_name'"

    # get_submission
    def test_get_submission_no_queue(self):
        """
        Confirm the error message when you don't specify a queue name but ask for a submission
        """
        client = Client()
        client.login(**self.credentials)
        response = client.get('/xqueue/get_submission/')
        self.assertEqual(response.status_code, 200)
        (error, msg) = parse_xreply(response.content)
        self.assertEqual(error, True)
        self.assertEqual(msg, "'get_submission' must provide parameter 'queue_name'")

    def test_get_submission_invalid_queue(self):
        """
        Confirm the error message when you try to get a submission for an invalid queue
        """
        client = Client()
        client.login(**self.credentials)
        response = client.get('/xqueue/get_submission/', {'queue_name': 'nope'})
        self.assertEqual(response.status_code, 200)
        (error, msg) = parse_xreply(response.content)
        self.assertEqual(error, True)
        self.assertEqual(msg, "Queue 'nope' not found")

    def test_get_submission_empty(self):
        """
        Confirm the message (non-error) when your queue is empty
        """
        client = Client()
        client.login(**self.credentials)
        response = client.get('/xqueue/get_submission/', {'queue_name': 'tmp'})
        self.assertEqual(response.status_code, 200)
        (error, msg) = parse_xreply(response.content)
        self.assertEqual(error, 1)  # queue empty but exists still comes with a False code
        self.assertEqual(msg, "Queue 'tmp' is empty")

    def test_get_submission(self):
        """
        Retrieve a single submission for the queue
        """
        body = json.dumps({"test": "test"})
        Submission.objects.create(queue_name='tmp',
                                  lms_callback_url='/',
                                  xqueue_header='{}',
                                  xqueue_body=body)

        client = Client()
        client.login(**self.credentials)
        response = client.get('/xqueue/get_submission/', {'queue_name': 'tmp'})
        self.assertEqual(response.status_code, 200)
        (error, msg) = parse_xreply(response.content)
        self.assertEqual(error, 0)  # success apparently
        result = json.loads(msg)
        self.assertEqual(result['xqueue_body'], body)

    # combinations of get_queuelen and get_submission
    # these test mostly non-error conditions
    def test_get_submission_multiple_submissions(self):
        """
        This should have queuelen 2 then 1 since we hide submissions
        for a brief period of time after one is pulled so that it isn't
        double pulled.
        """
        body = json.dumps({"test": "test"})
        for i in range(2):
            Submission.objects.create(queue_name='tmp',
                                      lms_callback_url=f'/{i}',
                                      xqueue_header='{}',
                                      xqueue_body=body)

        client = Client()
        client.login(**self.credentials)

        # Confirm there are 2
        response = client.get('/xqueue/get_queuelen/', {'queue_name': 'tmp'})
        self.assertEqual(response.status_code, 200)
        error, queue_length = parse_xreply(response.content)
        self.assertEqual(error, 0)  # success apparently
        self.assertEqual(queue_length, 2)

        # Fetch one down
        response = client.get('/xqueue/get_submission/', {'queue_name': 'tmp'})
        self.assertEqual(response.status_code, 200)
        (error, msg) = parse_xreply(response.content)
        self.assertEqual(error, 0)  # success apparently

        # Confirm that we now have 1
        response = client.get('/xqueue/get_queuelen/', {'queue_name': 'tmp'})
        self.assertEqual(response.status_code, 200)
        error, queue_length = parse_xreply(response.content)
        self.assertEqual(error, 0)  # success apparently
        self.assertEqual(queue_length, 1)

    def test_is_valid_reply(self):
        '''
        Test Xqueue's ability to evaluate valid request format from graders
            and its ability to gracefully reject bad replies
        '''
        (is_valid, _, _, _) = ext_interface._is_valid_reply(self.valid_reply)
        self.assertEqual(is_valid, True)

        # 1) Header is missing
        bad_reply1 = {'xqueue_body': json.dumps({'msg': "I graded it",
                                                 'score': 1,
                                                 'correct': True})}
        # 2) Body is missing
        bad_reply2 = {'xqueue_header': json.dumps({'submission_id': 3,
                                                   'submission_key': 'qwerty'})}
        # 3) Header not serialized
        bad_reply3 = {'xqueue_header': {'submission_id': 3,
                                        'submission_key': 'qwerty'},
                      'xqueue_body': json.dumps({'msg': "I graded it",
                                                 'score': 1,
                                                 'correct': True})}
        # 4) 'submission_key' is missing in header
        bad_reply4 = {'xqueue_header': json.dumps({'submission_id': 3}),
                      'xqueue_body': json.dumps({'msg': "I graded it",
                                                 'score': 1,
                                                 'correct': True})}
        # 5) 'submission_id' is missing in header
        bad_reply5 = {'xqueue_header': json.dumps({'submission_key': 'qwerty'}),
                      'xqueue_body': json.dumps({'msg': "I graded it",
                                                 'score': 1,
                                                 'correct': True})}
        # 5) Header is not a dict
        bad_reply6 = {'xqueue_header': json.dumps(['MIT', 'Harvard', 'Berkeley']),
                      'xqueue_body': ''}
        # 6) Arbitrary payload
        bad_reply7 = 'The capital of Mongolia is Ulaanbaatar'

        bad_replys = [bad_reply1, bad_reply2, bad_reply3, bad_reply4, bad_reply5, bad_reply6, bad_reply7]
        for bad_reply in bad_replys:
            (is_valid, _, _, _) = ext_interface._is_valid_reply(bad_reply)
            self.assertEqual(is_valid, False)

        client = Client()
        client.login(**self.credentials)
        response = client.post('/xqueue/put_result/', bad_reply1)
        self.assertEqual(response.status_code, 200)
        (error, msg) = parse_xreply(response.content)
        self.assertEqual(error, 1)  # failure
        self.assertEqual(msg, 'Incorrect reply format')

    def test_put_result_with_invalid_submission(self):
        client = Client()
        client.login(**self.credentials)
        response = client.post('/xqueue/put_result/', self.valid_reply)
        self.assertEqual(response.status_code, 200)
        (error, msg) = parse_xreply(response.content)
        self.assertEqual(error, 1)  # failure
        self.assertEqual(msg, 'Submission does not exist')

    @patch('submission_queue.consumer.post_grade_to_lms', return_value=False)
    @override_settings(SUBMISSION_PROCESSING_DELAY=0)
    def test_put_result_with_lms_failures(self, mock_post_grade_to_lms):
        """
        Checks that if you submit a reply more than MAX_NUMBER_OF_FAILURES times,
        it gets auto-retired rather than being available forever.
        """

        body = json.dumps({"test": "test"})
        submission = Submission.objects.create(queue_name='tmp',
                                               lms_callback_url='/',
                                               xqueue_header='{}',
                                               xqueue_body=body,
                                               pullkey='testkey')

        valid_reply = {
            'xqueue_header': json.dumps({'submission_id': submission.id,
                                         'submission_key': 'testkey'}),
            'xqueue_body': json.dumps({'msg': "I graded it",
                                       'score': 1,
                                       'correct': True})
        }

        client = Client()
        client.login(**self.credentials)

        for i in range(settings.MAX_NUMBER_OF_FAILURES):
            response = client.post('/xqueue/put_result/', valid_reply)
            self.assertEqual(response.status_code, 200)
            submission.refresh_from_db()
            self.assertFalse(submission.retired)
            self.assertFalse(submission.lms_ack)
            self.assertEqual(submission.num_failures, i+1)

        # After enough replies, we should auto-retire this
        response = client.post('/xqueue/put_result/', valid_reply)
        self.assertEqual(response.status_code, 200)
        submission.refresh_from_db()
        self.assertTrue(submission.retired)
        self.assertFalse(submission.lms_ack)
        self.assertEqual(submission.num_failures, settings.MAX_NUMBER_OF_FAILURES + 1)

# We don't test put_result with valid replies further because that's handled by
# the passive/active graders with fake LMSes already.
