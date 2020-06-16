from submission_queue.management.commands.tests import bulk_create_submissions
from submission_queue.models import Submission

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TransactionTestCase


class DeleteOldSubmissionsTest(TransactionTestCase):
    def test_deletes(self):
        "Default is 10 days old, default is deleting older than 7 days"
        bulk_create_submissions(30)
        self.assertEqual(Submission.objects.count(), 30)
        call_command('delete_old_submissions')
        self.assertEqual(Submission.objects.count(), 0)

    def test_undeleted(self):
        bulk_create_submissions(15, 5)
        bulk_create_submissions(15)
        self.assertEqual(Submission.objects.count(), 30)
        call_command('delete_old_submissions')
        self.assertEqual(Submission.objects.count(), 15)

    def test_chunks(self):
        bulk_create_submissions(20)
        call_command('delete_old_submissions', chunk_size=5, sleep_between=1)
        self.assertEqual(Submission.objects.count(), 0)

    def test_days_old(self):
        bulk_create_submissions(20)
        self.assertEqual(Submission.objects.count(), 20)
        call_command('delete_old_submissions', days_old=2)
        self.assertEqual(Submission.objects.count(), 0)

    def test_bad_arguments(self):
        with self.assertRaisesRegex(CommandError, 'Only non-negative days old is allowed.*'):
            call_command('delete_old_submissions', days_old=-1)
        with self.assertRaisesRegex(CommandError, 'Only non-negative sleep between seconds is allowed.*'):
            call_command('delete_old_submissions', sleep_between=-2)
        with self.assertRaisesRegex(CommandError, 'Only positive chunk size is allowed.*'):
            call_command('delete_old_submissions', chunk_size=-3)
