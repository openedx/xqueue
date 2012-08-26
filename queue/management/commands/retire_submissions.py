import logging

from django.core.management.base import BaseCommand
from django.conf import settings
from optparse import make_option
from queue.models import Submission
from queue.consumer import post_failure_to_lms

log = logging.getLogger(__name__)


class Command(BaseCommand):
    args = "<queue_name>"
    help = "Retire submissions that have more than settings.MAX_NUMBER_OF_FAILURES failures. Notify the LMS/student that the queue will no longer attempt to process the submission. Optional <queue_name>"

    option_list = BaseCommand.option_list + (
        make_option('-f','--force',
            action='store_true',
            dest='force',
            default=False,
            help='Force retire submissions'),
        )

    def handle(self, *args, **options):
        log.info(' [*] Scanning Submission database to retire failed submissions...')
        
        if len(args) > 1:
            queue_name = args[0]
            failed_submissions = Submission.objects.select_for_update().filter(queue_name=queue_name, lms_ack=False)
        else:
            failed_submissions = Submission.objects.select_for_update().filter(lms_ack=False)

        failed_submissions = failed_submissions.exclude(num_failures=0)
        
        for failed_submission in failed_submissions:
            if failed_submission.num_failures >= settings.MAX_NUMBER_OF_FAILURES:
                log.info(" [ ] Retiring submission id=%d from queue '%s' with num_failures=%d" %\
                            (failed_submission.id, failed_submission.queue_name, failed_submission.num_failures))
                failed_submission.lms_ack = post_failure_to_lms(failed_submission.xqueue_header)
                if not failed_submission.lms_ack:
                    log.error(' [ ] Could not contact LMS to retire submission id=%d' % failed_submission.id)
                    if options['force']:
                        failed_submission.lms_ack = True # Forcibly mark as done
                failed_submission.save()
