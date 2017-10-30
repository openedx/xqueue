import mock
from datetime import timedelta
from django.conf import settings
from django.core.management import call_command
from django.utils.six import StringIO
from django.utils import timezone
from django.test import TestCase
from queue.models import Submission


class TestQueueUngradedSubmissions(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stdout = StringIO()
        cls.default_pull_time = timezone.now() - timedelta(seconds=settings.PULLED_SUBMISSION_TIMEOUT * 2)
        super(TestQueueUngradedSubmissions, cls).setUpClass()

    def setUp(self):
        self.mock_push_to_queue = mock.patch(
            'queue.management.commands.queue_ungraded_submissions.push_to_queue'
        ).start()

    def tearDown(self):
        self.mock_push_to_queue.stop()

    def _create_submission(self, **create_params):
        submission_params = dict(
            xqueue_header=u'{}',
            lms_ack=0,
            retired=0,
            pull_time=self.default_pull_time
        )
        submission_params.update(create_params)
        return Submission.objects.create(**submission_params)

    def _datetime_to_str(self, datetime_obj):
        return datetime_obj.isoformat().replace('+00:00', 'Z')

    def test_default_filters(self):
        self._create_submission(lms_ack=1, retired=1),
        self._create_submission(pull_time=None)
        call_command(
            'queue_ungraded_submissions',
            stdout=self.stdout
        )
        self.mock_push_to_queue.assert_not_called()

    def test_submission_id_param(self):
        submissions = [self._create_submission(queue_name='some_queue') for _ in range(4)]
        submissions_to_target = submissions[0:2]
        call_command(
            'queue_ungraded_submissions',
            submission_ids=','.join([str(submission.id) for submission in submissions_to_target]),
            stdout=self.stdout
        )
        self.assertEquals(self.mock_push_to_queue.call_count, len(submissions_to_target))
        for submission in submissions_to_target:
            self.mock_push_to_queue.assert_any_call('some_queue', str(submission.id))

    def test_queue_names_param(self):
        submissions = [
            self._create_submission(queue_name=queue_name)
            for queue_name in ['queue1', 'queue2', 'queue3', 'queue4']
        ]
        call_command(
            'queue_ungraded_submissions',
            queue_names='queue1,queue2',
            stdout=self.stdout
        )
        self.assertEquals(self.mock_push_to_queue.call_count, 2)
        self.mock_push_to_queue.assert_any_call('queue1', str(submissions[0].id))
        self.mock_push_to_queue.assert_any_call('queue2', str(submissions[1].id))

    def test_pull_time_params(self):
        submission_pull_time_bounds = (
            self.default_pull_time - timedelta(days=5),
            self.default_pull_time - timedelta(days=3),
        )
        submission_pull_times = [
            # Times within range
            submission_pull_time_bounds[0],
            submission_pull_time_bounds[0] + timedelta(minutes=30),
            submission_pull_time_bounds[1],
            # Times outside of range
            submission_pull_time_bounds[0] - timedelta(days=1),
            submission_pull_time_bounds[1] + timedelta(days=1),
        ]
        submissions = [
            self._create_submission(queue_name='some_queue', pull_time=pull_time)
            for pull_time in submission_pull_times
        ]
        call_command(
            'queue_ungraded_submissions',
            pull_time_start=self._datetime_to_str(submission_pull_time_bounds[0]),
            pull_time_end=self._datetime_to_str(submission_pull_time_bounds[1]),
            stdout=self.stdout
        )
        self.assertEquals(self.mock_push_to_queue.call_count, 3)
        for submission in submissions[0:3]:
            self.mock_push_to_queue.assert_any_call('some_queue', str(submission.id))

    def test_ignore_failures_param(self):
        submissions = [
            self._create_submission(queue_name='some_queue', num_failures=num_failures)
            for num_failures in [0, settings.MAX_NUMBER_OF_FAILURES]
        ]
        call_command(
            'queue_ungraded_submissions',
            '--ignore-failures',
            stdout=self.stdout
        )
        self.assertEquals(self.mock_push_to_queue.call_count, 2)

    def test_dry_run_param(self):
        self._create_submission(queue_name='some_queue')
        call_command(
            'queue_ungraded_submissions',
            '--dry-run',
            stdout=self.stdout
        )
        self.mock_push_to_queue.assert_not_called()

    def test_no_matching_submissions(self):
        self._create_submission(queue_name='some_queue')
        call_command(
            'queue_ungraded_submissions',
            queue_names='some_other_queue',
            stdout=self.stdout
        )
        self.mock_push_to_queue.assert_not_called()

    def test_submission_with_pull_time(self):
        '''
        Tests that a submission with a non-null pull_time value is updated when it's
        resubmitted to the queue
        '''
        submission = self._create_submission(queue_name='some_queue')
        self.assertEquals(submission.num_failures, 0)
        self.assertIsNotNone(submission.pull_time)
        call_command(
            'queue_ungraded_submissions',
            stdout=self.stdout
        )
        submission.refresh_from_db()
        self.mock_push_to_queue.assert_called_once()
        self.assertEquals(submission.num_failures, 1)
        self.assertIsNone(submission.pull_time)
