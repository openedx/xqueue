import logging

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

from queue.models import Submission
from queue.consumer import post_failure_to_lms

log = logging.getLogger(__name__)


class Command(BaseCommand):
    args = "<queue_name>"
    help = "Process currently open, pulled submissions on queue <queue_name>, and requeue if external grader has not replied in settings.PULLED_SUBMISSION_TIMEOUT seconds" 

    def handle(self, *args, **options):
        log.info(' [*] Running requeue of pulled submissions...')

        queue_name = args[0]

        open_submissions = Submission.objects.filter(queue_name=queue_name, lms_ack=False) 
        open_submissions = open_submissions.exclude(pull_time=None)

        for open_submission in open_submissions:
            current_time = timezone.now()
            time_difference = current_time - open_submission.pull_time
            if time_difference.total_seconds() > settings.PULLED_SUBMISSION_TIMEOUT:
                post_failure_to_lms(open_submission.xqueue_header) # TODO: Requeue, not retire 
