import json
import logging

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

from queue.models import Submission
from queue.consumer import post_failure_to_lms, post_grade_to_lms, _http_post # TODO: Wrap the _http_post which is used to deliver to grader

log = logging.getLogger(__name__)


class Command(BaseCommand):
    args = "<queue_name>"
    help = "Push orphaned submissions to the external grader"

    def handle(self, *args, **options):
        log.info(' [*] Pushing orphaned submission to the external grader...')

        for queue_name in args:
            orphaned_submissions = Submission.objects.filter(queue_name=queue_name, push_time=None, return_time=None, retired=False)
            self.push_orphaned_submissions(orphaned_submissions)

    def push_orphaned_submissions(self, orphaned_submissions):
        for orphaned_submission in orphaned_submissions:
            current_time = timezone.now()
            time_difference = (current_time - orphaned_submission.arrival_time).total_seconds()
            if time_difference > settings.ORPHANED_SUBMISSION_TIMEOUT:

                log.info("Found orphaned submission: queue_name: {0}, lms_header: {1}".format(
                    orphaned_submission.queue_name, orphaned_submission.xqueue_header))
                orphaned_submission.num_failures += 1

                payload = {'xqueue_body': orphaned_submission.xqueue_body,
                           'xqueue_files': orphaned_submission.urls}

                orphaned_submission.grader_id = settings.XQUEUES[orphaned_submission.queue_name]
                orphaned_submission.push_time = timezone.now()
                (grading_success, grader_reply) = _http_post(orphaned_submission.grader_id, json.dumps(payload), settings.GRADING_TIMEOUT)
                orphaned_submission.return_time = timezone.now()

                if grading_success:
                    orphaned_submission.grader_reply = grader_reply
                    orphaned_submission.lms_ack = post_grade_to_lms(orphaned_submission.xqueue_header, grader_reply)
                else:
                    log.error("Submission {} to grader {} failure: Reply: {}, ".format(orphaned_submission.id, orphaned_submission.grader_id, grader_reply))
                    orphaned_submission.num_failures += 1
                    orphaned_submission.lms_ack = post_failure_to_lms(orphaned_submission.xqueue_header)

                orphaned_submission.retired = True # NOTE: Retiring pushed submissions after one shot regardless of grading_success
                orphaned_submission.save()
