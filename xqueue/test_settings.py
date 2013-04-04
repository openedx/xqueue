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
    }
}

# Nose Test Runner
INSTALLED_APPS += ('django_nose',)
NOSE_ARGS = ['--cover-erase', '--with-xunit', '--with-xcoverage', 
             '--cover-html',
             '--cover-inclusive', '--cover-html-dir',
             os.environ.get('NOSE_COVER_HTML_DIR', 'cover_html'),
             '--cover-package', 'queue', 'queue']
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
