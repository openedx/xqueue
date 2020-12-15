"""
Tests of the update_users management command.
"""

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase


class TestUpdateUsers(TestCase):
    """
    Tests of the update_users management command.
    """
    def test_existing_user(self):
        assert User.objects.count() == 0
        user = User.objects.create_user(username='test_user')
        assert not user.has_usable_password()
        call_command('update_users')
        users = User.objects.all()
        assert len(users) == 1
        user = users[0]
        assert user.username == 'test_user'
        assert user.has_usable_password()

    def test_new_user(self):
        assert User.objects.count() == 0
        call_command('update_users')
        users = User.objects.all()
        assert len(users) == 1
        assert users[0].username == 'test_user'
