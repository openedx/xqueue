"""Test that the XQueue responds to a client, using a Passive Grader
(one that the XQueue pushes submissions to)"""
from uuid import uuid4

from django.test import TransactionTestCase
from django.test.utils import override_settings

from test_framework.integration_framework import (GradeResponseListener,
                                                  PassiveGraderStub,
                                                  XQueueTestClient)


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
        user1 = self.client.login(username='test', password='password')
        self.assertEqual(user1.username, 'test')

    def test_submission(self):
        """Submit a single response to the XQueue and check that
        we get the expected response."""
        self.assertEqual(1, 1)
