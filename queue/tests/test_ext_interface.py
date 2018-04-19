import json
from queue.models import Submission

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TransactionTestCase, override_settings
from django.test.client import Client
from mock import patch


@override_settings(XQUEUES={'tmp': None})
class TestExtInterface(TransactionTestCase):

    def setUp(self):
        self.credentials = {'username': 'LMS', 'password': 'CambridgeMA'}
        self.user = User.objects.create_user(**self.credentials)

    @patch('queue.consumer.post_grade_to_lms', return_value=False)
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
