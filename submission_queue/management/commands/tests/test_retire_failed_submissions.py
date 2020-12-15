"""
Tests of the retire_submissions management command.
"""

from unittest import mock
from django.core.management import call_command
from django.test import TestCase


class TestRetireFailedSubmissions(TestCase):
    """
    Tests of the retire_submissions management command.
    """
    def test_all_queues(self):
        path = 'submission_queue.management.commands.retire_failed_submissions.Command.retire_submissions'
        with mock.patch(path) as mock_method:
            call_command('retire_failed_submissions', force=True)
            assert mock_method.call_count == 1
