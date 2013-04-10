'''
Test that the XQueue responds to a client.
'''
from tests.integration_framework import PassiveGraderStub, \
                                    GradeResponseListener, XQueueTestClient

from django.utils import unittest
from django.contrib.auth.models import User
from django.conf import settings
from nose.plugins.attrib import attr


@attr('grader_integration')
class MatlabGraderTest(unittest.TestCase):
    '''
    Test that we can send messages to the xqueue
    and receive a response from a Mathworks server

    The test requires that the Mathworks end-point is set up
    correctly in the settings:

    * XQUEUES must contain an entry for matlab:
        {'matlab': URL }

    * MATLAB_API_KEY must contain the API key to send the Mathworks
        servers.

    You can specify these in env.json (see test_settings.py for details)
    If the required settings cannot be loaded, the test will fail.
    '''

    CALLBACK_PORT = 12348
    QUEUE_NAME = 'matlab'

    def setUp(self):
        '''
        Set up the client and stubs to be used across tests.
        '''

        # Attempt to load settings for the Mathworks servers
        self.api_key = settings.MATHWORKS_API_KEY
        grader_url = settings.XQUEUES.get(MatlabGraderTest.QUEUE_NAME, None)

        # Fail immediately if settings are missing
        self.assertTrue(self.api_key is not None,
                    'You must specify an API key for Mathworks in envs.json.')
        self.assertTrue(grader_url is not None,
                'You must specify a URL for the Mathworks grader in envs.json')

        # Create the client (input submissions)
        # and configure it to send messages
        # that end up back at CALLBACK_PORT
        self.client = XQueueTestClient(MatlabGraderTest.CALLBACK_PORT)

        # Create the response listener
        # and configure it to receive messages on CALLBACK_PORT
        self.response_listener = \
                GradeResponseListener(MatlabGraderTest.CALLBACK_PORT)

        # Create the user and make sure we are logged in
        XQueueTestClient.create_user('test', 'test@edx.org', 'password')
        self.client.login(username='test', password='password')

        # Start up workers to pull messages from the queue
        # and forward them to our grader
        PassiveGraderStub.start_workers(MatlabGraderTest.QUEUE_NAME,
                                        grader_url)


    def tearDown(self):
        '''
        Stop each of the listening services to free up the ports
        '''
        self.response_listener.stop()

        # Stop the workers we started earlier
        PassiveGraderStub.stop_workers()


    def test_submission(self):
        '''
        Test submitting directly to Mathworks
        '''
        payload = "%%api_key=%s\n%%%%\nassert(isequal(x,1))\n" % self.api_key
        student_input = 'x=1'

        # Send the XQueue a submission to be graded
        submission = self.client.build_request(MatlabGraderTest.QUEUE_NAME,
                                                grader_payload=payload,
                                                student_response=student_input)

        self.client.send_request(submission)

        # Poll the response listener until we get a response
        # or reach the timeout
        poll_func = lambda listener: len(listener.get_grade_responses()) > 0
        success = self.response_listener.block_until(poll_func,
                                                    sleep_time=0.5,
                                                    timeout=10.0)

        # Check that we did not time out
        self.assertTrue(success)

        # Check that the response matches what we expect
        responses = self.response_listener.get_grade_responses()
        xqueue_body = responses[0]['response']['xqueue_body']

        self.assertEqual(xqueue_body.get('msg', None), 
                        "<div class='matlabResponse'><ul></ul></div>")
        self.assertEqual(xqueue_body.get('correct', None), True)
        self.assertEqual(xqueue_body.get('score', None), 1)
