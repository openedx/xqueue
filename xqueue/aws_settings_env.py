from .aws_settings import *

import os

DB_OVERRIDES = dict(
    PASSWORD=os.environ.get('XQUEUE_MYSQL_PASSWORD', None),
    USER=os.environ.get('XQUEUE_MYSQL_USER', None),
    NAME=os.environ.get('XQUEUE_MYSQL_DB_NAME', None),
    HOST=os.environ.get('XQUEUE_MYSQL_HOST', None),
    PORT=os.environ.get('XQUEUE_MYSQL_PORT', None),
)

for override, value in DB_OVERRIDES.iteritems():
    if value:
        DATABASES['default'][override] = value
