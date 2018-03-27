"""
Remove old submissions after they were lost or returned to the LMS
"""

import logging
import time
from datetime import datetime, timedelta
from queue.models import Submission

import pytz
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

log = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Delete old submissions by chunks for large databases
    """

    # Default maximum number of expired tokens to delete in a single transaction.
    DEFAULT_CHUNK_SIZE = 1000

    # Default seconds to sleep between chunked deletes of expired tokens.
    DEFAULT_SLEEP_BETWEEN_DELETES = 0

    # Default seconds to sleep between chunked deletes of expired tokens.
    DEFAULT_DAYS_OLD = 7

    def add_arguments(self, parser):
        parser.add_argument(
            '--chunk_size',
            default=self.DEFAULT_CHUNK_SIZE,
            type=int,
            help='Maximum number of expired tokens to delete in one transaction.'
        )
        parser.add_argument(
            '--sleep_between',
            default=self.DEFAULT_SLEEP_BETWEEN_DELETES,
            type=float,
            help='Seconds to sleep between chunked delete of expired tokens.'
        )
        parser.add_argument(
            '--days_old',
            default=self.DEFAULT_DAYS_OLD,
            type=int,
            help='How many days of submissions to keep'
        )

    def handle(self, *args, **options):
        """
        Deletes old submissions, chunking the deletes to avoid long table/row locks.
        """
        # Process the command arguments.
        chunk_size = options.get('chunk_size', self.DEFAULT_CHUNK_SIZE)
        if chunk_size <= 0:
            raise CommandError('Only positive chunk size is allowed ({}).'.format(chunk_size))
        sleep_between = options.get('sleep_between', self.DEFAULT_SLEEP_BETWEEN_DELETES)
        if sleep_between < 0:
            raise CommandError('Only non-negative sleep between seconds is allowed ({}).'.format(sleep_between))
        days_old = options.get('days_old', self.DEFAULT_DAYS_OLD)
        if days_old < 0:
            raise CommandError('Only non-negative days old is allowed ({}).'.format(days_old))

        delete_date = datetime.now(pytz.utc) - timedelta(days=days_old)

        old_submissions = Submission.objects.filter(arrival_time__lte=delete_date)
        total_old_submissions = old_submissions.count()

        log.info("STARTED: Deleting %s submissions older than '%s' with chunk size of %s and %s seconds between chunk.",
                 total_old_submissions, delete_date, chunk_size, sleep_between
                 )

        total_deletions = 0
        while old_submissions.exists():
            qs = old_submissions[:chunk_size]
            batch_ids = qs.values_list('id', flat=True)
            deletions_now = batch_ids.count()
            log.info("Deleting %s expired submissions...", deletions_now)
            with transaction.atomic():
                Submission.objects.filter(pk__in=list(batch_ids)).delete()
                total_deletions += deletions_now

            if old_submissions.exists():
                log.info("Sleeping %s seconds...", sleep_between)
                time.sleep(sleep_between)

        log.info("FINISHED: Deleted %s old submissions tokens total.", total_deletions)
