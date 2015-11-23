"""
WSGI config for xqueue project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xqueue.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
import django
from django.core.wsgi import WSGIHandler


class ForceReadPostHandler(WSGIHandler):
    """WSGIHandler that forces reading POST data before forwarding to the
    application.

    nginx as a proxy expects the backend to respond only after the
    whole body of the request has been read. In some cases (see below)
    the backend starts responding before reading the request. This
    causes nginx to return a 502 error, instead of forwarding the
    proper response to the client, which makes very hard to debug
    problems with the backend.

    Cases where the backend responds early:

    - Early errors from django, for example errors from view decorators.
    - POST request with large payloads, which may get chunked by nginx.
      django sends a 100 Continue response before reading the whole body.

    For more information:
    http://kudzia.eu/b/2012/01/switching-from-apache2-to-nginx-as-reverse-proxy

    """
    def __init__(self):
        django.setup()
        super(ForceReadPostHandler, self).__init__()

    def get_response(self, request):
        data = request.POST.copy()  # read the POST data passing it
        return super(ForceReadPostHandler, self).get_response(request)

application = ForceReadPostHandler()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)
