"""
Framework for writing integration tests for xqueue and external
graders at the level of HTTP requests.
Basic xqueue communication:

1)    XQueueTestClient --(push)--> xqueue --(push/pull)--> GraderStub subclass

2)    GraderStub subclass --(push)--> xqueue --(push)--> GradeResponseListener

Test cases verify that the output to GradeResponseListener given
inputs specified by XQueueTestClient.


How messages get routed (PassiveGraderStub):

The test client sends messages to a particular queue.

XQueue checks its settings and finds that the queue has
a URL associated with it.  XQueue forwards the message to that URL.

PassiveGraderStub is listening at the URL and receives a POST request
from XQueue.  The stub responds synchronously with the graded response.

XQueue forwards grading responses to GradeResponseListener using
the callback_url provided by the test client.


How messages get routed (ActiveGraderStub):

The test client sends messages to a particular queue.
XQueue puts the messages in a RabbitMQ queue.

The ActiveGraderStub polls the XQueue using a REST-like interface.
When it receives a submission, it pushes a response back to XQueue
using the REST-like interface.

XQueue pushes the response back to the LMS.


Failure injection:

This framework also makes it easy to inject failure into the system:
for example, by configuring ExternalGraderStub to stop responding
to messages, or to send invalid responses.


RabbitMQ Requirement:

Integration tests currently require that rabbitmq is running.
You can start rabbitmq using the commands:

    rabbitmq-server
    rabbitmqctl start_app

See the installation guides at http://www.rabbitmq.com/download.html
for platform-specific instructions.


Jenkins:

XQueue's current design makes it difficult to test in a
continuous integration environment.
Here are some of the conflicts that can occur:

    1) Because workers run in separate threads and each access
        the database, we cannot use an in-memory database.
        File-based databases need unique names in order
        to avoid conflicts.

    2) Because workers pull messages from rabbitmq queues,
        the queue names need to be unique.  Otherwise,
        a test might pull a message created by another test.

The integration tests use open local ports and free the ports
for re-use when finished to avoid TCP port conflicts.
"""

from django.test.client import Client
from django.contrib.auth.models import User
from django.conf import settings
import datetime
import time
import json
from abc import ABCMeta, abstractmethod
from queue.consumer import Worker
import urlparse
import threading
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn, ForkingMixIn
import pika

import logging
logger = logging.getLogger(__name__)

# Suppress low-level network messages
# from rabbitmq (pika) and requests
logging.getLogger('pika').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)


class GraderStubBase(object):
    """Abstract base class for external grader service stubs.

    We make this abstract to accommodate the two kinds of grading servers:

    * Active: Uses the REST-like interface for pulling
        and pushing requests to the XQueue.


    * Passive: Waits for XQueue to send it a message,
        then responds synchronously."""

    __metaclass__ = ABCMeta

    @staticmethod
    def build_response(submission_id, submission_key, score_msg):
        """Construct a valid xqueue response

        `submission_id`: Graded submission's database ID in xqueue (int)
        `submission_key`: Secret key to match against XQueue database (string)
        `score_msg`: Grading result from external grader (string)

        Returns: valid xqueue response (dict)"""
        return json.dumps({'xqueue_header':
                          {'submission_id': submission_id,
                           'submission_key': submission_key},
                           'xqueue_body': score_msg})

    @abstractmethod
    def response_for_submission(self, submission):
        """Respond to an XQueue submission.

        Subclasses implement this method, usually to either:

        * Return a pre-defined response from `build_response()`

        * Forward the call to the actual external grader,
            then return the result.

        * Return an invalid response to test error handling.

        `submission`: dict of the form
            {'xqueue_header': {'submission_id': ID,
                                'submission_key': KEY },
            'xqueue_body: STRING,
            'xqueue_files': list of file URLs }

        returns: dictionary

        XQueue expects the dict to be of the form used by
        `build_response()`, but you can provide invalid responses
        to test error handling."""
        pass

    @staticmethod
    def delete_queue(queue_name):
        """Delete the queue named queue_name.

        Use this to clean up queues created implicitly when
        using XQueue."""

        # Establish a connection to the broker
        creds = pika.PlainCredentials(settings.RABBITMQ_USER,
                                      settings.RABBITMQ_PASS)

        params = pika.ConnectionParameters(credentials=creds,
                                           host=settings.RABBIT_HOST,
                                           port=settings.RABBIT_PORT,
                                           virtual_host=settings.RABBIT_VHOST,
                                           ssl=settings.RABBIT_TLS)

        connection = pika.BlockingConnection(parameters=params)
        channel = connection.channel()
        channel.queue_delete(queue=queue_name)


class GradingRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for grading requests from xqueue
    to the passive external grader.

    Test cases shouldn't need to use this directly;
    they can use PassiveGraderStub instead."""

    protocol = "HTTP/1.0"

    def do_POST(self):
        """Parses the request, then
        delegates to the server to construct the response."""

        # Get the length of the request
        length = int(self.headers.getheader('content-length'))

        # Parse the POST data, which XQueue sends to
        # us as directly-encoded JSON
        post_data = self.rfile.read(length)

        try:
            submission = json.loads(post_data)

        # If we could not process the request, log it
        # and respond with failure
        except ValueError:

            # Respond with failure
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
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
            response_str = json.dumps(response)
            self.wfile.write(response_str)


class PassiveGraderStub(ForkingMixIn, HTTPServer, GraderStubBase):
    """Stub for external grader service that responds to submissions
    it receives directly from the XQueue.

    It does so by establishing a simple HTTP server listening
    on a local port.  Since it needs to respond asynchronously
    to multiple (possibly simultaneous) submissions, it
    forks new processes to handle each request.

    Concrete subclass need to implement `response_for_submission()`"""

    @classmethod
    def start_workers_for_grader_url(cls, queue_name,
                                     destination_url, num_workers=1):
        """We need to start workers (consumers) to pull messages
        from the queue and pass them to our passive grader.

        `queue_name`: The name of the queue to pull messages from (string)

        `destination_url`: The url to forward responses to.

        `num_workers`: The number of workers to start for this queue (int)

        Raises an `AssertionError` if trying to start workers before
        stopping the current workers."""
        if hasattr(cls, 'worker_list'):
            assert(len(cls.worker_list) > 0)

        else:
            cls.worker_list = []

        for i in range(num_workers):
            worker = Worker(queue_name=queue_name, worker_url=destination_url)

            # There is a bug in pika on Mac OS X
            # in which using multithreading.Process with
            # pika's ioloop causes an IncompatibleProtocolError
            # to be raised.
            # The workaround for now is to run each worker
            # as a separate thread.
            worker_thread = threading.Thread(target=worker.run)
            worker_thread.daemon = True
            worker_thread.start()

            cls.worker_list.append(worker)

    @classmethod
    def stop_workers(cls):
        """Stop all workers we created earlier.

        Raises an AssertionError if called without first calling
        `start_workers()`"""
        assert(hasattr(cls, 'worker_list'))

        for worker in cls.worker_list:
            worker.stop()

    def __init__(self):
        """Create the stub and start listening on a local port"""

        # Choose a local open port
        address = ('', 0)

        # Start the server
        HTTPServer.__init__(self, address, GradingRequestHandler)
        self.start()

    def start(self):
        """Start the listener in a separate thread"""
        server_thread = threading.Thread(target=self.serve_forever)
        server_thread.daemon = True
        server_thread.start()

    def stop(self):
        """Stop listening on the local port and close the socket"""
        self.shutdown()

        # We also need to manually close the socket, so it can
        # be re-used later
        self.socket.close()

    def grader_url(self):
        """Returns the URL for the local port we are listening on"""
        port_num = self.socket.getsockname()[1]
        return "http://127.0.0.1:%d" % port_num

    def start_workers(self, queue_name, num_workers=1):
        """Start workers that will forward submissions
        to the port the grader stub is listening on

        `queue_name`: The name of the queue to pull messages from (string)

        `num_workers`: The number of workers to start for this queue (int)

        Raises an `AssertionError` if trying to start workers before
        stopping the current workers."""
        PassiveGraderStub.start_workers_for_grader_url(queue_name,
                                                       self.grader_url(),
                                                       num_workers=num_workers)


class ActiveGraderStub(GraderStubBase):
    """Stub for an active grader, which polls the XQueue for new
    submissions, processes the submissions, then pushes
    responses back to the XQueue.  It uses XQueue's REST-like interface.

    It runs a daemon thread to asynchronously poll the XQueue."""

    SLEEP_TIME = 0.5

    USERNAME = 'active_grader'
    PASSWORD = 'password'

    _poll_thread = None
    _is_polling = True
    _queue_name = None

    def __init__(self, queue_name):
        """Start polling the Xqueue for new submissions"""

        # Store the queue name, so we know
        # which queue to poll
        self._queue_name = queue_name

        # Create a logged-in Django test client
        # to interact with the XQueue
        XQueueTestClient.create_user(ActiveGraderStub.USERNAME,
                                    ActiveGraderStub.USERNAME + '@edx.org',
                                    ActiveGraderStub.PASSWORD)
        self._client = XQueueTestClient(0)
        self._client.login(username=ActiveGraderStub.USERNAME,
                            password=ActiveGraderStub.PASSWORD)

        # The polling thread will run until
        # this flag is set to False
        self._is_polling = True

        # Start polling the XQueue
        self._poll_thread = threading.Thread(target=self.poll)
        self._poll_thread.daemon = True
        self._poll_thread.start()

    def stop(self):
        """Stop polling the XQueue"""
        self._is_polling = False

    def poll(self):
        """Poll the XQueue for new submissions, delegating
        to concrete subclasses to determine the response."""

        # Check the running flag
        while self._is_polling:

            # Try to get a submission
            submission = self._pop_submission()

            # If we can't get one now, wait a bit then retry
            if submission is None:
                time.sleep(ActiveGraderStub.SLEEP_TIME)

            # Otherwise, process the submission
            # and push a response back to the XQueue
            else:

                # Delegate to the concrete base class
                # to create a response
                response = self.response_for_submission(submission)

                # Push the response back to the XQueue
                self._push_response(response)

    def _pop_submission(self):
        """Attempts to pop a submission from the XQueue.
        If it succeeds, it returns a `dict` of the submission info,
        which has keys `xqueue_header` and `xqueue_body`
        (and sometimes `xqueue_files` as well).

        The `xqueue_header` is itself a JSON-decoded dict,
        but `xqueue_body` is a string.

        If no submission is available, or an error occurs,
        returns None."""

        # Use the Django test client to retrieve a submission
        # from our queue
        response = self._client.get('/xqueue/get_submission/',
                                    {'queue_name': self._queue_name})

        # If any kind of HTTP error occurred,
        # log it and return None
        if response.status_code != 200:
            logger.warning('Could not get submission from XQueue: status = %d',
                            response.status_code)
            return None

        # Otherwise the response was successful
        else:

            # JSON-decode the response
            response_dict = json.loads(response.content)

            # Check that we successfully retrieved a submission
            if response_dict['return_code'] == 0:

                # If so, JSON-decode the submission and
                # return the resulting dict
                submission_dict = json.loads(response_dict['content'])
                xqueue_header = json.loads(submission_dict['xqueue_header'])
                xqueue_body = submission_dict['xqueue_body']
                return {'xqueue_header': xqueue_header,
                        'xqueue_body': xqueue_body}

            # Otherwise, we could not retrieve the submission,
            # usually because the queue is empty.
            else:
                return None

    def _push_response(self, response_dict):
        """Push a response back to the XQueue.
        `response_dict` is a JSON-serializable dictionary
        with keys `xqueue_header` and `xqueue_body`,
        both JSON-serialized strings.

        Returns `True` if successful, `False` otherwise."""

        # Construct the response
        xqueue_header = response_dict['xqueue_header']
        xqueue_body = response_dict['xqueue_body']

        post_params = {'xqueue_header': json.dumps(xqueue_header),
                        'xqueue_body': json.dumps(xqueue_body) }

        # Use the Django test client to POST a response
        # back to the XQueue
        response = self._client.post('/xqueue/put_result/', post_params)

        # Check the status code, and log a warning if we failed
        if response.status_code != 200:
            logger.warning('Could not push response to XQueue: status=%d',
                             response.status_code)
            return False

        else:
            # Check the response's return_code and log a warning if we failed
            response_dict = json.loads(response.content)
            if response_dict['return_code'] != 0:
                logger.warning('Could not submit response to XQueue: %s',
                                response_dict['content'])
                return False

            # Otherwise, everything was successful
            else:
                return True

class LoggingRequestHandler(BaseHTTPRequestHandler):
    """HTTPRequestHandler that logs requests from the XQueue server
    for later retrieval.

    Test cases shouldn't need to use this directly; instead, they
    can use GradeResponseListener."""

    protocol = "HTTP/1.0"

    def do_POST(self):
        """Store the request and respond with success"""

        # Send header information
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

        # Get the length of the request
        length = int(self.headers.getheader('content-length'))

        # Retrieve the POST dict, which has the form:
        # { POST_PARAM: [ POST_VAL_1, POST_VAL_2, ...], ... }
        #
        # Note that each key in POST dict is a list, even
        # if the list has only 1 value.
        post_dict = urlparse.parse_qs(self.rfile.read(length))

        # Try to parse the grade response
        try:
            grade_response = self._parse_post_dict(post_dict)

        except KeyError:
            logger.warning('Received grade response with missing or invalid keys')
            self.send_response(500)

        except ValueError:
            logger.warning('Could not parse JSON grade response')
            self.send_response(500)

        else:
            # Store the response
            self.server.log_grade_response(grade_response)

            # Respond with success
            self.send_response(200)

    def _parse_post_dict(self, post_dict):
        """`post_dict`: a dict of the form
            `{ POST_PARAM: [ POST_VAL_1, POST_VAL_2, ...], ... }`

        returns: dict of the form
            `{'xqueue_header': DICT, 'xqueue_body: DICT }`

        raises `KeyError` if the post_dict did not contain expected keys
        raises `ValueError` if the post_dict values could not be parsed
            as valid JSON. """

        # Retrieve the keys we need
        # If the value is one element, we return just that
        # element, not the list.
        xqueue_header = json.loads(post_dict['xqueue_header'][0])
        xqueue_body = json.loads(post_dict['xqueue_body'][0])

        return {'xqueue_header': xqueue_header, 'xqueue_body': xqueue_body}


class GradeResponseListener(ThreadingMixIn, HTTPServer):
    """Listens to a local callback port and records grade responses from the xqueue """

    def __init__(self):
        """Start listening on a local port for responses from the xqueue"""
        # Create an empty list in which to store request records
        self._request_list = []

        # Choose an open local port
        address = ('', 0)

        # Create and start the server
        HTTPServer.__init__(self, address, LoggingRequestHandler)
        self.start()

    def get_grade_responses(self):
        """Retrieves record of grade responses received

        Returns: list of dictionaries of the form
            `{'datetime_received': datetime, 'response': dict}`

        response is usually (but not necessarily) a dict of the form
        `{'xqueue_header': dict, 'xqueue_body': dict }`"""
        return self._request_list

    def log_grade_response(self, response_dict):
        """Store that a POST request was received.
        Called by LoggingRequestHandler when it receives POST requests
        from the xqueue.

        `response_dict` is any dictionary"""

        request_record = {'datetime_received': datetime.datetime.now(),
                          'response': response_dict}

        # Python lists are thread-safe, so
        # we can add to the list even if log_post_request()
        # is called from multiple threads simultaneously.
        self._request_list.append(request_record)

    def start(self):
        """Start the listener in a separate thread"""
        server_thread = threading.Thread(target=self.serve_forever)
        server_thread.daemon = True
        server_thread.start()

    def stop(self):
        """Stop listening on the local port and close the socket"""
        self.shutdown()

        # We also need to manually close the socket, so it can
        # be re-used later
        self.socket.close()

    def block_until(self, poll_func, sleep_time=0.1, timeout=10.0):
        """Block until the grade response listener is in a certain state,
        or we time out.

        For example, a test case might poll until the listener
        receives 5 messages.

        If the condition is not met within timeout, then the function
        returns.

        `poll_func`: A function of the form (GradeResponseListener) -> boolean
            If poll_func returns True, stop blocking and return.
            If poll_func returns False, continue polling.

        `sleep_time`: The number of seconds to sleep
            between calls to `poll_func` (float)

        `timeout`: The maximum number of seconds to poll (float)

        returns: True if poll_func was successful
                False if we timed out"""

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
                total_time += (now - last_time).total_seconds()
                last_time = now

        # We timed out, so return False
        return False

    def port_num(self):
        """Return the local port we are listening on"""
        return self.socket.getsockname()[1]


class XQueueTestClient(Client):
    """Client that simulates input to the XQueue

    Since this is a subclass of Django's test client,
    we can use it to login and send HTTP requests."""

    @staticmethod
    def create_user(username, email, password):
        """Utility to create a user (if one does not already exist)

        username: string
        email: string
        password: string"""
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            User.objects.create_user(username, email, password)

    def __init__(self, callback_port):
        """Create a test client for interacting with the xqueue.

        callback_port: The local port for the xqueue to POST callback
            responses to."""
        self._callback_port = callback_port
        super(XQueueTestClient, self).__init__()

    def build_request(self, queuename,
                      grader_payload=None,
                      submission_time=None,
                      student_response=""):
        """Create a valid xqueue request.

        `queuename`: The name of the queue to send the request to.
            This should be the same queue that workers are pulling messages
            from (string)

        `grader_payload`: Information to pass to the grader service (dict)
            Defaults to an empty dict.

        `submission_time`: The timestamp of the request.  If not specified,
            defaults to the current time.
            XQueue expects a string formatted "YYYYmmddhhmmss"
            (e.g. 20130403114106 for 04-03-2013 at 11:41:06)
            However, you can specify invalid strings to test how
            xqueue and external graders respond.

        `student_response`: The response the student submitted.

        Returns a JSON-encoded string representing the request."""
        if grader_payload is None:
            grader_payload = {}

        if submission_time is None:
            submission_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

        header = json.dumps({'lms_callback_url': self._callback_url(),
                            'lms_key': 'not used',
                            'queue_name': queuename})

        content = json.dumps({'grader_payload': grader_payload,
                             'submission_time': submission_time,
                             'student_response': student_response})

        return {'xqueue_header': header, 'xqueue_body': content}

    def send_request(self, request):
        """Send a request to the xqueue.

        request: The request to send to the server (JSON-encoded string)
            Usually you would create this using build_request().
            In some cases, it may be useful to mutate the request before
            sending it, to test how xqueue responds.

        Returns the status code of the request."""
        submit_url = '/xqueue/submit/'
        response = self.post(submit_url, request)
        return response.status_code

    def _callback_url(self):
        """Construct a callback url from the local port
        returns: local url (string)"""
        return 'http://127.0.0.1:%d' % self._callback_port
