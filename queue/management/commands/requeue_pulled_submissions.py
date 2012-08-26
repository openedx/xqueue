import logging

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

from queue.models import Submission
from queue.consumer import post_failure_to_lms
from queue.queue_producer import push_to_queue

log = logging.getLogger(__name__)


class Command(BaseCommand):
    args = "<queue_name>"
    help = "Process currently pulled submissions, and requeue if external grader has not replied in settings.PULLED_SUBMISSION_TIMEOUT seconds. Optional <queue_name>" 

    def handle(self, *args, **options):
        log.info(' [*] Running requeue of pulled submissions...')

        if len(args) > 0:
            queue_name = args[0]
            open_submissions = Submission.objects.filter(queue_name=queue_name, lms_ack=False) 
        else:
            open_submissions = Submission.objects.filter(lms_ack=False)
        open_submissions = open_submissions.exclude(pull_time=None)

        for open_submission in open_submissions:
            current_time = timezone.now()
            time_difference = (current_time - open_submission.pull_time).total_seconds()
            if time_difference > settings.PULLED_SUBMISSION_TIMEOUT:
                open_submission.num_failures += 1
                if open_submission.num_failures < settings.MAX_NUMBER_OF_FAILURES:
                    log.info(' [ ] Requeuing submission.id=%d to queue %s which has been outstanding for %d seconds' %\
                        (open_submission.id, open_submission.queue_name, time_difference))
                    qitem = str(open_submission.id)
                    open_submission.pull_time = None
                    push_to_queue(open_submission.queue_name, qitem)
                else:
                    log.info(' [ ] NOT requeueing submission.id=%d to queue %s because num_failures=%d >= MAX_NUMBER_OF_FAILURES=%d' %\
                                (open_submission.id, open_submission.queue_name, open_submission.num_failures, settings.MAX_NUMBER_OF_FAILURES))
                open_submission.save()
                #post_failure_to_lms(open_submission.xqueue_header) # TODO: Requeue, not retire 
