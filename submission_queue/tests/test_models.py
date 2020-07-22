"""
Tests of the database models in the ``queue`` application.
"""

from submission_queue.models import Submission

from django.test import TestCase


class TestSubmission(TestCase):
    """
    Tests of the ``Submission`` model.
    """
    def test_keys(self):
        keys = u'Alabama Florida Ohio Oklahoma West Virginia'
        submission = Submission(s3_keys=keys)
        assert submission.keys == keys

    def test_text_representation(self):
        submission = Submission(requester_id=u'Alice', queue_name=u'Wonderland', xqueue_header=u'{}')
        assert u"Submission from Alice for queue 'Wonderland'" in str(submission)
