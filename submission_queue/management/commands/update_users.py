"""
Ensure that the right users exist:

- read USERS dictionary from settings
- if they don't exist, create them.
- if they do, update the passwords to match

"""
import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Create users that are specified in your configuration"

    def handle(self, *args, **options):

        for username, pwd in settings.USERS.items():
            log.info(f' [*] Creating/updating user {username}')
            try:
                user = User.objects.get(username=username)
                user.set_password(pwd)
                user.save()
            except User.DoesNotExist:
                log.info(f'     ... {username} does not exist. Creating')

                user = User.objects.create(username=username,
                                           email=username + '@dummy.edx.org',
                                           is_active=True)
                user.set_password(pwd)
                user.save()
