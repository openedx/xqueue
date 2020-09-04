import codecs
from os import environ

import yaml
# Normally you should not import ANYTHING from Django directly
# into your settings, but ImproperlyConfigured is an exception.
from django.core.exceptions import ImproperlyConfigured

from .settings import *


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

# We use the default development logging from settings.py
# but override this to force a console log for docker.
# Stolen from the LMS.
LOGGING['handlers']['local'] = {
    'class': 'logging.NullHandler',
}

# It's probably ok to search your DB for push queues every minute (or even longer) on a
# development instance, rather than the brief prod timespan.
CONSUMER_DELAY = 60

#####################################################################
# See if the developer has any local overrides.
if os.path.isfile(join(dirname(abspath(__file__)), 'private.py')):
    from .private import *  # pylint: disable=import-error,wildcard-import
