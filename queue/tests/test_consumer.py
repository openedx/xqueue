import mock
from unittest import TestCase
from django.conf import settings
from uuid import uuid4

from pika.exceptions import AMQPConnectionError

from queue.consumer import Worker


class TestWorkerConnection(TestCase):

    QUEUE_NAME = 'test_queue_%s' % uuid4().hex

    def setUp(self):
        self.worker = Worker(queue_name=self.QUEUE_NAME, worker_url='some_test_url')

    @mock.patch('time.sleep', mock.Mock(return_value=None))
    @mock.patch('queue.consumer.log')
    @mock.patch('queue.consumer.Worker.connect')
    def test_connection_retries_on_exception(self, mock_worker_connect, mock_log):
        """
        Tests worker's connection on 'AMQPConnectionError' exception.
        """
        mock_worker_connect.side_effect = AMQPConnectionError

        self.assertEquals(self.worker.retries, 0)

        with self.assertRaises(AMQPConnectionError):
            self.worker.run()

        self.assertEquals(self.worker.retries, settings.RETRY_MAX_ATTEMPTS)

        # Asserts connection retry logging.
        for attempt in xrange(1, settings.RETRY_MAX_ATTEMPTS):
            mock_log.info.assert_any_call(
                "[{id}] - Retrying connection, attempt # {attempt} of {max_attempts} of MAX".format(
                    id=self.worker.id,
                    attempt=attempt,
                    max_attempts=settings.RETRY_MAX_ATTEMPTS
                )
            )

        # Asserts that the error was logged on crossing max retry attempts.
        mock_log.error.assert_called_with("[{id}] Consumer for queue {queue} connection error: ".format(
            id=self.worker.id,
            queue=self.worker.queue_name,
        ))
