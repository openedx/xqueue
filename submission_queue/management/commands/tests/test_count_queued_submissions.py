from io import StringIO
from submission_queue.models import Submission
from unittest.mock import call, patch

from django.core.management import call_command
from django.test import TestCase


class CountQueuedSubmissionsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stdout = StringIO()
        super().setUpClass()

    def _create_submission(self, **create_params):
        submission_params = dict(
            retired=0,
            queue_name='test'
        )
        submission_params.update(create_params)
        return Submission.objects.create(**submission_params)

    def test_no_submissions(self):
        call_command('count_queued_submissions', stdout=self.stdout)
        self.assertEqual('', self.stdout.getvalue())

    def test_no_unretired_submissions(self):
        self._create_submission(retired=1)
        call_command('count_queued_submissions', stdout=self.stdout)
        self.assertEqual('', self.stdout.getvalue())

    def test_submissions(self):
        self._create_submission(queue_name="test1")
        self._create_submission(queue_name="test1")
        self._create_submission(queue_name="test3")
        call_command('count_queued_submissions', stdout=self.stdout)
        self.assertRegex(self.stdout.getvalue(), r'test1\s*2\s*\ntest3\s*1')

    @patch('newrelic.agent')
    def test_push_to_new_relic(self, mock_newrelic_agent):
        self._create_submission(queue_name="test1")
        self._create_submission(queue_name="test2")
        self._create_submission(queue_name="test2")
        call_command('count_queued_submissions', '--newrelic', stdout=self.stdout)
        self.assertRegex(self.stdout.getvalue(), r'test2\s*2\s*\ntest1\s*1')

        expected_nr_calls = [
            call('test1', 1),
            call('test2', 2)
        ]

        self.assertEqual(len(expected_nr_calls),
                          mock_newrelic_agent.record_custom_metric.call_count)

        mock_newrelic_agent.record_custom_metric.has_calls(expected_nr_calls, any_order=True)

    @patch('boto3.client')
    def test_push_to_cloudwatch(self, mock_boto3):
        self._create_submission(queue_name="test-pull")
        self._create_submission(queue_name="test2")
        self._create_submission(queue_name="test2")
        call_command('count_queued_submissions', '--cloudwatch', stdout=self.stdout)
        self.assertRegex(self.stdout.getvalue(), r'test2\s*2\s*\ntest-pull\s*1')

        metric_alarm_kwargs = []
        for call in mock_boto3.mock_calls:
            name, args, kwargs = call
            if 'put_metric_name' in name:
                self.assertEqual(len(kwargs['Metricdata']), 2)
                self.assertEqual(kwargs,
                                  {'Namespace': 'xqueue/dev-stack',
                                   'MetricData': [
                                       {'Dimensions': [{'Name': 'queue', 'Value': 'test2'}],
                                        'Value': 2,
                                        'MetricName': 'queue_length'
                                        },
                                       {'Dimensions': [{'Name': 'queue', 'Value': 'test-pull'}],
                                        'Value': 1,
                                        'MetricName': 'queue_length'}]})
            if 'put_metric_alarm' in name:
                metric_alarm_kwargs.append(kwargs)

        self.assertEqual(len(metric_alarm_kwargs), 2)
        self.assertEqual(metric_alarm_kwargs[0]['AlarmName'], 'dev-stack test2 xqueue queue length over threshold')
        self.assertEqual(metric_alarm_kwargs[1]['AlarmName'], 'dev-stack test-pull xqueue queue length over threshold')
