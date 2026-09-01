"""Issuing a stage's calls at once without letting the run depend on the order
they finish.

Two properties, and they fail for different reasons. The calls must actually
overlap, or the change bought nothing; and the result must not depend on which
one finished first, or the change bought a faster nondeterministic reviewer,
which is worse than a slow deterministic one (M0.5).

The second is the one defect injection would find. A `for` loop over
`as_completed` is the obvious way to write this, passes any test that only
checks the results are all present, and silently reorders every list a stage
builds.
"""

from __future__ import annotations

import threading
import time

import pytest

from acceptance.concurrency import DEFAULT_MAX_IN_FLIGHT, flatten, map_calls


def test_results_come_back_in_input_order_not_completion_order():
    """The load-bearing property. Later items finish first here, by construction,
    so a pool that yielded on completion returns the reverse."""

    def slow_then_fast(n: int) -> int:
        time.sleep((5 - n) * 0.02)
        return n

    assert map_calls([0, 1, 2, 3, 4], slow_then_fast) == [0, 1, 2, 3, 4]


def test_the_calls_actually_overlap():
    """Otherwise this is a `for` loop with extra machinery.

    Measured by peak concurrent entries rather than by wall-clock, which is
    flaky on a loaded machine and proves less: two calls that ran at the same
    time is the claim.
    """
    in_flight = 0
    peak = 0
    lock = threading.Lock()

    def watched(_: int) -> None:
        nonlocal in_flight, peak
        with lock:
            in_flight += 1
            peak = max(peak, in_flight)
        time.sleep(0.05)
        with lock:
            in_flight -= 1

    map_calls(list(range(8)), watched, max_in_flight=4)

    assert peak > 1


def test_no_more_than_the_limit_run_at_once():
    """The limit is a promise to the provider, not a hint."""
    in_flight = 0
    peak = 0
    lock = threading.Lock()

    def watched(_: int) -> None:
        nonlocal in_flight, peak
        with lock:
            in_flight += 1
            peak = max(peak, in_flight)
        time.sleep(0.05)
        with lock:
            in_flight -= 1

    map_calls(list(range(20)), watched, max_in_flight=3)

    assert peak <= 3


def test_a_limit_of_one_is_the_serial_path_and_still_ordered():
    assert map_calls([3, 1, 2], lambda n: n * 2, max_in_flight=1) == [6, 2, 4]


def test_a_single_item_runs_inline_without_a_thread():
    """Not only an optimisation: a stack trace from a one-call stage should read
    the way it always did, without a pool frame in the middle."""
    seen: list[str] = []

    def record(_: int) -> None:
        seen.append(threading.current_thread().name)

    map_calls([0], record)

    assert seen == [threading.current_thread().name]


def test_an_exception_surfaces_rather_than_being_swallowed():
    """A failing call aborted the run before this change and must still. A pool
    that logged and continued would turn a broken provider into a review with
    quietly missing judgements."""

    def boom(n: int) -> int:
        if n == 2:
            raise ValueError("call 2 failed")
        return n

    with pytest.raises(ValueError, match="call 2 failed"):
        map_calls([0, 1, 2, 3], boom)


def test_an_empty_input_issues_nothing():
    assert map_calls([], lambda _: pytest.fail("a call was issued for no items")) == []


def test_a_limit_below_one_is_refused():
    """Silently treating 0 as 1 would make a misconfigured run look serial for a
    reason nobody could find."""
    with pytest.raises(ValueError, match="at least 1"):
        map_calls([1, 2], lambda n: n, max_in_flight=0)


def test_flatten_preserves_order_across_batches():
    assert flatten([[1, 2], [], [3], [4, 5]]) == [1, 2, 3, 4, 5]


def test_the_default_limit_is_more_than_one():
    """A default of 1 would leave every stage serial while every call site looked
    parallel — the change present in form and absent in effect."""
    assert DEFAULT_MAX_IN_FLIGHT > 1
