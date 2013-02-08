"""
  Tests all push queues to ensure that we see a sucessful
  round trip submission
"""
import json
import logging
import SocketServer
import cgi
from BaseHTTPServer import BaseHTTPRequestHandler
from django.core.management.base import BaseCommand
from django.conf import settings
from queue.xqueue_client import XQueueClient

PORT = 8989
logger = logging.getLogger(__name__)
responses = {}


class TCPServerReuse(SocketServer.TCPServer):
    # prevents address already in use errors
    # when the server is started
    allow_reuse_address = True


class ServerHandler(BaseHTTPRequestHandler):
    # handle POSTS from the xserver
    def setup(self):
        self.request.settimeout(self.timeout)
        BaseHTTPRequestHandler.setup(self)

    def do_POST(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST',
                     'CONTENT_TYPE': self.headers['Content-Type'],
                     })
        queue_name = json.loads(form.getvalue('xqueue_header'))['queue_name']
        istrue = json.loads(form.getvalue('xqueue_body'))['correct']
        responses[queue_name] = istrue
        self.send_response(200, "OK")
        self.end_headers()


class Command(BaseCommand):

    help = """
       Test all queues that push to the xserver by submitting hello world.
       If a response is not received it will wait forever
    """

    def handle(self, *args, **options):
        xq_client = XQueueClient(server='http://127.0.0.1:8000',
                                 passwd=settings.XQUEUE_USERS['lms'],
                                 post_url=
                                 'http://stage-xqueue-001.m.edx.org:8989')
        xq_client.login()
        httpd = TCPServerReuse(("", PORT), ServerHandler)
        for queue_name, queue_url in settings.XQUEUES.iteritems():
            if queue_url and 'xserver' in queue_url:
                # only submit to queues that use the xserver
                xq_client.submit_job(queue_name, queue_name)
                logger.info("Waiting for response from {0}".format(queue_name))
                while not queue_name in responses:
                    httpd.handle_request()
