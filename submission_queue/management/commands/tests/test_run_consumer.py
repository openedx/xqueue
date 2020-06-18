from submission_queue.consumer import Worker
from submission_queue.management.commands.run_consumer import Command

from django.core.management import call_command
from django.test import TestCase, override_settings
from mock import patch


class RunConsumer(TestCase):

    @override_settings(XQUEUES={})
    def test_noqueues(self):
        """
        Empty XQUEUES list causes run_consumer to exit without
        creating any workers and spinning in a loop
        """
        call_command('run_consumer')

    @patch.object(Worker, 'run')
    @patch('submission_queue.management.commands.run_consumer.MONITOR_SLEEPTIME', 0)
    def test_stop_workers(self, mock_worker):
        """
        Having a Worker() with a zero exitcode tells monitor
        that workers are shutting down and cleans up
        """
        mock_worker.exitcode = 0
        call_command('run_consumer')

    @patch.object(Worker, 'run')
    def test_failed_workers(self, mock_worker):
        """
        Giving a non-zero exitcode makes monitor() create a new
        mock'ed Worker
        """
        mock_worker.exitcode = 77
        Command().monitor([mock_worker])
