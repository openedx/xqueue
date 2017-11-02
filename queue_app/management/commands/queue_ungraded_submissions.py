import logging

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
import pprint

from queue_app.models import Submission
from queue_app.producer import push_to_queue

log = logging.getLogger(__name__)


def parse_iso_8601_string(iso_string):
    return datetime.strptime(iso_string, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)


class Command(BaseCommand):
    help = "Push ungraded submissions onto the queue for grading. Useful for cases where grading fails."
    ECHO_LIMIT = 25
    ECHO_PROPERTIES = ('id', 'queue_name', 'push_time', 'pull_time', 'return_time', 'num_failures', 'lms_callback_url')

    def add_arguments(self, parser):
        parser.add_argument(
            '--queues',
            dest='queue_names',
            default='',
            help='Names of queues (comma-separated)',
        )
        parser.add_argument(
            '--ids',
            dest='submission_ids',
            default='',
            help='Submission.id values (comma-separated)',
        )
        parser.add_argument(
            '--pull-time-start',
            dest='pull_time_start',
            default=None,
            help='Submission pull_time range start (UTC, ISO-8601 formatted - 2017-01-01T00:00:00Z, et. al.)',
        )
        parser.add_argument(
            '--pull-time-end',
            dest='pull_time_end',
            default=None,
            help='Submission pull_time range end (UTC, ISO-8601 formatted - 2017-01-01T00:00:00Z, et. al.)',
        )
        parser.add_argument(
            '--ignore-failures',
            action='store_true',
            dest='ignore_failures',
            default=False,
            help='Requeue the submissions even if their num_failures is greater than the max in settings',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            default=False,
            help='Echo the submissions that will be queued for grading (instead of actually queueing them)',
        )

    def handle(self, *args, **options):
        grading_success_params = dict(
            lms_ack=1,
            retired=1
        )
        exclude_params = dict(pull_time=None)
        filter_params = {}
        if options['queue_names']:
            filter_params['queue_name__in'] = options['queue_names'].split(',')
        if options['submission_ids']:
            filter_params['id__in'] = options['submission_ids'].split(',')
        if options['pull_time_start']:
            filter_params['pull_time__gte'] = parse_iso_8601_string(options['pull_time_start'])
        if options['pull_time_end']:
            filter_params['pull_time__lte'] = parse_iso_8601_string(options['pull_time_end'])
        else:
            filter_params['pull_time__lte'] = (
                timezone.now() - timedelta(seconds=settings.PULLED_SUBMISSION_TIMEOUT)
            )
        if not options['ignore_failures']:
            filter_params['num_failures__lt'] = settings.MAX_NUMBER_OF_FAILURES

        submission_qset = (
            Submission.objects
            .filter(**filter_params)
            .exclude(**grading_success_params)
            .exclude(**exclude_params)
            .order_by('-id')
        )
        if options['dry_run']:
            pp = pprint.PrettyPrinter(indent=2)
            for submission in submission_qset.values(*self.ECHO_PROPERTIES)[0:self.ECHO_LIMIT]:
                self.stdout.write(pp.pformat(submission))
            num_submissions = submission_qset.count()
            self.stdout.write("\nMatching submission count: {0}".format(num_submissions))
            if num_submissions > self.ECHO_LIMIT:
                submission_ids = submission_qset.values_list('id', flat=True)
                self.stdout.write("\nIDs: {0}\n\n".format(','.join(map(str, submission_ids))))
        else:
            self.requeue_submissions(submission_qset)

    def requeue_submissions(self, submission_qset):
        num_submissions = submission_qset.count()
        if num_submissions == 0:
            self.stdout.write("No matching submissions to queue.")
            return
        self.stdout.write("Queueing {0} submissions...".format(num_submissions))
        for submission in submission_qset:
            if submission.pull_time:
                submission.num_failures += 1
                submission.pull_time = None
                submission.pullkey = ''
                submission.save()
            push_to_queue(submission.queue_name, str(submission.id))
        self.stdout.write("Queueing finished")
