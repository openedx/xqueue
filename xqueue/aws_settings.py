import json
import os

from django.conf import global_settings

from logsettings import get_logger_config
from settings import *

with open(ENV_ROOT / "xqueue.env.json") as env_file:
    ENV_TOKENS = json.load(env_file)

XQUEUES = ENV_TOKENS['XQUEUES']

UPLOAD_BUCKET = ENV_TOKENS.get('UPLOAD_BUCKET', UPLOAD_BUCKET)
UPLOAD_PATH_PREFIX = ENV_TOKENS.get('UPLOAD_PATH_PREFIX', UPLOAD_PATH_PREFIX)
UPLOAD_URL_EXPIRE = ENV_TOKENS.get('UPLOAD_URL_EXPIRE', UPLOAD_URL_EXPIRE)

ALLOWED_HOSTS = ENV_TOKENS.get('ALLOWED_HOSTS', ALLOWED_HOSTS)

LOG_DIR = ENV_TOKENS['LOG_DIR']
local_loglevel = ENV_TOKENS.get('LOCAL_LOGLEVEL', 'INFO')
TIME_ZONE = ENV_TOKENS.get('TIME_ZONE', TIME_ZONE)

LOGGING = get_logger_config(LOG_DIR,
                            logging_env=ENV_TOKENS['LOGGING_ENV'],
                            syslog_addr=(ENV_TOKENS['SYSLOG_SERVER'], 514),
                            local_loglevel=local_loglevel,
                            debug=False)

with open(ENV_ROOT / "xqueue.auth.json") as auth_file:
    AUTH_TOKENS = json.load(auth_file)

SUBMISSION_PROCESSING_DELAY = ENV_TOKENS.get('SUBMISSION_PROCESSING_DELAY', SUBMISSION_PROCESSING_DELAY)
CONSUMER_DELAY = ENV_TOKENS.get('CONSUMER_DELAY', CONSUMER_DELAY)

DATABASES = AUTH_TOKENS['DATABASES']
# The normal database user does not have enough permissions to run migrations.
# Migrations are run with separate credentials, given as DB_MIGRATION_*
# environment variables
DATABASES['default'].update({
    'ENGINE': os.environ.get('DB_MIGRATION_ENGINE', DATABASES['default']['ENGINE']),
    'USER': os.environ.get('DB_MIGRATION_USER', DATABASES['default']['USER']),
    'PASSWORD': os.environ.get('DB_MIGRATION_PASS', DATABASES['default']['PASSWORD']),
    'NAME': os.environ.get('DB_MIGRATION_NAME', DATABASES['default']['NAME']),
    'HOST': os.environ.get('DB_MIGRATION_HOST', DATABASES['default']['HOST']),
    'PORT': os.environ.get('DB_MIGRATION_PORT', DATABASES['default']['PORT']),
})

AWS_ACCESS_KEY_ID = AUTH_TOKENS.get("AWS_ACCESS_KEY_ID", AWS_ACCESS_KEY_ID)
AWS_SECRET_ACCESS_KEY = AUTH_TOKENS.get("AWS_SECRET_ACCESS_KEY", AWS_SECRET_ACCESS_KEY)

REQUESTS_BASIC_AUTH = AUTH_TOKENS["REQUESTS_BASIC_AUTH"]
XQUEUE_USERS = AUTH_TOKENS.get('USERS', None)

# Use S3 as the default storage backend
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
AWS_STORAGE_BUCKET_NAME = UPLOAD_BUCKET
AWS_LOCATION = UPLOAD_PATH_PREFIX
AWS_QUERYSTRING_EXPIRE = ENV_TOKENS.get('UPLOAD_URL_EXPIRE', UPLOAD_URL_EXPIRE)

# Use session engine settings from env
SESSION_ENGINE = ENV_TOKENS.get('SESSION_ENGINE') or global_settings.SESSION_ENGINE
# Use a custom cache setting from env; useful if, for example, the session engine uses cache and requires Memcached
CACHES = ENV_TOKENS.get('CACHES') or global_settings.CACHES

# To use newrelic agent from a management command, we need the app name and the license key
# In order to register the agent with the license key it needs to be in the environment (or an otherwise
# unused config file) before the later import of the agent by the command.
NEWRELIC_APPNAME = ENV_TOKENS.get('NEWRELIC_APPNAME', NEWRELIC_APPNAME)
if not os.environ.get('NEW_RELIC_LICENSE_KEY', '') and AUTH_TOKENS.get('NEWRELIC_LICENSE_KEY', ''):
    os.environ['NEW_RELIC_LICENSE_KEY'] = AUTH_TOKENS.get('NEWRELIC_LICENSE_KEY')
