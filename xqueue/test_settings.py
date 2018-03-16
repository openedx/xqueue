from __future__ import print_function

import json
import os
import os.path
from uuid import uuid4

from logsettings import get_logger_config
from settings import *

log_dir = REPO_PATH / "log"

try:
    os.makedirs(log_dir)
except Exception as e:
    print(e)

LOGGING = get_logger_config(log_dir,
                            logging_env="test",
                            dev_env=True,
                            debug=True)

# If we are running on Jenkins, then expect that
# an environment variable is set for
# the config file directory
JENKINS_CONFIG_DIR = os.environ.get('JENKINS_CONFIG_DIR', None)

# Try to load sensitive information from env.json
# Fail gracefully if  we can't find or parse the file.
try:

    # If a Jenkins config directory is specified,
    # then look there
    if JENKINS_CONFIG_DIR is not None:
        env_file = open(os.path.join(JENKINS_CONFIG_DIR, 'test_env.json'))

    # Otherwise look in the repo root (used if running locally)
    else:
        env_file = open(ENV_ROOT / "test_env.json")

    ENV_TOKENS = json.load(env_file)

# Fail gracefully if the file could not be found or parsed
except (IOError, ValueError):
    ENV_TOKENS = {}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        # pytest/django TestCase instances auto-prefix test_ onto the NAME
        'NAME': 'xqueue',
        'HOST': os.environ.get('DB_HOST', ENV_TOKENS.get('DB_HOST', 'edx.devstack.mysql')),
        # Wrap all view methods in an atomic transaction automatically.
        'ATOMIC_REQUESTS': True
    }
}

# RabbitMQ configuration
# Default to local broker if no external
# broker defined in test_env.json
RABBITMQ_USER = ENV_TOKENS.get('RABBITMQ_USER', 'guest')
RABBITMQ_PASS = ENV_TOKENS.get('RABBITMQ_PASS', 'guest')
RABBIT_HOST = os.environ.get('RABBIT_HOST', ENV_TOKENS.get('RABBIT_HOST', 'edx.devstack.rabbit'))
RABBIT_PORT = ENV_TOKENS.get('RABBIT_PORT', 5672)
RABBIT_VHOST = ENV_TOKENS.get('RABBIT_VHOST', '/')
RABBIT_TLS = ENV_TOKENS.get('RABBIT_TLS', False)
# Mathworks setup
# We load the Mathworks settings from envs.json
# to avoid storing auth information in the repository
# If you do not configure envs.json with the auth information
# for the Mathworks servers, then the Mathworks integration
# tests will be skipped.
XQUEUES = ENV_TOKENS.get('XQUEUES', {})
MATHWORKS_API_KEY = ENV_TOKENS.get('MATHWORKS_API_KEY', None)

# We set up the XQueue to send submissions to test_queue
# to a local port.  This must match the port we use
# when we set up passive grader stubs in integration tests.
TEST_XQUEUE_NAME = 'test_queue_%s' % uuid4().hex
XQUEUES[TEST_XQUEUE_NAME] = 'http://127.0.0.1:12348'

# Configuration for testing the update_users management command
ENV_ROOT = ROOT_PATH
AUTH_FILENAME = 'test_auth.json'

# Default keep testing with RabbitMQ
# We rerun the tests in `make test` and travis to test with only a database
WABBITS = True
