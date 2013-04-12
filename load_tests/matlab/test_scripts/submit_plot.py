'''
Test interaction script that submits a request to the matlab
graders to plot a function.

The test requires that Mathworks API endpoint login information
is configured correctly in test_env.json.  See xqueue.test_settings
for details.

The test also assumes that the xqueue django app has the correct
settings to push messages from the 'matlab' queue to the mathworks
end-point.
'''

# Use test settings to satisfy Django
# We use settings only to load mathworks end-point information
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'xqueue.test_settings'

# Load test settings so we can access
# mathworks end-point information
from django.conf import settings

# Use the integration test framework to interact with XQueue
from test_framework.integration_framework import GradeResponseListener, \
                                                XQueueTestClient

import requests

import logging
logger = logging.getLogger(__name__)

class Transaction(object):

    # By default, assume that XQueue is running locally
    XQUEUE_URL = 'http://127.0.0.1:3031/'

    # Assume that we have already created user credentials
    # using management commands
    # See CONFIG for details
    USERNAME = 'lms'
    PASSWORD = 'abcd'
    
    # Assume that the queue name is configured correctly
    QUEUE_NAME = 'matlab'

    # The number of problems to submit answers for
    # We distribute submissions over several problems
    # to avoid being rejected as a DDOS attack
    NUM_PROBLEMS = 5

    # Student submission (Matlab code)
    # This tells the matlab server to create an image of a graph
    SUBMISSION = "peaks;"

    def __init__(self):

        # Attempt to load settings for the Mathworks servers
        self.api_key = settings.MATHWORKS_API_KEY

        # Fail immediately if settings are missing
        # Check the configuration in test_env.json
        # (see xqueue.test_settings for details)
        assert(self.api_key is not None)

        # Initialize as many response listeners as we have
        # problems.  A submission to a problem will go
        # to a specific response listener.
        self.response_listeners = []
        self.clients = []
        for i in range(Transaction.NUM_PROBLEMS):

            # Create the response listener
            # This is unique for our test, so we can capture
            # responses only for the submissions we sent
            listener = GradeResponseListener()
            self.response_listeners.append(listener)

            # Create a client that submits to this problem
            # (configure it so the xqueue will send its response
            # to this response listener)
            client = XQueueTestClient(listener.port_num())
            self.clients.append(client)

        # Log in and store the session
        self.session = self._log_in()

    def shut_down_listeners(self):
        '''
        Shut down all listeners we created
        '''
        for listener in self.response_listeners:
            listener.stop()

    def run(self):

        # This is the matlab code that the grader will execute
        # We have it assert something true, so it always grades us correct
        matlab_code = 'assert(isequal(1,1))'
        payload = "%%api_key=%s\n%%%%\n%s\n" % (self.api_key, matlab_code)

        # Send one submission for each problem
        submission_sent = []
        for client in self.clients:

            # Construct a submission for a particular problem
            submission = client.build_request(Transaction.QUEUE_NAME,
                                    grader_payload=payload,
                                    student_response=Transaction.SUBMISSION)

            # POST the submission to the XQueue
            # We do this using requests rather than our test client
            # because we are not using Django's TestCase
            success = self._send_submission(submission)

            # Remember whether we were able to send the submission successfully
            # If not, then we do not want to wait indefinitely for
            # a response
            submission_sent.append(success)
        
        # Wait for the XQueue to respond to all our requests,
        # or time out.
        # This is slightly inefficient in that we have to poll each
        # listener individually.
        # We use a short sleep time so when the messages arrive,
        # we know right away and can therefore (somewhat) accurately time
        # the XQueue.
        poll_func = lambda listener: len(listener.get_grade_responses()) > 0
        for (submitted, listener) in zip(submission_sent, self.response_listeners):

            # Only wait for a submission that we managed to send successfully
            if submitted:
                success = listener.block_until(poll_func, 
                                                sleep_time=0.05, 
                                                timeout=5.0)

                if success:
                    logger.info('Received response from XQueue')
                else:
                    logger.warning('Timed out waiting for response from XQueue')

        # Clean up, free up ports
        self.shut_down_listeners()

    def _log_in(self):
        '''
        Log in using default credentials.
        Returns a session object used to make additional requests

        Raises IOError if we could not log in.
        '''
        session = requests.Session()
        response = session.post(Transaction.XQUEUE_URL + "xqueue/login/",
                    {'username': Transaction.USERNAME,
                        'password': Transaction.PASSWORD})

        if response.status_code != requests.codes.ok:
            raise IOError("Could not log in: response code %d" 
                                % response.status_code)
        else:
            logger.info("Logged in successfully")
            return session
                    

    def _send_submission(self, submission):
        '''
        POST a submission to the XQueue

        submission is a dictionary that will be form-encoded and sent
        to the xqueue

        Returns True if successful, False otherwise
        '''
        logger.info('Sending submission to XQueue')

        response = self.session.post(Transaction.XQUEUE_URL + "xqueue/submit/", 
                                        data=submission,
                                        timeout=2.0)

        if response.status_code != requests.codes.ok:
            logger.warning('XQueue submission had status code %d' 
                            % response.status_code)
            return False

        else:
            # Check that the XQueue responded with success
            response_dict = response.json

            if response_dict['return_code'] != 0:
                logger.warning('XQueue responded with error: %s' %
                                response_dict['content'])
                return False

            else:
                logger.info('Submitted successfully')
                return True

if __name__ == '__main__':
    trans = Transaction()
    trans.run()
