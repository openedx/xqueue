"""
Tests of the database models in the ``queue`` application.
"""

from submission_queue.models import Submission

from django.test import TestCase
import six


class TestSubmission(TestCase):
    """
    Tests of the ``Submission`` model.
    """
    def test_keys(self):
        keys = 'Alabama Florida Ohio Oklahoma West Virginia'
        submission = Submission(s3_keys=keys)
        assert submission.keys == keys

    def test_text_representation(self):
        submission = Submission(requester_id='Alice', queue_name='Wonderland', xqueue_header='{}')
        assert "Submission from Alice for queue 'Wonderland'" in str(submission)
