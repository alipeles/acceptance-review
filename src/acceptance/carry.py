"""Deciding whether a stored result may be reused, for any stage (#251, #286).

#269 built this for decomposition. #251 is the second stage to need it, and two
callers is when the rule is worth stating once rather than twice — at one it is
speculative, and by the seventh it is six near-copies. #286 carries the plan for
the remaining stages.

**The rule, independent of what is being carried.** A stored result may be reused
exactly when all of:

1. the unit is still there, matched by whatever identity that stage uses;
2. re-deriving it today would issue the *same request* — the carry key;
3. the code that turns a response into a result has not moved — the stage-logic
   version, which the request key cannot see;
4. the stored result still fits the inputs it is being reused against, which is
   the one check only the stage can make.

Everything stage-specific lives in what the caller passes: what a unit is, what
its identity is, which of its inputs go into the key, and what (4) means. This
module holds no notion of a requirement, a criterion, or a test.

**Why the refusal is a value and not a bool.** Both callers have to *report* why
they re-derived something. The decompose ledger records a disposition per
requirement, and #251's re-judgement has to hand the model the changes its new
answer must rest on. A bare `False` throws away the only part a reader needs.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from acceptance.serialization import canonical_json


class Refusal(str, Enum):
    """Why a stored result was not reused. One cause each, named separately
    because they fail for different reasons and a reader acts on them
    differently."""

    NO_PRIOR = "no_prior"
    """Nothing stored for this unit — a new unit, or no continued run named."""

    STAGE_LOGIC_MOVED = "stage_logic_moved"
    """Recorded under different stage logic: the tool changed under the answer."""

    REQUEST_MOVED = "request_moved"
    """Re-deriving it today would issue a different request."""

    NOT_APPLICABLE = "not_applicable"
    """The stored result no longer fits the inputs it would be reused against."""


@dataclass(frozen=True)
class Decision:
    """Whether one unit's stored result may be reused, and why not when it may
    not."""

    identity: str
    prior: Any | None = None
    refusal: Refusal | None = None

    @property
    def carried(self) -> bool:
        return self.refusal is None and self.prior is not None


def decide(
    identity: str,
    *,
    prior: Any | None,
    prior_key: str | None = None,
    current_key: str | None = None,
    stage_logic_matches: bool = True,
    still_applies: bool = True,
) -> Decision:
    """Apply the four checks, in the order a reader would want them reported.

    Order matters only for which refusal is named when more than one holds, and
    the order here is most-fundamental-first: a missing prior is not a stale one,
    and a tool that moved under the answer explains a key mismatch rather than
    being explained by it.

    `still_applies` is the stage's own check and defaults to True, because most
    stages have none: decomposition uses it for `stale_spans`, where a carried
    obligation quotes text its requirement no longer has.
    """
    if prior is None:
        return Decision(identity, refusal=Refusal.NO_PRIOR)
    if not stage_logic_matches:
        return Decision(identity, prior=prior, refusal=Refusal.STAGE_LOGIC_MOVED)
    if prior_key != current_key:
        return Decision(identity, prior=prior, refusal=Refusal.REQUEST_MOVED)
    if not still_applies:
        return Decision(identity, prior=prior, refusal=Refusal.NOT_APPLICABLE)
    return Decision(identity, prior=prior)


def carry_key(
    *,
    system_prompt: str,
    response_schema: dict,
    model: str,
    temperature: float,
    seed: int | None,
    stage_logic_version: int,
    inputs: Mapping[str, Any],
) -> str:
    """The key a carried entry is valid under.

    A carried entry stays valid exactly while re-deriving it today would issue the
    same request — so this hashes the determinism controls `llm.py` puts in a
    request key, plus the stage-logic version the request cannot see, plus the
    unit's **own** inputs.

    `inputs` is spread into the payload rather than nested under a key of its own,
    so a stage naming `{"requirement_text": ...}` hashes exactly what #269's
    decompose-specific version hashed. That is not tidiness: every ledger entry
    already on disk holds a key computed the old way, and a payload change would
    make all of them stale and re-derive every requirement — the churn this whole
    mechanism exists to remove.

    **What a caller should leave out: everything the unit does not own.** The
    decompose prompt carries the whole task file as context on every call (#178),
    so the real request key for one requirement moves whenever any *other* is
    edited. Hashing that would make a carried entry valid only when nothing
    changed at all, which is the one case where carrying buys nothing. The cost is
    real — an unchanged unit could legitimately be judged differently once its
    neighbours change, and carrying suppresses that — and it is the trade the
    feature exists to make. See `docs/DR-269-carry-key-excludes-registry-context.md`.
    """
    payload = {
        "system_prompt": system_prompt,
        "response_schema": response_schema,
        "model": model,
        "temperature": temperature,
        "seed": seed,
        "stage_logic_version": stage_logic_version,
        **dict(inputs),
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
