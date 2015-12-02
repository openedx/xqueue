"""Test that the XQueue responds to a client, using an Active Grader
(one that polls the XQueue and pushes responses using a REST-like
interface)"""
from test_framework.integration_framework \
    import GradeResponseListener, XQueueTestClient, ActiveGraderStub
from django.test.utils import override_settings
from django.conf import settings
from django.test import TransactionTestCase
from uuid import uuid4


class SimpleActiveGrader(ActiveGraderStub):
    """Active external grader stub that always responds
    with the same, pre-defined message."""

    def __init__(self, queue_name, response_dict):
        """Configure the stub to always respond with the same message

        `queue_name`: The name of the queue to poll

        `response_dict`: JSON-serializable dict to send in response to
            a submission.
        """
        self._response_dict = response_dict
        ActiveGraderStub.__init__(self, queue_name)

    def response_for_submission(self, submission):
        """Always send the same response

        submission: The student's submission (dict)
        returns: response to submission (dict)
        """

        # Pass the same XQueue header back, so the XQueue
        # can validate our response
        return {'xqueue_header': submission['xqueue_header'],
                'xqueue_body': self._response_dict}


class ActiveGraderTest(TransactionTestCase):
    """Test that we can send messages to the xqueue
    and receive a response when using an "active" external
    grader (one that polls the XQueue and pushes responses using
    a REST-like interface)
    """

    GRADER_RESPONSE = {'submission_data': 'test'}

    # Choose a unique queue name to prevent conflicts
    # in Jenkins
    QUEUE_NAME = 'test_queue_%s' % uuid4().hex

    def setUp(self):
        """Set up the client and stubs to be used across tests."""
        # Create the grader
        self.grader = SimpleActiveGrader(ActiveGraderTest.QUEUE_NAME,
                                         ActiveGraderTest.GRADER_RESPONSE)

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

        # Since the ActiveGraderStub is polling the XQueue,
        # we do NOT need to start any workers (consumers)
        # that pull messages from the XQueue and pass them on

    def tearDown(self):
        """Stop each of the listening services to free up the ports"""
        self.grader.stop()
        self.response_listener.stop()

        # Delete the queue we created
        SimpleActiveGrader.delete_queue(ActiveGraderTest.QUEUE_NAME)

    def test_submission(self):
        """Submit a single response to the XQueue and check that
        we get the expected response."""
        payload = {'test': 'test'}
        student_input = 'test response'

        # Add our queue to the available queues
        # Otherwise, XQueue will not process our messages
        # We set the callback URL to None because XQueue does not
        # need to forward the messages; instead, our ActiveGrader
        # polls for them
        xqueue_settings = settings.XQUEUES
        xqueue_settings[ActiveGraderTest.QUEUE_NAME] = None
        with override_settings(XQUEUES=xqueue_settings):

            # Send the XQueue a submission to be graded
            submission = self.client.build_request(ActiveGraderTest.QUEUE_NAME,
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
        self.assertEqual(ActiveGraderTest.GRADER_RESPONSE, xqueue_body)
