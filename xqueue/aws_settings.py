from settings import *
import json
from logsettings import get_logger_config

with open(ENV_ROOT / "env.json") as env_file:
    ENV_TOKENS = json.load(env_file)

XQUEUES = ENV_TOKENS['XQUEUES']
XQUEUE_WORKERS_PER_QUEUE = ENV_TOKENS['XQUEUE_WORKERS_PER_QUEUE']

LOG_DIR = ENV_TOKENS['LOG_DIR']
local_loglevel = ENV_TOKENS.get('LOCAL_LOGLEVEL','INFO')

LOGGING = get_logger_config(LOG_DIR,
                            logging_env=ENV_TOKENS['LOGGING_ENV'],
                            syslog_addr=(ENV_TOKENS['SYSLOG_SERVER'], 514),
                            local_loglevel=local_loglevel,
                            debug=False)

with open(ENV_ROOT / "auth.json") as auth_file:
    AUTH_TOKENS = json.load(auth_file)

DATABASES = AUTH_TOKENS['DATABASES']

AWS_ACCESS_KEY_ID = AUTH_TOKENS["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = AUTH_TOKENS["AWS_SECRET_ACCESS_KEY"]

REQUESTS_BASIC_AUTH = AUTH_TOKENS["REQUESTS_BASIC_AUTH"]
