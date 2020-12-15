import logging
from submission_queue.consumer import post_failure_to_lms
from submission_queue.models import Submission

from django.core.management.base import BaseCommand, CommandError
from django.utils import dateparse, timezone

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """
           Retire submissions for the requested <queue> that were submitted from the LMS before <date>
           It will send a message to the LMS so that learners know to resubmit, but will still be marked
           as retired regardless of success contacting the LMS.
           """

    def add_arguments(self, parser):
        parser.add_argument(
            'queue_name',
            help="Which queue to retire submissions for")

        parser.add_argument(
            '--retire-before',
            dest='retire_before',
            help='Date + time (UTC) to limit submissions up for retirement (arrival_time < YYYY-MM-DD HH:MM::SS)'
            )

    def handle(self, *args, **options):
        submissions = Submission.objects.filter(queue_name=options['queue_name'], retired=False)
        if options['retire_before']:
            retire_before = dateparse.parse_datetime(options['retire_before'])
            if retire_before:
                log.info(f"finding submissions submitted before {retire_before}")
                if not timezone.is_aware(retire_before):
                    retire_before = timezone.make_aware(retire_before, timezone.utc)
                submissions = submissions.filter(arrival_time__lte=retire_before)
            else:
                raise CommandError("unable to parse datetime {}".format(options['retire_before']))

        for submission in submissions:
            log.info(f"Retiring submission id={submission.id} from queue '{submission.queue_name}' ")
            submission.retired = True
            submission.lms_ack = post_failure_to_lms(submission.xqueue_header)
            if not submission.lms_ack:
                log.error(f'Could not contact LMS to retire submission id={submission.id} - retired anyway')
            submission.save()
