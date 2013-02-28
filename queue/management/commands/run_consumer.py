import logging
from itertools import combinations

from django.core.management.base import BaseCommand

from django.conf import settings

from queue.consumer import Worker

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
    help = """
    Listens to all queues specified as being push-queues in the django
    configuration with <worker count> processes
    """

    def handle(self, *args, **options):
        log.info(' [*] Starting queue consumers...')

        workers = []
        queues = settings.XQUEUES.items()

        # Assigned one worker for queue
        for name, url in queues:
            if url is not None:
                worker = Worker(queue_name=name, worker_url=url)
                worker.start()
                workers.append(worker)

        for worker in workers:
            worker.join()

        log.info(' [*] All workers finished. Exiting')
