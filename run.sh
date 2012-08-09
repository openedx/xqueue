#!/bin/sh

gunicorn --workers=4 -b 127.0.0.1:3031 xqueue.wsgi &
