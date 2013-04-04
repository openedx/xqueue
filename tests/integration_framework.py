'''
Framework for writing integration tests for xqueue and external
graders at the level of HTTP requests.
Basic xqueue communication:

1)    XQueueTestClient --(push)--> xqueue --(pull)--> GraderStub subclass

2)    GraderStub subclass --(push)--> xqueue --(push)--> GradeResponseListener

Test cases verify that the output to GradeResponseListener given
inputs specified by XQueueTestClient.


How messages get routed (ActiveGraderStub):

The test client sends messages to a particular queue.

ActiveGraderStub pulls messages from a particular queue, which
is specified by the test client.

ActiveGraderStub pushes the response back to XQueue

XQueue forwards grading responses to GradeResponseListener using
the callback_url provided by the test client.



How messages get routed (PassiveGraderStub):

The test client sends messages to a particular queue.

XQueue checks its settings and finds that the queue has
a URL associated with it.  XQueue forwards the message to that URL.

PassiveGraderStub is listening at the URL and receives POST request
from XQueue.  The stub responds synchronously with the graded response

XQueue forwards grading responses to GradeResponseListener using
the callback_url provided by the test client.


Failure injection:

This framework also makes it easy to inject failure into the system:
for example, by configuring ExternalGraderStub to stop responding
to messages, or to send invalid responses.
'''

from django.test.client import Client
from django.core.urlresolvers import reverse
import datetime
import time
import json
from abc import ABCMeta, abstractmethod
from queue.consumer import Worker
import urlparse
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn, ForkingMixIn

from logging import getLogger
logger = getLogger(__name__)

class GraderStubBase(object):
    '''
    Abstract base class for external grader service stubs.

    Subclasses are: 

    * ActiveGraderStub: Uses the REST-like interface for pulling
        and pushing requests to the XQueue.

    * PassiveGraderStub: Waits for XQueue to send it a message,
        then responds synchronously.
    '''

    __metaclass__ = ABCMeta

    def __init__(self):
        '''
        Initialize the grader
        '''
        self._delay = 0.0

    @staticmethod
    def build_response(submission_id, submission_key, score_msg):
        '''
        Construct a valid xqueue response

        submission_id: Graded submission's database ID in xqueue (int)
        submission_key: Secret key to match against XQueue database (string)
        score_msg: Grading result from external grader (string)

        Returns: valid xqueue response (dict)
        '''
        return json.dumps({'xqueue_header': 
                                {'submission_id': submission_id,
                                 'submission_key': submission_key},
                           'xqueue_body': score_msg})

    def get_response(self, submission):
        '''
        Return a response, with the configured delay.
        Delegates to concrete subclass response_for_submission()
        to construct the actual response.

        submission: dict of the form
            {'xqueue_header': {'submission_id': ID,
                                'submission_key': KEY },
            'xqueue_body: STRING,
            'xqueue_files': list of file URLs }

        returns: dict created by subclasss response_for_submission()
        '''

        # If we have a delay set, wait before responding
        if self._delay > 0.0:
            time.sleep(self._delay)

        # Delegate to the concrete subclass to actually
        # construct the response
        return self.response_for_submission(submission)

    @abstractmethod
    def response_for_submission(self, submission):
        '''
        Respond to an XQueue submission.

        Subclasses implement this method, usually to either:

        * Return a pre-defined response from build_response()

        * Forward the call to the actual external grader,
            then return the result.

        * Return an invalid response to test error handling.

        submission: dict of the form
            {'xqueue_header': {'submission_id': ID,
                                'submission_key': KEY },
            'xqueue_body: STRING,
            'xqueue_files': list of file URLs }

        returns: dictionary 

        XQueue expects the dict to be of the form used by
        build_response(), but you can provide invalid responses
        to test error handling.
        '''
        pass

    def set_delay(self, seconds):
        '''
        Specify a delay before responding to a submission.
        The default is to respond immediately.

        seconds: the number of seconds to delay (float)
        '''
        assert(seconds >= 0.0)
        self._delay = seconds


class ActiveGraderStub(object):
    '''
    Stub for external grader service that pulls messages from the queue
    using the LMS interface and pushes responses using a REST-like
    interface.

    To better simulate real-world conditions, the external grader
    runs in its own thread.

    Concrete subclasses need to implement response_for_submission()
    '''

    __metaclass__ = ABCMeta

    def __init__(self, queuename):
        '''
        Create the external grader and start polling
        for messages in a particular queue.

        queuename: name of the queue to poll (string)
        '''
        raise NotImplemented


    def stop(self):
        '''
        Stops polling the queue for new submissions.
        '''
        raise NotImplemented


class GradingRequestHandler(BaseHTTPRequestHandler):
    '''
    HTTP request handler for grading requests from xqueue
    to the passive external grader.

    Test cases shouldn't need to use this directly;
    they can use PassiveGraderStub instead.
    '''

    protocol = "HTTP/1.0" 

    def do_POST(self):
        '''
        Parses the request, then 
        delegates to the server to construct the response.
        '''
        # Get the length of the request
        length = int(self.headers.getheader('content-length'))

        # Retrieve the POST dict, which has the form:
        # { POST_PARAM: [ POST_VAL_1, POST_VAL_2, ...], ... }
        # 
        # Note that each key in POST dict is a list, even
        # if the list has only 1 value.
        post_dict = urlparse.parse_qs(self.rfile.read(length))

        # Get a submission dict from the POST dict
        try:
            submission = self._parse_post_dict(post_dict)

        # If we could not process the request, log it
        # and ignore the request
        except ValueError:

            # Respond with failure
            self.send_response(500)
            self.send_headers('Content-type', 'text/plain')
            self.end_headers()

            logger.warning('Could not retrieve submission from POST request')

        # Otherwise, process the submission
        else:

            # Delegate to the server to construct the response
            # This will be a concrete subclass of PassiveGraderStub
            response = self.server.response_for_submission(submission)

            # Respond with success
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()

            # Send the response

    def _parse_post_dict(self, post_dict):
        '''
        post_dict: a dict of the form
            { POST_PARAM: [ POST_VAL_1, POST_VAL_2, ...], ... }

        returns: dict of the form
            {'xqueue_header': {'submission_id': ID,
                                'submission_key': KEY },
            'xqueue_body: STRING,
            'xqueue_files': list of file URLs }
        
        raises KeyError if the post_dict did not contain expected keys
        raises ValueError if the post_dict values could not be parsed
            as valid JSON.
        '''

        # Retrieve the keys we need
        # If the value is one element, we return just that
        # element, not the list.
        xqueue_header = json.loads(post_dict['xqueue_header'][0])
        xqueue_body = post_dict['xqueue_body'][0]
        xqueue_files = post_dict['xqueue_files']

        return {'xqueue_header': xqueue_header,
                'xqueue_body': xqueue_body,
                'xqueue_files': xqueue_files}

class PassiveGraderStub(ForkingMixIn, HTTPServer):
    '''
    Stub for external grader service that responds to submissions
    it receives directly from the XQueue.

    It does so by establishing a simple HTTP server listening
    on a local port.  Since it needs to respond asynchronously
    to multiple (possibly simultaneous) submissions, it
    forks new processes to handle each request.

    Concrete subclass need to implement response_for_submission()
    '''

    @classmethod
    def start_workers(cls, queue_name, destination_port, num_workers=1):
        '''
        We need to start workers (consumers) to pull messages
        from the queue and pass them to our passive grader.

        queue_name: The name of the queue to pull messages from (string)

        destination_port: The local port to forward messages to
            (the one our grader stub is listening on)

        num_workers: The number of workers to start for this queue (int)

        Raises an AssertionError if trying to start workers before
        stopping the current workers.
        '''
        if hasattr(cls, 'worker_list'):
            assert(len(cls.worker_list) > 0)

        else:
            cls.worker_list = []

        for i in range(num_workers):
            destination_url = 'http://127.0.0.1:%d' % int(destination_port)
            worker = Worker(queue_name=queue_name,
                            worker_url=destination_url)
            worker.start()
            cls.worker_list.append(worker)

    @classmethod
    def stop_workers(cls):
        '''
        Stop all workers we created earlier.
        
        Raises an AssertionError if called without first calling
        start_workers()
        '''
        assert(hasattr(cls, 'worker_list'))

        for worker in cls.worker_list:
            worker.stop()

    def __init__(self, port_num):
        '''
        Create the stub and start listening on a local port

        port_num: The local port to listen on (int)
        '''
        address = ('', port_num)
        HTTPServer.__init__(self, address, GradingRequestHandler)

    def stop(self):
        '''
        Stop listening on the local port and close the socket
        '''
        self.shutdown()

        # We also need to manually close the socket, so it can
        # be re-used later
        self.socket.close()


class LoggingRequestHandler(BaseHTTPRequestHandler):
    '''
    HTTPRequestHandler that logs requests from the XQueue server
    for later retrieval.

    Test cases shouldn't need to use this directly; instead, they
    can use GradeResponseListener.
    '''

    protocol = "HTTP/1.0" 

    def do_POST(self):
        '''
        Store the request and respond with success

        '''
        # Get the length of the request
        length = int(self.headers.getheader('content-length'))

        # Retrieve the POST dict, which has the form:
        # { POST_PARAM: [ POST_VAL_1, POST_VAL_2, ...], ... }
        # 
        # Note that each key in POST dict is a list, even
        # if the list has only 1 value.
        post_dict = urlparse.parse_qs(self.rfile.read(length))

        self.server.log_post_request(post_dict)

        # Respond with success
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()


class GradeResponseListener(ThreadingMixIn, HTTPServer):
    '''
    Listens to a local callback port and
    records grade responses from the xqueue.
    '''

    def __init__(self, listen_port):
        '''
        Start listening on a local port for responses from the xqueue

        listen_port: the local port xqueue will POST responses to (int)
        '''
        # Create an empty list in which to store request records
        self._request_list = []

        # Create and start the server
        address = ('', listen_port)
        HTTPServer.__init__(self, address, LoggingRequestHandler)

    def get_grade_responses(self):
        '''
        Retrieves record of POST requests received

        Returns: list of dictionaries of the form
            {'datetime_received': datetime, 'post_dict': dict}

        The POST dict has the form
        { POST_PARAM: [ POST_VAL_1, POST_VAL_2, ...], ... }

        where each entry is a list, even if it has only 1 value
        '''
        return self._request_list

    def log_post_request(self, post_dict):
        '''
        Store that a POST request was received.
        Called by LoggingRequestHandler when it receives POST requests
        from the xqueue.

        post_dict: dictionary of the form
            { POST_PARAM: [ POST_VAL_1, POST_VAL_2, ...], ... }

        where each entry is a list, even if it has only 1 value
        '''

        request_record = {'datetime_received': datetime.datetime.now(),
                            'post_dict': post_dict }


        # Python lists are thread-safe, so 
        # we can add to the list even if log_post_request()
        # is called from multiple threads simultaneously.
        self._request_list.append(request_record)

    def stop(self):
        '''
        Stop listening on the local port and close the socket
        '''
        self.shutdown()

        # We also need to manually close the socket, so it can
        # be re-used later
        self.socket.close()

    def block_until(self, poll_func, sleep_time=0.1, timeout=10.0):
        '''
        Block until the grade response listener is in a certain state,
        or we time out.

        For example, a test case might poll until the listener
        receives 5 messages.

        If the condition is not met within timeout, then the function
        returns.

        poll_func: A function of the form (GradeResponseListener) -> boolean
            If poll_func returns True, stop blocking and return.
            If poll_func returns False, continue polling.

        sleep_time: The number of seconds to sleep 
            between calls to poll_func (float)

        timeout: The maximum number of seconds to poll (float)

        returns: True if poll_func was successful
                False if we timed out
        '''

        last_time = datetime.datetime.now()
        total_time = 0.0

        # While we still have time 
        while total_time < timeout:

            # We satisfy the poll condition, return True
            if poll_func(self):
                return True

            # Otherwise: wait, then retry
            else:

                # Wait the specified amount of time before retrying
                time.sleep(sleep_time)

                # Update elapsed time
                now = datetime.datetime.now()
                total_time += (now - last_time)
                last_time = now

        # We timed out, so return False
        return False


class XQueueTestClient(Client):
    '''
    Client that simulates input to the XQueue

    Since this is a subclass of Django's test client,
    we can use it to login and send HTTP requests.
    '''
    
    def __init__(self, callback_port):
        '''
        Create a test client for interacting with the xqueue.

        callback_port: The local port for the xqueue to POST callback
            responses to.
        '''
        self._callback_port = callback_port
        super(XQueueTestClient, self).__init__()

    def build_request(self, queuename,
                            grader_payload=None,
                            submission_time=None,
                            student_response=""):
        '''
        Create a valid xqueue request.

        queuename: The name of the queue to send the request to.
            This should be the same queue that workers are pulling messages
            from (string)

        grader_payload: Information to pass to the grader service (dict)
            Defaults to an empty dict.

        submission_time: The timestamp of the request.  If not specified,
            defaults to the current time.
            XQueue expects a string formatted "YYYYmmddhhmmss"
            (e.g. 20130403114106 for 04-03-2013 at 11:41:06)
            However, you can specify invalid strings to test how
            xqueue and external graders respond.

        student_response: The response the student submitted.

        Returns a JSON-encoded string representing the request.
        '''
        if grader_payload is None:
            grader_payload = {}

        if submission_time is None:
            submission_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

        header = {'lms_callback_url': self._callback_url(),
                'lms_key': 'not used',
                'queue_name': queuename }

        content = json.dumps({'grader_payload': grader_payload,
                            'submission_time': submission_time,
                            'student_response': student_response })

        return {'xqueue_header': header, 'xqueue_body': content }

    def send_request(self, request):
        '''
        Send a request to the xqueue.

        request: The request to send to the server (JSON-encoded string)
            Usually you would create this using build_request().
            In some cases, it may be useful to mutate the request before
            sending it, to test how xqueue responds.

        Returns the status code of the request.
        '''
        response = self.post(reverse('submit'), request)
        return response.status_code

    def _callback_url(self):
        '''
        Construct a callback url from the local port

        returns: local url (string)
        '''
        return 'http://127.0.0.1:%d' % self._callback_port
