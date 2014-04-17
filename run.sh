#!/bin/sh

gunicorn --keep-alive=30 --workers=4 -b 127.0.0.1:3031 -k gevent -D xqueue.wsgi
