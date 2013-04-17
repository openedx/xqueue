from nose.tools import assert_raises, assert_equals
from itertools import combinations

from queue.management.commands.run_consumer import assign_workers_to_queues, assign_queues_to_workers, NoAssignmentError


def min_disjoint_workers(queue_assignments):
    return min(len(set(a) - set(b)) for (a, b) in combinations(queue_assignments.values(), 2))


def test_assign_workers_to_queues():
    # A -> 0, 1, 2
    # B -> 0, 1, 3
    # C -> 1, 2, 3
    assert min_disjoint_workers(assign_workers_to_queues("ABC", 4, 3, 1)) >= 1

    # Fewer workers than queues -> can't make single assignments distinct
    assert_raises(NoAssignmentError, assign_workers_to_queues, "ABC", 2, 1, 1)

    # A -> 0, 1
    # B -> 0, 1
    # C -> 0, 1
    assert_raises(NoAssignmentError, assign_workers_to_queues, "ABC", 2, 2, 1)

    # A -> 0, 1
    # B -> 0, 2
    # C -> 1, 2
    assert min_disjoint_workers(assign_workers_to_queues("ABC", 3, 2, 1)) >= 1

    # Based on prod settings
    assert_raises(NoAssignmentError, assign_workers_to_queues, range(8), 24, 12, 7)
    assert min_disjoint_workers(assign_workers_to_queues(range(8), 24, 12, 6)) >= 6
    assert min_disjoint_workers(assign_workers_to_queues(range(8), 24, 12, 4)) >= 4
    assert min_disjoint_workers(assign_workers_to_queues(range(8), 24, 12, 3)) >= 3
    assert min_disjoint_workers(assign_workers_to_queues(range(8), 24, 12, 2)) >= 2
    assert min_disjoint_workers(assign_workers_to_queues(range(8), 24, 12, 1)) >= 1


def test_assign_queues_to_workers():
    assert_equals(
        [set("A"), set("B")],
        assign_queues_to_workers(2, {"A": [0], "B": [1]})
    )

    assert_equals(
        [set("A"), set("B"), set("A"), set("B"), set("B")],
        assign_queues_to_workers(5, {"A": [0, 2], "B": [1, 3, 4]})
    )

    assert_equals(
        [set("AB"), set("ABC"), set("AC"), set("BC")],
        assign_queues_to_workers(4, {"A": [0, 1, 2], "B": [0, 1, 3], "C": [1, 2 , 3]})
    )
