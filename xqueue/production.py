import codecs
from os import environ

import yaml
# Normally you should not import ANYTHING from Django directly
# into your settings, but ImproperlyConfigured is an exception.
from django.core.exceptions import ImproperlyConfigured

from logsettings import get_logger_config
from settings import *


def get_env_setting(setting):
    """ Get the environment setting or return exception """
    try:
        return environ[setting]
    except KeyError:
        error_msg = "Set the %s env variable" % setting
        raise ImproperlyConfigured(error_msg)


# Keep track of the names of settings that represent dicts. Instead of overriding the values in settings.py,
# the values read from disk should UPDATE the pre-configured dicts.
DICT_UPDATE_KEYS = ()

CONFIG_FILE = get_env_setting('XQUEUE_CFG')
with codecs.open(CONFIG_FILE, encoding='utf-8') as f:
    config_from_yaml = yaml.safe_load(f)

    # Remove the items that should be used to update dicts, and apply them separately rather
    # than pumping them into the local vars.
    dict_updates = {key: config_from_yaml.pop(key, None) for key in DICT_UPDATE_KEYS}

    for key, value in dict_updates.items():
        if value:
            vars()[key].update(value)

    vars().update(config_from_yaml)

LOGGING = get_logger_config(LOG_DIR,
                            logging_env=LOGGING_ENV,
                            syslog_addr=(SYSLOG_SERVER, 514),
                            local_loglevel=LOCAL_LOGLEVEL,
                            debug=False)

# The normal database user does not have enough permissions to run migrations.
# Migrations are run with separate credentials, given as DB_MIGRATION_*
# environment variables
DATABASES['default'].update({
    'ENGINE': os.environ.get('DB_MIGRATION_ENGINE', DATABASES['default']['ENGINE']),
    'USER': os.environ.get('DB_MIGRATION_USER', DATABASES['default']['USER']),
    'PASSWORD': os.environ.get('DB_MIGRATION_PASS', DATABASES['default']['PASSWORD']),
    'NAME': os.environ.get('DB_MIGRATION_NAME', DATABASES['default']['NAME']),
    'HOST': os.environ.get('DB_MIGRATION_HOST', DATABASES['default']['HOST']),
    'PORT': os.environ.get('DB_MIGRATION_PORT', DATABASES['default']['PORT']),
})

# These are shared variables used by whatever storage backend we have
AWS_STORAGE_BUCKET_NAME = UPLOAD_BUCKET
AWS_LOCATION = UPLOAD_PATH_PREFIX
AWS_QUERYSTRING_EXPIRE = UPLOAD_URL_EXPIRE

# To use newrelic agent from a management command, we need the app name and the license key
# In order to register the agent with the license key it needs to be in the environment (or an otherwise
# unused config file) before the later import of the agent by the command.
if not os.environ.get('NEW_RELIC_LICENSE_KEY', '') and NEWRELIC_LICENSE_KEY:
    os.environ['NEW_RELIC_LICENSE_KEY'] = NEWRELIC_LICENSE_KEY
