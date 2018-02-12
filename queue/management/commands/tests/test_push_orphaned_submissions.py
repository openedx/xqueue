"""
Tests of the push_orphaned_submissions management command.
"""
from __future__ import absolute_import

import mock
import pytest
from django.core.management import CommandError, call_command
from django.test import TestCase


class TestPushOrphanedSubmissions(TestCase):
    """
    Tests of the push_orphaned_submissions management command.
    """
    def test_no_queue_names(self):
        with pytest.raises(CommandError, message='Error: too few arguments'):
            call_command(u'push_orphaned_submissions')

    def test_empty_queue(self):
        with mock.patch('queue.management.commands.push_orphaned_submissions._http_post') as mock_function:
            call_command(u'push_orphaned_submissions', u'empty')
            assert mock_function.call_count == 0
