from datetime import datetime, timedelta
from queue.models import Submission

import pytz
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TransactionTestCase


class CountQueuedSubmissionsTest(TransactionTestCase):
    def _bulk_create(self, count=1, days_old=10, **create_params):
        for i in range(count):
            submission = self._create_submission(**create_params)
            actual_arrival_time = datetime.now(pytz.utc) - timedelta(days=days_old)
            Submission.objects.filter(pk=submission.id).update(arrival_time=actual_arrival_time)

    def _create_submission(self, **create_params):
        submission_params = dict(
            retired=0,
            queue_name=u'test',
        )
        submission_params.update(create_params)
        return Submission.objects.create(**submission_params)

    def test_deletes(self):
        "Default is 10 days old, default is deleting older than 7 days"
        self._bulk_create(30)
        self.assertEquals(Submission.objects.count(), 30)
        call_command('delete_old_submissions')
        self.assertEquals(Submission.objects.count(), 0)

    def test_undeleted(self):
        self._bulk_create(15, 5)
        self._bulk_create(15)
        self.assertEquals(Submission.objects.count(), 30)
        call_command('delete_old_submissions')
        self.assertEquals(Submission.objects.count(), 15)

    def test_chunks(self):
        self._bulk_create(20)
        call_command('delete_old_submissions', chunk_size=5, sleep_between=1)
        self.assertEquals(Submission.objects.count(), 0)

    def test_days_old(self):
        self._bulk_create(20)
        self.assertEquals(Submission.objects.count(), 20)
        call_command('delete_old_submissions', days_old=2)
        self.assertEquals(Submission.objects.count(), 0)

    def test_bad_arguments(self):
        with self.assertRaisesRegexp(CommandError, 'Only non-negative days old is allowed.*'):
            call_command('delete_old_submissions', days_old=-1)
        with self.assertRaisesRegexp(CommandError, 'Only non-negative sleep between seconds is allowed.*'):
            call_command('delete_old_submissions', sleep_between=-2)
        with self.assertRaisesRegexp(CommandError, 'Only positive chunk size is allowed.*'):
            call_command('delete_old_submissions', chunk_size=-3)
