from settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

# Nose Test Runner
INSTALLED_APPS += ('django_nose',)
NOSE_ARGS = ['--cover-erase', '--with-xunit', '--with-xcoverage', '--cover-html',
             '--cover-inclusive', '--cover-html-dir',
             os.environ.get('NOSE_COVER_HTML_DIR', 'cover_html'),
             '--cover-package', 'queue',
             'queue']
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
