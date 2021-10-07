"""
Check on currently queued submissions
"""
from submission_queue.models import Submission

import backoff
import boto3
import botocore
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Value
from six.moves import zip_longest

try:
    import newrelic.agent
except ImportError:  # pragma: no cover
    newrelic = None  # pylint: disable=invalid-name


class Command(BaseCommand):
    """
    Count submissions per-queue that have not been retired
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--newrelic',
            action='store_true',
            help='Submit New Relic custom metrics'
        )
        parser.add_argument(
            '--cloudwatch',
            action='store_true',
            help='Submit CloudWatch custom metrics'
        )

    def handle(self, *args, **options):
        """
        Return a list of queues and their unretired submissions.
        If --newrelic is passed, these will be sent as a custom metric
        to New Relic Insights
        """
        queue_counts = (
            Submission.objects.
                values('queue_name').
                filter(retired=Value(0)).
                annotate(queue_count=Count('queue_name')).
                order_by('-queue_count')
        )

        self.pretty_print_queues(queue_counts)

        use_newrelic = options.get('newrelic')
        if use_newrelic:
            self.send_nr_metrics(queue_counts)

        use_cloudwatch = options.get('cloudwatch')
        if use_cloudwatch:
            self.send_cloudwatch_metrics(queue_counts)

    def pretty_print_queues(self, queue_counts):
        """
        Send a tabulated log output of the queues and the counts to the console
        No output if there are no queued submissions
        """

        for queue in queue_counts:
            self.stdout.write("{:<30} {:<10}".format(queue['queue_name'],
                                                     queue['queue_count']))

    def send_nr_metrics(self, queue_counts):
        """
        Send custom metrics to New Relic Insights
        """
        if not newrelic:  # pragma: no cover
            raise CommandError("--newrelic cannot be used unless the newrelic library is installed")

        newrelic.agent.initialize()
        nr_app = newrelic.agent.register_application(name=settings.NEWRELIC_APPNAME, timeout=10.0)

        for queue in queue_counts:
            newrelic.agent.record_custom_metric(
                'Custom/XQueueLength/{}[submissions]'.format(queue['queue_name']),
                queue['queue_count'],
                application=nr_app)

    def send_cloudwatch_metrics(self, queue_counts):
        """
        Send custom metrics to AWS CloudWatch
        """
        cloudwatch = CwBotoWrapper()
        cloudwatch_configuration = settings.CLOUDWATCH_QUEUE_COUNT_METRICS
        metric_name = 'queue_length'
        dimension = 'queue'
        environment = cloudwatch_configuration['environment']
        deployment = cloudwatch_configuration['deployment']
        namespace = "xqueue/{}-{}".format(environment,
                                          deployment)

        # iterate 10 at a time through the list of queues to stay under AWS limits.
        for queues in grouper(queue_counts, 10):
            # grouper can return a bunch of Nones and we want to skip those
            queues = [q for q in queues if q is not None]
            metric_data = []
            for queue in queues:
                metric_data.append({
                    'MetricName': metric_name,
                    'Dimensions': [{
                        "Name": dimension,
                        "Value": queue['queue_name']
                    }],
                    'Value': queue['queue_count']
                })

            if len(metric_data) > 0:
                cloudwatch.put_metric_data(Namespace=namespace, MetricData=metric_data)

            for queue in queues:
                dimensions = [{'Name': dimension, 'Value': queue['queue_name']}]
                threshold = cloudwatch_configuration['default_threshold']
                if queue['queue_name'] in cloudwatch_configuration['thresholds']:
                    threshold = cloudwatch_configuration['thresholds'][queue['queue_name']]
                # Period is in seconds - has to be over the max for an hour
                period = 600
                evaluation_periods = 6
                comparison_operator = "GreaterThanThreshold"
                treat_missing_data = "notBreaching"
                statistic = "Maximum"
                actions = cloudwatch_configuration['sns_arns']
                alarm_name = "{}-{} {} xqueue queue length over threshold".format(environment,
                                                                                  deployment,
                                                                                  queue['queue_name'])

                print(f'Creating or updating alarm "{alarm_name}"')
                cloudwatch.put_metric_alarm(AlarmName=alarm_name,
                                            AlarmDescription=alarm_name,
                                            Namespace=namespace,
                                            MetricName=metric_name,
                                            Dimensions=dimensions,
                                            Period=period,
                                            EvaluationPeriods=evaluation_periods,
                                            TreatMissingData=treat_missing_data,
                                            Threshold=threshold,
                                            ComparisonOperator=comparison_operator,
                                            Statistic=statistic,
                                            InsufficientDataActions=actions,
                                            OKActions=actions,
                                            AlarmActions=actions)


class CwBotoWrapper:
    max_tries = 5

    def __init__(self):
        self.client = boto3.client('cloudwatch')

    @backoff.on_exception(backoff.expo,
                          (botocore.exceptions.ClientError),
                          max_tries=max_tries)
    def put_metric_data(self, *args, **kwargs):
        return self.client.put_metric_data(*args, **kwargs)

    @backoff.on_exception(backoff.expo,
                          (botocore.exceptions.ClientError),
                          max_tries=max_tries)
    def put_metric_alarm(self, *args, **kwargs):
        return self.client.put_metric_alarm(*args, **kwargs)


# Stolen right from the itertools recipes
# https://docs.python.org/3/library/itertools.html#itertools-recipes
def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)
