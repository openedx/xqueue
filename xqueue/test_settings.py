from uuid import uuid4

from .settings import *

log_dir = REPO_PATH / "log"

try:
    os.makedirs(log_dir)
except Exception as e:
    print(e)

LOGGING = get_logger_config(log_dir,
                            logging_env="test",
                            dev_env=True,
                            debug=True)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        # pytest/django TestCase instances auto-prefix test_ onto the NAME
        'NAME': 'xqueue',
        'HOST': os.environ.get('DB_HOST', 'edx.devstack.mysql'),
        # Wrap all view methods in an atomic transaction automatically.
        'CONN_MAX_AGE': 21600,
        'ATOMIC_REQUESTS': True,
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"
        },
    }
}

# We set up the XQueue to send submissions to test_queue
# to a local port.  This must match the port we use
# when we set up passive grader stubs in integration tests.
TEST_XQUEUE_NAME = 'test_queue_%s' % uuid4().hex
XQUEUES[TEST_XQUEUE_NAME] = 'http://127.0.0.1:12348'

# Number of seconds to wait between checks for new submissions that need to be
# sent to an external grader.  Tests only delay for ~4 seconds, so we need to
# poll faster.
CONSUMER_DELAY = 1

# This skips the matlab tests.  If you have a key to run those tests,
# you can set it here, or add a config file / env variable support.
MATHWORKS_API_KEY = None

USERS = {"test_user": "password"}
