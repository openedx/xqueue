from settings import *
from logsettings import get_logger_config

log_dir = REPO_PATH / "log"

try:
    os.makedirs(log_dir)
except:
    pass

LOGGING = get_logger_config(ENV_ROOT / "log",
                            logging_env="dev",
                            dev_env=True,
                            debug=True)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test_xqueue.sqlite',

        # We need to use TEST_NAME here,
        # otherwise Django tests will use an in-memory database 
        # In-memory databases do not support access from
        # multiple threads, which the integration tests need
        'TEST_NAME': 'test_xqueue.sqlite',
    }
}

# Local RabbitMQ configuration
RABBITMQ_USER = 'guest'
RABBITMQ_PASS = 'guest'
RABBIT_HOST = 'localhost'

# We set up the XQueue to send submissions to test_queue
# to a local port.  This must match the port we use
# when we set up passive grader stubs in integration tests.
XQUEUES = {'test_queue': 'http://127.0.0.1:12348'}

# Nose Test Runner
INSTALLED_APPS += ('django_nose',)
NOSE_ARGS = ['--cover-erase', '--with-xunit', '--with-xcoverage', 
             '--cover-html',
             '--cover-inclusive', '--cover-html-dir',
             os.environ.get('NOSE_COVER_HTML_DIR', 'cover_html'),
             '--cover-package', 'queue', 'queue']
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
