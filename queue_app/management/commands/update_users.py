"""
Ensure that the right users exist:

- read USERS dictionary from auth.json
- if they don't exist, create them.
- if they do, update the passwords to match

"""
import json
import logging
import os

from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth.models import User

log = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Create users that are specified in auth.json"

    def handle(self, *args, **options):

        log.info("root is : " + settings.ENV_ROOT)
        auth_filename = '{0}auth.json'.format(settings.CONFIG_PREFIX)
        auth_path = os.path.join(settings.ENV_ROOT, auth_filename)

        log.info(' [*] reading {0}'.format(auth_path))

        with open(auth_path) as auth_file:
            AUTH_TOKENS = json.load(auth_file)
            users = AUTH_TOKENS.get('USERS', {})
            for username, pwd in users.items():
                log.info(' [*] Creating/updating user {0}'.format(username))
                try:
                    user = User.objects.get(username=username)
                    user.set_password(pwd)
                    user.save()
                except User.DoesNotExist:
                    log.info('     ... {0} does not exist. Creating'.format(username))

                    user = User.objects.create(username=username,
                                               email=username + '@dummy.edx.org',
                                               is_active=True)
                    user.set_password(pwd)
                    user.save()
        log.info(' [*] All done!')
