"""
Tests of the update_users management command.
"""

from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from submission_queue.management.commands.tests import bulk_create_submissions
from submission_queue.models import Submission


class RetireOldSubmissionsTest(TestCase):

    def count_unretired(self, count):
        self.assertEqual(Submission.objects.filter(retired=False).count(),
                          count)

    @patch('submission_queue.management.commands.retire_old_submissions.post_failure_to_lms', return_value=True)
    def test_deletes(self, mock_post_to_lms):
        "Retire all the submissions"
        bulk_create_submissions(5)
        self.count_unretired(5)
        call_command('retire_old_submissions', 'test')
        self.count_unretired(0)

    @patch('submission_queue.management.commands.retire_old_submissions.post_failure_to_lms', return_value=True)
    def test_undeleted(self, mock_post_to_lms):
        """
        Create some older submissions and only retire those old ones
        Defaults are 10 days old, add 4 day old ones and retire anything 5 days or older
        """
        bulk_create_submissions(5, 4)
        bulk_create_submissions(5)
        self.count_unretired(10)
        older = timezone.now() - timedelta(5)
        call_command('retire_old_submissions', 'test', retire_before=older.isoformat())
        self.count_unretired(5)

    @patch('submission_queue.management.commands.retire_old_submissions.log')
    @patch('submission_queue.management.commands.retire_old_submissions.post_failure_to_lms', return_value=False)
    def test_deletes_failing_to_connect_to_lms(self, mock_post_to_lms, mock_logger):
        "Retire all the submissions, and fail the LMS callback"

        bulk_create_submissions(5)
        self.count_unretired(5)
        call_command('retire_old_submissions', 'test')
        mock_logger.error.assert_called()
        logs, _ = mock_logger.error.call_args
        self.assertRegex(logs[0], r'Could not contact LMS to retire submission')
        self.count_unretired(0)

    def test_bad_arguments(self):
        with self.assertRaisesRegex(CommandError, 'unable to parse datetime'):
            call_command('retire_old_submissions', 'test', retire_before='2018-04-03')
