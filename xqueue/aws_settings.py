from settings import *
import json
from logsettings import get_logger_config

# Allow to specify a prefix for env/auth configuration files
SERVICE_VARIANT = os.environ.get('SERVICE_VARIANT', '')
if SERVICE_VARIANT:
    CONFIG_PREFIX = SERVICE_VARIANT + "."

with open(ENV_ROOT / CONFIG_PREFIX + "env.json") as env_file:
    ENV_TOKENS = json.load(env_file)

XQUEUES = ENV_TOKENS['XQUEUES']
XQUEUE_WORKERS_PER_QUEUE = ENV_TOKENS['XQUEUE_WORKERS_PER_QUEUE']
WORKER_COUNT = ENV_TOKENS.get('WORKER_COUNT', XQUEUE_WORKERS_PER_QUEUE * 2)
S3_BUCKET = ENV_TOKENS.get('S3_BUCKET', S3_BUCKET)
S3_PATH_PREFIX = ENV_TOKENS.get('S3_PATH_PREFIX', S3_PATH_PREFIX)

ALLOWED_HOSTS = ENV_TOKENS.get('ALLOWED_HOSTS', ALLOWED_HOSTS)

LOG_DIR = ENV_TOKENS['LOG_DIR']
local_loglevel = ENV_TOKENS.get('LOCAL_LOGLEVEL', 'INFO')
TIME_ZONE = ENV_TOKENS.get('TIME_ZONE', TIME_ZONE)

LOGGING = get_logger_config(LOG_DIR,
                            logging_env=ENV_TOKENS['LOGGING_ENV'],
                            syslog_addr=(ENV_TOKENS['SYSLOG_SERVER'], 514),
                            local_loglevel=local_loglevel,
                            debug=False)

RABBIT_HOST = ENV_TOKENS.get('RABBIT_HOST', RABBIT_HOST).encode('ascii')
RABBIT_VHOST = ENV_TOKENS.get('RABBIT_VHOST', RABBIT_VHOST).encode('ascii')
with open(ENV_ROOT / CONFIG_PREFIX + "auth.json") as auth_file:
    AUTH_TOKENS = json.load(auth_file)

DATABASES = AUTH_TOKENS['DATABASES']

AWS_ACCESS_KEY_ID = AUTH_TOKENS["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = AUTH_TOKENS["AWS_SECRET_ACCESS_KEY"]

REQUESTS_BASIC_AUTH = AUTH_TOKENS["REQUESTS_BASIC_AUTH"]
RABBITMQ_USER = AUTH_TOKENS.get('RABBITMQ_USER', 'guest').encode('ascii')
RABBITMQ_PASS = AUTH_TOKENS.get('RABBITMQ_PASS', 'guest').encode('ascii')
XQUEUE_USERS = AUTH_TOKENS.get('USERS', None)
