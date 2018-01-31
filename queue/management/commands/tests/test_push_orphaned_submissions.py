"""
Tests of the push_orphaned_submissions management command.
"""
from __future__ import absolute_import

import mock
from django.core.management import call_command
from django.test import TestCase


class TestPushOrphanedSubmissions(TestCase):
    """
    Tests of the push_orphaned_submissions management command.
    """
    def test_no_queue_names(self):
        path = 'queue.management.commands.push_orphaned_submissions.Command.push_orphaned_submissions'
        with mock.patch(path) as mock_method:
            call_command(u'push_orphaned_submissions')
            assert mock_method.call_count == 0

    def test_empty_queue(self):
        with mock.patch('queue.management.commands.push_orphaned_submissions._http_post') as mock_function:
            call_command(u'push_orphaned_submissions', u'empty')
            assert mock_function.call_count == 0
