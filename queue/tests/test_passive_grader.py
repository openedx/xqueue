"""Test that the XQueue responds to a client, using a Passive Grader
(one that the XQueue pushes submissions to)"""
from test_framework.integration_framework import PassiveGraderStub, \
    GradeResponseListener, XQueueTestClient

from django.test import TransactionTestCase
from django.test.utils import override_settings
from uuid import uuid4


class SimplePassiveGrader(PassiveGraderStub):
    """Passive external grader stub that always responds
    with the same, pre-defined message."""

    def __init__(self, response_dict):
        """
        Configure the stub to always respond with the same message

        response_dict: JSON-serializable dict to send in response to
            a submission.
        """
        self._response_dict = response_dict
        PassiveGraderStub.__init__(self)

    def response_for_submission(self, submission):
        """
        Always send the same response

        submission: The student's submission (dict)
        returns: response to submission (dict)
        """
        return self._response_dict


class PassiveGraderTest(TransactionTestCase):
    """Test that we can send messages to the xqueue
    and receive a response when using a "passive" external
    grader (one that expects xqueue to send it submissions)"""

    GRADER_RESPONSE = {'submission_data': 'test'}

    # Choose a unique queue name to prevent conflicts
    # in Jenkins
    QUEUE_NAME = 'test_queue_%s' % uuid4().hex

    def setUp(self):
        """Set up the client and stubs to be used across tests."""
        # Create the grader
        self.grader = SimplePassiveGrader(PassiveGraderTest.GRADER_RESPONSE)

        # Create the response listener
        # and configure it to receive messages on a local port
        self.response_listener = GradeResponseListener()

        # Create the client (input submissions)
        # and configure it to send messages
        # that will be sent back to our response listener
        self.client = XQueueTestClient(self.response_listener.port_num())

        # Create the user and make sure we are logged in
        XQueueTestClient.create_user('test', 'test@edx.org', 'password')
        self.client.login(username='test', password='password')

        # Start up workers to pull messages from the queue
        # and forward them to our grader
        self.grader.start_workers(PassiveGraderTest.QUEUE_NAME)

    def tearDown(self):
        """Stop each of the listening services to free up the ports"""
        self.grader.stop()
        self.response_listener.stop()

        # Stop the workers we started earlier
        SimplePassiveGrader.stop_workers()

        # Delete the queue we created
        SimplePassiveGrader.delete_queue(PassiveGraderTest.QUEUE_NAME)

    def test_submission(self):
        """Submit a single response to the XQueue and check that
        we get the expected response."""

        payload = {'test': 'test'}
        student_input = 'test response'

        # Tell the xqueue to forward messages to our grader
        xqueue_settings = {PassiveGraderTest.QUEUE_NAME: self.grader.grader_url()}
        with override_settings(XQUEUES=xqueue_settings):

            # Send the XQueue a submission to be graded
            submission = self.client.build_request(PassiveGraderTest.QUEUE_NAME,
                                                   grader_payload=payload,
                                                   student_response=student_input)

            self.client.send_request(submission)

            # Poll the response listener until we get a response
            # or reach the timeout
            def poll_func(listener):
                return len(listener.get_grade_responses()) > 0
            success = self.response_listener.block_until(poll_func,
                                                         sleep_time=0.5,
                                                         timeout=4.0)

        # Check that we did not time out
        self.assertTrue(success)

        # Check the response matches what we expect
        responses = self.response_listener.get_grade_responses()
        xqueue_body = responses[0]['response']['xqueue_body']
        self.assertEqual(PassiveGraderTest.GRADER_RESPONSE, xqueue_body)
