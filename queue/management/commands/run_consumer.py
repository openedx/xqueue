import logging

from django.core.management.base import BaseCommand
from django.conf import settings

from queue.consumer import SingleChannel

log = logging.getLogger(__name__)


class Command(BaseCommand):
    args = "<worker count>"
    help = "Listens to all queues specified as being push-queues in the django configuration with <worker count> threads"

    def handle(self, *args, **options):
        log.info(' [*] Starting queue consumers...')

        channels = []
        for queue_name, push_url in settings.XQUEUES.items():
            if push_url is None:
                continue

            for wid in xrange(settings.XQUEUE_WORKERS_PER_QUEUE):
                channel = SingleChannel(wid, push_url, queue_name)
                channel.start()
                channels.append(channel)

        # TODO (cpennington): Manage this so that if a subset of workers die, we figure that out and restart
        for channel in channels:
            channel.join()

        log.info(' [*] All workers finished. Exiting')
