import os

from path import Path as path

from xqueue.logsettings import get_logger_config

ROOT_PATH = path(__file__).dirname()
REPO_PATH = ROOT_PATH.dirname()
ENV_ROOT = REPO_PATH.dirname()
CONFIG_PREFIX = ''

# Django settings for xqueue project.

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = ['*']

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

REQUESTS_TIMEOUT = 5    # seconds
GRADING_TIMEOUT = 30    # seconds

XQUEUES = {'test-pull': None}

MAX_NUMBER_OF_FAILURES = 3
PULLED_SUBMISSION_TIMEOUT = 10    # seconds

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'xqueue.sqlite',
    }
}

# Bucket where files will be uploaded
UPLOAD_BUCKET = "s3_bucket"
UPLOAD_PATH_PREFIX = "xqueue"
UPLOAD_URL_EXPIRE = 60 * 60 * 24 * 365  # 1 year

# Basic auth tuple to pass to reqests library to authenticate with other services
REQUESTS_BASIC_AUTH = None

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'uofqkujp@z#_vtwct+v716z+^3hijelj1^fkydwo2^pbkxghfq'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    # 'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'xqueue.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'xqueue.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(ROOT_PATH, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'queue',
    'release_util',
    'storages',
)

LOGIN_URL = '/xqueue/login/'

LOGGING = get_logger_config(
    log_dir=ENV_ROOT / "log",
    logging_env="dev",
    dev_env=True,
    debug=True)

# How many minutes to ignore pulled or pushed submissions when a client connects
# for a given queue, since another client/worker may have pulled the submission
# and be processing it.
SUBMISSION_PROCESSING_DELAY = 1

# Number of seconds to wait between checks for new submissions that need to be
# sent to an external grader
CONSUMER_DELAY = 10

# This is normally used in the supervisor configuration but if you have a
# standalone script, you need to report to the correct app (and aren't
# already running inside NR)
NEWRELIC_APPNAME = 'xqueue'

# These are learner permissions and we generate signed URLs for external graders
# to download.  The uploads should not be public by default.
AWS_DEFAULT_ACL = 'private'

# This is the list of users managed by update_users
USERS = None
