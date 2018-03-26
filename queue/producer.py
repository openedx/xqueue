from datetime import datetime, timedelta
from queue.models import Submission

import pytz
from django.conf import settings
from django.db.models import Q


def get_queue_length(queue_name):
    """
    How many unretired submissions are available for a queue
    """
    pull_time_filter = Q(pull_time__lte=(datetime.now(pytz.utc) - timedelta(minutes=settings.SUBMISSION_PROCESSING_DELAY))) | Q(pull_time__isnull=True)
    return Submission.objects.filter(queue_name=queue_name).filter(pull_time_filter).exclude(retired=False).count()
