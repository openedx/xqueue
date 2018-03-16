from settings import *
import json

with open(ENV_ROOT / "xqueue.env.json") as env_file:
    ENV_TOKENS = json.load(env_file)

XQUEUES = ENV_TOKENS['XQUEUES']
XQUEUE_WORKERS_PER_QUEUE = ENV_TOKENS['XQUEUE_WORKERS_PER_QUEUE']
WORKER_COUNT = ENV_TOKENS.get('WORKER_COUNT', XQUEUE_WORKERS_PER_QUEUE * 2)

ALLOWED_HOSTS = ENV_TOKENS.get('ALLOWED_HOSTS', ALLOWED_HOSTS)

LOG_DIR = ENV_TOKENS['LOG_DIR']
TIME_ZONE = ENV_TOKENS.get('TIME_ZONE', TIME_ZONE)

# We use the default development logging from settings.py
# but override this to force a console log for docker.
# Stolen from the LMS.
LOGGING['handlers']['local'] = {
    'class': 'logging.NullHandler',
}


RABBIT_HOST = ENV_TOKENS.get('RABBIT_HOST', RABBIT_HOST).encode('ascii')
RABBIT_PORT = ENV_TOKENS.get('RABBIT_PORT', RABBIT_PORT)
RABBIT_VHOST = ENV_TOKENS.get('RABBIT_VHOST', RABBIT_VHOST).encode('ascii')
RABBIT_TLS = ENV_TOKENS.get('RABBIT_TLS', RABBIT_TLS)
with open(ENV_ROOT / "xqueue.auth.json") as auth_file:
    AUTH_TOKENS = json.load(auth_file)

DATABASES = AUTH_TOKENS['DATABASES']

REQUESTS_BASIC_AUTH = AUTH_TOKENS["REQUESTS_BASIC_AUTH"]
RABBITMQ_USER = AUTH_TOKENS.get('RABBITMQ_USER', 'guest').encode('ascii')
RABBITMQ_PASS = AUTH_TOKENS.get('RABBITMQ_PASS', 'guest').encode('ascii')
XQUEUE_USERS = AUTH_TOKENS.get('USERS', None)

# This is all used for file uploads, but some of these uploads are done by the LMS and are
# stored in the s3_urls fields in the submission table.  Using django storage to put these on
# disk would be great, but sharing the disk upload from lms -> xqueue is fascinating.

UPLOAD_BUCKET = ENV_TOKENS.get('UPLOAD_BUCKET', UPLOAD_BUCKET)
UPLOAD_PATH_PREFIX = ENV_TOKENS.get('UPLOAD_PATH_PREFIX', UPLOAD_PATH_PREFIX)
UPLOAD_URL_EXPIRE = ENV_TOKENS.get('UPLOAD_URL_EXPIRE', UPLOAD_URL_EXPIRE)

AWS_ACCESS_KEY_ID = AUTH_TOKENS["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = AUTH_TOKENS["AWS_SECRET_ACCESS_KEY"]

# Use S3 as the default storage backend
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
AWS_STORAGE_BUCKET_NAME = UPLOAD_BUCKET
AWS_LOCATION = UPLOAD_PATH_PREFIX
AWS_QUERYSTRING_EXPIRE = ENV_TOKENS.get('UPLOAD_URL_EXPIRE', UPLOAD_URL_EXPIRE)

# It's probably ok to search your DB for push queues every minute (or even longer) on a
# development instance, rather than the brief prod timespan.
CONSUMER_DELAY = 60
