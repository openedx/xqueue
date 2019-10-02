from __future__ import absolute_import
from datetime import datetime, timedelta
from submission_queue.models import Submission

import pytz
from six.moves import range


def bulk_create_submissions(count=1, days_old=10, **create_params):
    for i in range(count):
        submission = create_submission(**create_params)
        actual_arrival_time = datetime.now(pytz.utc) - timedelta(days=days_old)
        Submission.objects.filter(pk=submission.id).update(arrival_time=actual_arrival_time)


def create_submission(**create_params):
    submission_params = dict(
        retired=0,
        queue_name=u'test',
    )
    submission_params.update(create_params)
    return Submission.objects.create(**submission_params)
