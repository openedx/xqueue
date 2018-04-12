from queue.models import Submission

from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO
from mock import call, patch


class CountQueuedSubmissionsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stdout = StringIO()
        super(CountQueuedSubmissionsTest, cls).setUpClass()

    def _create_submission(self, **create_params):
        submission_params = dict(
            retired=0,
            queue_name=u'test'
        )
        submission_params.update(create_params)
        return Submission.objects.create(**submission_params)

    def test_no_submissions(self):
        call_command('count_queued_submissions', stdout=self.stdout)
        self.assertEquals('', self.stdout.getvalue())

    def test_no_unretired_submissions(self):
        self._create_submission(retired=1)
        call_command('count_queued_submissions', stdout=self.stdout)
        self.assertEquals('', self.stdout.getvalue())

    def test_submissions(self):
        self._create_submission(queue_name="test1")
        self._create_submission(queue_name="test1")
        self._create_submission(queue_name="test3")
        call_command('count_queued_submissions', stdout=self.stdout)
        self.assertRegexpMatches(self.stdout.getvalue(), r'test1\s*2\s*\ntest3\s*1')

    @patch('newrelic.agent')
    def test_push_to_new_relic(self, mock_newrelic_agent):
        self._create_submission(queue_name="test1")
        self._create_submission(queue_name="test2")
        self._create_submission(queue_name="test2")
        call_command('count_queued_submissions', '--newrelic', stdout=self.stdout)
        self.assertRegexpMatches(self.stdout.getvalue(), r'test2\s*2\s*\ntest1\s*1')

        expected_nr_calls = [
            call('test1', 1),
            call('test2', 2)
        ]

        self.assertEquals(len(expected_nr_calls),
                          mock_newrelic_agent.record_custom_metric.call_count)

        mock_newrelic_agent.record_custom_metric.has_calls(expected_nr_calls, any_order=True)
