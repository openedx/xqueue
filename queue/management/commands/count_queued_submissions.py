"""
Check on currently queued submissions
"""

from __future__ import unicode_literals

from queue.models import Submission

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

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

    def handle(self, *args, **options):
        """
        Return a list of queues and their unretired submissions.
        If --newrelic is passed, these will be sent as a custom metric
        to New Relic Insights
        """
        queue_counts = (
                        Submission.objects.
                        values('queue_name').
                        filter(retired=False).
                        annotate(queue_count=Count('queue_name')).
                        order_by('-queue_count')
        )

        self.pretty_print_queues(queue_counts)

        use_newrelic = options.get('newrelic')
        if use_newrelic:
            self.send_nr_metrics(queue_counts)

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
