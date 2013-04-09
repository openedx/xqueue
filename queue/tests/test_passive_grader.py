'''
Test that the XQueue responds to a client.
'''
from tests.integration_framework import PassiveGraderStub, \
                                GradeResponseListener, XQueueTestClient

from django.utils import unittest
from django.contrib.auth.models import User
import json


class SimplePassiveGrader(PassiveGraderStub):
    '''
    Passive external grader stub that always responds
    with the same, pre-defined message.
    '''

    PORT_NUM = 12347

    def __init__(self, response_dict):
        '''
        Configure the stub to always respond with the same message

        port_num: The local port to listen on (int)

        response_dict: JSON-serializable dict to send in response to
            a submission.
        '''
        self._response_dict = response_dict
        PassiveGraderStub.__init__(self, SimplePassiveGrader.PORT_NUM)

    def response_for_submission(self, submission):
        '''
        Always send the same response

        submission: The student's submission (dict)
        returns: response to submission (dict)
        '''
        return self._response_dict


class PassiveGraderTest(unittest.TestCase):
    '''
    Test that we can send messages to the xqueue
    and receive a response when using a "passive" external
    grader (one that expects xqueue to send it submissions)
    '''

    GRADER_RESPONSE = {'submission_data': 'test'}
    CALLBACK_PORT = 12348
    QUEUE_NAME = 'test_queue'

    def setUp(self):
        '''
        Set up the client and stubs to be used across tests.
        '''
        # Create the grader
        self.grader = SimplePassiveGrader(PassiveGraderTest.GRADER_RESPONSE)

        # Create the client (input submissions)
        # and configure it to send messages
        # that end up back at CALLBACK_PORT
        self.client = XQueueTestClient(PassiveGraderTest.CALLBACK_PORT)

        # Create the response listener
        # and configure it to receive messages on CALLBACK_PORT
        self.response_listener = \
                GradeResponseListener(PassiveGraderTest.CALLBACK_PORT)

        # Create the user and make sure we are logged in
        User.objects.create_user('test', 'test@edx.org', 'password')
        self.client.login(username='test', password='password')

        # Start up workers to pull messages from the queue
        # and forward them to our grader
        SimplePassiveGrader.start_workers(PassiveGraderTest.QUEUE_NAME,
                                            SimplePassiveGrader.PORT_NUM)


    def tearDown(self):
        ''' 
        Stop each of the listening services to free up the ports 
        '''
        self.grader.stop()
        self.response_listener.stop()

        # Stop the workers we started earlier
        SimplePassiveGrader.stop_workers()


    def test_submission(self):
        '''
        Submit a single response to the XQueue and check that
        we get the expected response.
        '''

        payload = {'test': 'test'}
        student_input = 'test response'

        # Send the XQueue a submission to be graded
        submission = self.client.build_request(PassiveGraderTest.QUEUE_NAME,
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

        # Check the response matches what we expect
        responses = self.response_listener.get_grade_responses()
        xqueue_body = json.loads(responses[0]['response']['xqueue_body'])
        self.assertEqual(PassiveGraderTest.GRADER_RESPONSE, xqueue_body)
