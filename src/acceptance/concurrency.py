"""Issue a stage's independent calls at the same time instead of one after another.

Every batched stage was a `for` loop around `client.complete`, so a review's
calls ran strictly in sequence — each one a full round trip to the provider,
with nothing else happening while it was in flight. The calls in one stage's
loop are independent by construction: each judges its own batch, and none reads
another's answer. Waiting for them one at a time bought nothing.

The cost was the whole wall-clock of a review. #314's Gate 2 issued 332 pair
calls; a later run on a larger diff issued several thousand, and the review took
longer than the work it was reviewing.

## What this is not

**It is not a determinism control, and it re-records nothing.** Concurrency
changes when a request is sent, never what is in it. Every request key is
unchanged, so every recorded transcript still replays and no benchmark figure
crosses a boundary. That is the whole reason this is a safe change to make on
its own: it has no interaction with the corpus.

## The three rules that keep a parallel run byte-identical

**1. Results come back in INPUT order.** `ThreadPoolExecutor.map` yields in the
order the items went in, not the order they finished, so a caller building a
list gets the same list every run. A raw `as_completed` loop would not, and is
the obvious way to write this wrongly.

**2. Side effects belong to the caller, after the pool.** `call` must not touch
shared state — not the unusable-answer log, not an accumulating result list.
Appending from several threads is safe from corruption (the interpreter lock
sees to that) but the ORDER varies, and an unusable-answer list in a different
order is a different review. Do the work in the pool; record it in the loop that
consumes the results.

**3. The client's own bookkeeping must stay order-free, and is.** Every reducer
over `ModelClient`'s observed calls — `models_by_stage`, `controls_in_force`,
`partition_sizes_in_force`, `usage.summarize` — folds into sets, sums or
sorted dicts, and `summarize`'s docstring already required order-independence
for a different reason: an incremental re-run issues its live calls in a
different sequence from the run that recorded them. Adding threads does not
introduce that requirement, it relies on one that was already there.

An exception raised inside the pool surfaces when the results are iterated, so a
failing call still aborts the run as it did before. Nothing half-written
survives: `_persist_live_call` writes a transcript only after the reply
validates.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")

# Calls in flight per stage. Sized for a provider's concurrency allowance rather
# than for this machine — the work is entirely waiting on a network round trip,
# so the useful ceiling is what the provider will accept at once, not how many
# cores are free. Eight is conservative enough not to trip a rate limit on a
# default account and still turns a several-thousand-call stage from hours into
# a fraction of one.
#
# It is not a determinism control and is deliberately not hashed into any
# request: changing it changes when calls are sent, never what they say.
DEFAULT_MAX_IN_FLIGHT = 8


def map_calls(
    items: Sequence[T],
    call: Callable[[T], R],
    max_in_flight: int = DEFAULT_MAX_IN_FLIGHT,
) -> list[R]:
    """Run `call` over `items` concurrently, in input order.

    `call` must be free of shared-state side effects — see rule 2 in the module
    docstring. Returns a list the caller can zip back against `items`.

    One item, or a limit of one, runs inline. That is not only an optimisation:
    it keeps the single-call path free of a thread, so a stack trace from a
    stage that issues one call reads the way it always did.
    """
    if max_in_flight < 1:
        raise ValueError(f"max_in_flight must be at least 1, got {max_in_flight}")
    ordered = list(items)
    if len(ordered) <= 1 or max_in_flight == 1:
        return [call(item) for item in ordered]
    with ThreadPoolExecutor(max_workers=min(max_in_flight, len(ordered))) as pool:
        return list(pool.map(call, ordered))


def flatten(results: Iterable[Iterable[R]]) -> list[R]:
    """One list out of a per-batch list of lists, order preserved."""
    return [item for group in results for item in group]
