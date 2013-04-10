'''
Test that the XQueue responds to a client.
'''
from tests.integration_framework import PassiveGraderStub, \
                                    GradeResponseListener, XQueueTestClient

from django.utils import unittest
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

    def test_matlab_check_correct(self):
        response = self._submit_to_mathworks("assert(isequal(x,1))", "x=1")

        self.assertEqual(response.get('msg', None), 
                        "<div class='matlabResponse'><ul></ul></div>")
        self.assertEqual(response.get('correct', None), True)
        self.assertEqual(response.get('score', None), 1)

    def test_matlab_check_incorrect(self):
        response = self._submit_to_mathworks("assert(isequal(x,1))", "x=5")

        self.assertEqual(response.get('msg', None), 
                        "<div class='matlabResponse'>" + 
                        "<ul><li>Assertion failed.\n</li></ul></div>")
        self.assertEqual(response.get('correct', None), False)
        self.assertEqual(response.get('score', None), 0)

    def test_matlab_graph(self):
        response = self._submit_to_mathworks("peaks;", "")

        # The response message is usually very long,
        # so we scan for the CSS tag instead.
        response_msg = response.get('msg', '')
        self.assertTrue('matlabFigures' in response_msg)

        self.assertEqual(response.get('correct', None), True)
        self.assertEqual(response.get('score', None), 1)

    def test_matlab_invalid(self):
        response = self._submit_to_mathworks("invalid", "x=5")

        self.assertEqual(response.get('msg', None), 
            "<div class='matlabResponse'><ul>" +
            "<li>Undefined function or variable 'invalid'.\n</li></ul></div>")
        self.assertEqual(response.get('correct', None), False)
        self.assertEqual(response.get('score', None), 0)


    def _submit_to_mathworks(self, matlab_code, student_input):
        '''
        Assert that Mathworks servers provide the correct response.

        matlab_code: Matlab code to be processed by external servers (string)

        student_input: The student's response (string)

        Returns the response from Mathworks (dict)
        '''
        payload = "%%api_key=%s\n%%%%\n%s\n" % (self.api_key, matlab_code)

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
        self.assertTrue(success, 'Timed out waiting for response')

        # Return the response
        responses = self.response_listener.get_grade_responses()
        xqueue_body = responses[0]['response']['xqueue_body']
        return xqueue_body
