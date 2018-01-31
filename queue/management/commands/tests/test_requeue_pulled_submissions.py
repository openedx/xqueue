"""
Tests of the requeue_pulled_submissions management command.
"""
from __future__ import absolute_import

import mock
from django.core.management import call_command
from django.test import TestCase


class TestRequeuePulledSubmissions(TestCase):
    """
    Tests of the requeue_pulled_submissions management command.
    """
    def test_all_queues(self):
        path = 'queue.management.commands.requeue_pulled_submissions.Command.requeue_submissions'
        with mock.patch(path) as mock_method:
            call_command(u'requeue_pulled_submissions')
            assert mock_method.call_count == 1
