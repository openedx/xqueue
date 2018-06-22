import os

from path import Path as path

from xqueue.logsettings import get_logger_config

ROOT_PATH = path(__file__).dirname()
REPO_PATH = ROOT_PATH.dirname()
ENV_ROOT = REPO_PATH.dirname()
CONFIG_PREFIX = ''

# Django settings for xqueue project.

DEBUG = False

ALLOWED_HOSTS = ['*']

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

# How long we should wait for the LMS to accept a grader response before
# timing out.
REQUESTS_TIMEOUT = 5    # seconds
# How long xqueue_consumer should wait for a response from a remote
# grader before timing out the request.
GRADING_TIMEOUT = 30    # seconds

XQUEUES = {'test-pull': None}

# How many times XQueue posting a result back to the LMS can fail
# This happens during put_submission in the external interface as well
# as in the retire_submissions command
MAX_NUMBER_OF_FAILURES = 3

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

# It's unclear why this is defined, xqueue doesn't use django sites, but does
# have the database table with one entry in it.  TODO: remove the sites app.
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

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'uofqkujp@z#_vtwct+v716z+^3hijelj1^fkydwo2^pbkxghfq'

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

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
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

# If you use count_queue_submissions to submit data to AWS CloudWatch you'll need to
# provide some information for how to construct the metrics and alarms.
# It will store metrics in a namespace of xqueue/environment-deployment and create an alarm
# for each queue with an alarm on the default_threshold.  If you want a different threshold
# for a given queue, thresholds has a dictionary of "queue name" : "custom limit".
# All thresholds share the sns_arn.
CLOUDWATCH_QUEUE_COUNT_METRICS = {
    'environment': 'dev',
    'deployment': 'stack',
    'sns_arn': 'arn:aws:sns:::',
    'default_threshold': 50,
    'thresholds': {
        'test-pull': 100
    }
}
