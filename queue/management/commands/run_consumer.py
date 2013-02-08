import logging

from itertools import combinations
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from queue.consumer import SingleChannel, QueueConsumer

log = logging.getLogger(__name__)


class NoAssignmentError(Exception):
    pass


def assign_workers_to_queues(queues, number_of_workers, workers_per_queue, minimum_disjoint_workers):
    """
    Returns a map of queues to worker ids (integers in range(number_of_workers))

    The function guarantees that each queue is assigned to workers_per_queue workers,
    and that each pair of queues has at least minimum_disjoint_workers workers
    that are distinct. This ensures that if one queue is overloaded, the other queues will
    still have active workers.

    If no such assignment is possible, then will raise NoAssignmentError
    """
    workers = range(number_of_workers)
    num_queues = len(queues)

    possible_assignments = (set(combo) for combo in combinations(workers, workers_per_queue))
    queue_assignments = []
    for next_assignment in possible_assignments:
        if len(queue_assignments) >= num_queues:
            break

        if min([len(next_assignment - old) for old in queue_assignments] + [workers_per_queue]) >= minimum_disjoint_workers:
            queue_assignments.append(next_assignment)

    if len(queue_assignments) < num_queues:
        raise NoAssignmentError()

    return dict(zip(queues, queue_assignments))


def assign_queues_to_workers(num_workers, queue_assignments):
    """
    Takes a dictionary mapping queues to workers for those queues, and converts
    it to a set of queues assigned to each worker

    queue_assignments: Dict from queue -> worker ids (ints)
    """
    worker_assignments = [set() for worker in range(num_workers)]
    for queue, assignment in queue_assignments.items():
        for worker in assignment:
            worker_assignments[worker].add(queue)

    return worker_assignments


class Command(BaseCommand):
    args = "<worker count>"
    help = "Listens to all queues specified as being push-queues in the django configuration with <worker count> threads"

    def handle(self, *args, **options):
        log.info(' [*] Starting queue consumers...')

        channels = []
        queues = [
            QueueConsumer(push_url, queue_name)
            for (queue_name, push_url)
            in settings.XQUEUES.items()
            if push_url is not None
        ]

        workers_per_queue = settings.XQUEUE_WORKERS_PER_QUEUE
        num_workers = settings.WORKER_COUNT

        assignments = None
        for min_disjoint_workers in range(max(workers_per_queue / 2, 1), 0, -1):
            try:
                queue_assignments = assign_workers_to_queues(queues, num_workers, workers_per_queue, min_disjoint_workers)
                assignments = assign_queues_to_workers(num_workers, queue_assignments)

                break
            except NoAssignmentError:
                continue

        if assignments is None:
            raise CommandError("Unable to assign workers to queues with constraints: workers_per_queue=%d, num_workers=%d" % (workers_per_queue, num_workers))

        for wid, queues in enumerate(assignments):
            channel = SingleChannel(wid, queues)
            channel.start()
            channels.append(channel)

        # TODO (cpennington): Manage this so that if a subset of workers die, we figure that out and restart
        for channel in channels:
            channel.join()

        log.info(' [*] All workers finished. Exiting')
