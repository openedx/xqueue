import logging
import time
from submission_queue.consumer import Worker

from django.conf import settings
from django.core.management.base import BaseCommand

log = logging.getLogger(__name__)


MONITOR_SLEEPTIME = 10


class Command(BaseCommand):
    help = """
    Listens to all queues specified as being push-queues in the django
    configuration
    """

    def handle(self, *args, **options):
        log.info(' [*] Starting queue workers...')

        workers = []
        queues = list(settings.XQUEUES.items())

        # Assigned one worker for queue
        for name, url in queues:
            if url is not None:
                worker = Worker(queue_name=name, worker_url=url)
                workers.append(worker)

        # Start workers
        for worker in workers:
            log.info(f' [{worker.queue_name}] Starting worker')
            worker.start()

        # Monitor workers
        while workers:
            self.monitor(workers)
            time.sleep(MONITOR_SLEEPTIME)

        log.info(' [*] All workers finished. Exiting')

    def monitor(self, workers):
        finished_workers = []
        failed_workers = []

        for worker in workers:
            exitcode = worker.exitcode

            if exitcode is None:  # the process is running
                continue
            elif exitcode >= 1:  # the process failed
                failed_workers.append(worker)
            else:  # the process has finished (0) or was interrupted (<0)
                finished_workers.append(worker)

        # remove finished workers
        for worker in finished_workers:
            log.info(f' [{worker.queue_name}] Worker stopped')
            workers.remove(worker)

        # restart failed workers
        for worker in failed_workers:
            log.info(f' [{worker.queue_name}] Worker failed')
            workers.remove(worker)

            new_worker = Worker(queue_name=worker.queue_name, worker_url=worker.worker_url)
            workers.append(new_worker)

            log.info(f' [{new_worker.queue_name}] Starting worker')
            new_worker.start()
