"""Request partitioning — decisions per request (plan §3.2, DR-164).

A schema-constrained call degrades by *shedding work* long before it runs out of
context. The M4 mapping stage asked one call for tests x obligations relevance
judgments — 1,632 on a review of this repo — and returned a well-formed entry per
test with an empty `obligation_ids` list for up to 80 of 96 tests. The response
stayed schema-valid, so nothing downstream noticed, and the review reported the
reviewer's own failure as the user's untested change.

Size was measured and is not the binding constraint: the largest prompt used 2.5%
of the model's context window. What binds is how many independent judgments one
response is asked to carry. So the fix partitions the *judgments*, not the bytes.

This module is the generic mechanism. It is deliberately not applied everywhere:
partitioning is cheap only when the repeated context is small relative to the axis
being split, which measurement says is true of mapping (obligations are 4% of the
prompt) and false of the diff-dominated stages, where it would cost ~3.8x the
tokens on stages with no observed failure (DR-164, decision 2).
"""

from __future__ import annotations

from typing import Any, Callable, Generic, Iterable, Sequence, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Batch(BaseModel, Generic[T]):
    """One partition of a stage's input, and the request it describes."""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    items: tuple[T, ...]
    index: int = Field(ge=0)
    count: int = Field(ge=1)
    size: int = Field(ge=1)  # the configured control, not len(items)

    def request_partition(self) -> dict[str, Any]:
        """The partition descriptor to fold into the hashed request.

        Only `size` is included, and deliberately. It is a run control, so
        changing it must invalidate every recorded transcript exactly as changing
        the seed does (#154) — and it would not otherwise, because two batch
        sizes can produce identical batches when the input is smaller than both.

        `index` and `count` are left out for the opposite reason: the messages
        already differ between batches, so including them would buy no
        distinguishing power while making a batch's key depend on how many
        batches follow it. Appending one test would then invalidate the first
        batch's transcript even though its content is unchanged.
        """
        return {"size": self.size}


def partition(
    items: Iterable[T], size: int, key: Callable[[T], Any]
) -> list[Batch[T]]:
    """Split `items` into batches of at most `size`, in a stable order.

    Ordering is imposed here rather than trusted from upstream: batch composition
    must be a pure function of the input or request keys churn between runs and
    replay misses, and a caller's ordering guarantee is one refactor away from
    being untrue. Sorting on `key` makes the guarantee local and testable.
    """
    if size < 1:
        raise ValueError(f"batch size must be at least 1, got {size}")

    ordered: Sequence[T] = sorted(items, key=key)
    if not ordered:
        return []

    groups = [ordered[start : start + size] for start in range(0, len(ordered), size)]
    return [
        Batch(items=tuple(group), index=index, count=len(groups), size=size)
        for index, group in enumerate(groups)
    ]
