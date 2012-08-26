import logging

from django.core.management.base import BaseCommand
from django.conf import settings
from queue.models import Submission
from queue.consumer import post_failure_to_lms

log = logging.getLogger(__name__)


class Command(BaseCommand):
    args = "<queue_name>"
    help = "Retire submissions in <queue_name> that have more than settings.MAX_NUMBER_OF_FAILURES failures. Notify the LMS/student that the queue will no longer attempt to process the submission"

    def handle(self, *args, **options):
        log.info(' [*] Scanning Submission database to retire failed submissions')
        
        queue_name = args[0]

        incomplete_submissions = Submission.objects.filter(queue_name=queue_name, lms_ack=False)
        for incomplete_submission in incomplete_submissions:
            if incomplete_submission.num_failures >= settings.MAX_NUMBER_OF_FAILURES:
                log.info(' [ ] Submission id %d with num_failures=%d marked as failure' %\
                            (incomplete_submission.id, incomplete_submission.num_failures))
                post_failure_to_lms(incomplete_submission.xqueue_header) # TODO: Move the submission into a separate "done" database
