from .aws_settings import *

import os
from django.core.exceptions import ImproperlyConfigured

DB_OVERRIDES = dict(
    PASSWORD=os.environ.get('DB_MIGRATION_PASS', None),
    ENGINE=os.environ.get('DB_MIGRATION_ENGINE', DATABASES['default']['ENGINE']),
    USER=os.environ.get('DB_MIGRATION_USER', DATABASES['default']['USER']),
    NAME=os.environ.get('DB_MIGRATION_NAME', DATABASES['default']['NAME']),
    HOST=os.environ.get('DB_MIGRATION_HOST', DATABASES['default']['HOST']),
    PORT=os.environ.get('DB_MIGRATION_PORT', DATABASES['default']['PORT']),
)

if DB_OVERRIDES['PASSWORD'] is None:
    raise ImproperlyConfigured("No database password was provided for running "
                               "migrations.  This is fatal.")

for override, value in DB_OVERRIDES.iteritems():
    DATABASES['default'][override] = value
