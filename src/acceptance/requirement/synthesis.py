"""Synthesis: the obligation set, built from the mandate's claims (#437).

`docs/decomposition-redesign.md` §2 (Obligation, Provenance) and §5 step 3. One
model call takes every claim and returns the obligations, each citing the claims
that support it. This is where meaning is assigned: several claims about one
behaviour become one obligation, a claim saying two things becomes two, and an
obligation the claims plainly entail is included with no question asked.

**Typed fields in, ids out.** The model sees each claim as an id, its line, the
heading it sits under and its text; never the mandate's markdown. It cites claims
by id, and the ids are constrained to the ones supplied. An obligation whose
citations are all unknown cannot rest on the mandate, so it is dropped and
recorded as an unusable answer; an unknown id beside a known one is dropped from
the citation and recorded the same way.

**The type settles the evidence an obligation needs.** Four types
(`docs/DR-437-obligation-types.md`). A constraint and a scope exclusion are
settled by reading the change (design §3), a test deliverable by the test, and a
requested behaviour by code and a test. That is a rule, so the code applies it and
the model is not asked.

**Recorded, not yet consumed.** The pipeline persists these beside the
per-requirement obligations; nothing downstream reads them until the switch-over
issue. That keeps any movement in a rating or verdict attributable while
synthesis is only being recorded.
"""

from __future__ import annotations

import re
from typing import Literal

from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.request_blocks import Block, BlockKind, assemble
from acceptance.requirement.spans import normalise
from acceptance.review_state import (
    ClaimSet,
    Obligation,
    ObligationType,
    Reference,
    RequiredEvidence,
)
from acceptance.supplied_ids import UnusableAnswer, UnusableAnswerLog, constrain, scan

__all__ = ["SYNTHESIS_STAGE", "synthesize"]

SYNTHESIS_STAGE = "synthesis"
_STAGE = SYNTHESIS_STAGE

_SYSTEM_PROMPT = """\
You are an expert acceptance reviewer. You are given a change mandate — the task
a software change was asked to deliver — as a list of claims. Each claim is one
sentence or line of the mandate, word for word, with an id, the line it starts
on, and the heading it sits under.

Produce the obligations: the requirements the delivered change must meet, which
a reviewer would check before accepting it. You are writing requirements, not
rewriting claims.

CITING CLAIMS

Every obligation cites the claims that support it, by id. Cite every claim that
supports it, and only those.

- Several claims about one behaviour are ONE obligation citing all of them. A
  sentence restating an earlier one is a second citation, never a second
  obligation.
- One claim saying several things is SEVERAL obligations, each citing that
  claim. "Implement X using subsystem Y" is a requested behaviour, X, and a
  constraint, that X uses Y.
- A claim may support no obligation at all: an aside, a heading, a reference.

WHAT THE CLAIMS PLAINLY ENTAIL

Include what the claims plainly entail, not only what they say. "A CRUD
interface for X" entails that X can be deleted, so deleting X is an obligation
citing that claim, even though no claim says "delete". The test is whether you
can defend the obligation from the cited claims alone. Anything you cannot
defend that way is not an obligation; leave it out. Do not guess at qualifiers,
values or behaviours the claims do not settle.

TYPES

Give every obligation exactly one type:

- `requested_behavior`: something the delivered change must do, observable from
  outside it by a caller, a user, a downstream system, or a file or record it
  produces. Most obligations are this.
- `constraint`: a condition on how the work is done that a reader settles by
  looking at the change, not by running it: use an existing subsystem or
  utility, conform to an existing interface, put the work where that kind of
  work lives, use a named library or a pinned version.
- `scope_exclusion`: work this change must NOT do.
- `test_deliverable`: a test that is itself the thing delivered, such as a
  regression test reproducing a reported defect.

A claim asking for a test of a behaviour — "add a test that X", "a test asserts
X" — yields the obligation X, typed `requested_behavior`. Use
`test_deliverable` only when the test is the deliverable in its own right.

HOW TO STATE AN OBLIGATION

`description` states the requirement in one sentence. `observable_behavior`
names what a reviewer would look for to confirm it.

State a requested behaviour or a constraint as a property the change must HOLD,
never as a prohibition: "don't change the checkout behaviour" becomes "the
existing checkout behaviour is preserved".

A scope exclusion names WORK, and work has no positive form. State it as
absence — "The change does not alter how invoices are numbered." — never as
work to do and never as a property to keep. Its `observable_behavior` names the
work whose presence in the change would refute it ("invoice numbering logic
appearing in the diff"). A clause explaining why the work is excluded ("which
another team owns") is an aside; read past it.

`explicit` is true when a cited claim states the obligation outright, false when
the claims plainly entail it. `importance` is `critical` when the change would
be unacceptable without it, `normal` otherwise.

`id` is a short kebab-case slug naming the obligation. Write the reason first:
one sentence saying how the cited claims support the obligation.
"""


_Type = Literal["requested_behavior", "constraint", "scope_exclusion", "test_deliverable"]


class _SynthesizedObligation(StrictResponseModel):
    """One obligation. `claim_id` plus `more_claim_ids` makes "at least one
    citation" a property of the shape: a minimum on a list cannot be expressed in
    a strict schema, so an obligation citing nothing is unsayable instead."""

    id: str
    reason: str
    claim_id: str
    more_claim_ids: list[str]
    type: _Type
    description: str
    observable_behavior: str
    explicit: bool
    importance: Literal["critical", "normal"]


class _Synthesis(StrictResponseModel):
    obligations: list[_SynthesizedObligation]


# The evidence each type requires, and why. A rule, so it is the code's, and the
# reason a reader argues with is the rule's, stated once (as DR-310 did for
# scope exclusions).
_EVIDENCE: dict[ObligationType, tuple[RequiredEvidence, str]] = {
    ObligationType.REQUESTED_BEHAVIOR: (RequiredEvidence.CODE_AND_TESTS, ""),
    ObligationType.CONSTRAINT: (
        RequiredEvidence.CODE_ONLY,
        (
            "A constraint on how the work is done is settled by reading the change; "
            "it is owed code evidence only, never a test."
        ),
    ),
    ObligationType.SCOPE_EXCLUSION: (
        RequiredEvidence.CODE_ONLY,
        (
            "A scope exclusion is satisfied by work not done, which a reader confirms "
            "by inspecting the change; it is owed code evidence only, never a test."
        ),
    ),
    ObligationType.TEST_DELIVERABLE: (
        RequiredEvidence.TESTS_ONLY,
        "The test is the deliverable; it asks for no source change of its own.",
    ),
}


def synthesize(
    claim_set: ClaimSet | None,
    client: ModelClient,
    unusable_answers: UnusableAnswerLog | None = None,
) -> list[Obligation]:
    """The obligation set built from `claim_set`'s claims, in the model's order.

    One call for the whole mandate. No claims, no call.
    """
    if claim_set is None or not claim_set.claims:
        return []

    claim_ids = [claim.id for claim in claim_set.claims]
    allowed = {"claim_id": claim_ids, "more_claim_ids": claim_ids}
    messages = assemble(
        [
            Block(BlockKind.INSTRUCTIONS, _SYSTEM_PROMPT),
            Block(BlockKind.SUBJECT, _user_prompt(claim_set)),
        ]
    )
    result = client.complete(
        messages,
        constrain(_Synthesis, allowed),
        parse_as=_Synthesis,
        stage=SYNTHESIS_STAGE,
    )
    if unusable_answers is not None:
        unusable_answers.record(scan(result, allowed, SYNTHESIS_STAGE))
    return _obligations(claim_set, result, unusable_answers)


def _obligations(
    claim_set: ClaimSet,
    result: _Synthesis,
    unusable_answers: UnusableAnswerLog | None,
) -> list[Obligation]:
    """Each answered obligation with its citations resolved to claims.

    Citations are kept in mandate order and de-duplicated, so the same answer
    always yields the same bytes. An obligation left citing nothing is dropped
    and recorded: it would be an obligation resting on no text of the mandate.
    """
    order = {claim.id: index for index, claim in enumerate(claim_set.claims)}
    by_id = {claim.id: claim for claim in claim_set.claims}
    seen: set[str] = set()
    problems: list[UnusableAnswer] = []
    out: list[Obligation] = []
    for answer in result.obligations:
        cited = sorted(
            {cid for cid in [answer.claim_id, *answer.more_claim_ids] if cid in by_id},
            key=order.__getitem__,
        )
        if not cited:
            problems.append(
                UnusableAnswer(
                    stage=SYNTHESIS_STAGE,
                    field="claim_id",
                    returned_id=answer.id,
                    reason="the obligation cites no claim that was supplied, so it was dropped",
                )
            )
            continue
        obligation_type = ObligationType(answer.type)
        evidence, evidence_reason = _EVIDENCE[obligation_type]
        out.append(
            Obligation(
                id=_unique(_slug(answer.id), seen),
                description=answer.description.strip(),
                type=obligation_type,
                importance=answer.importance,
                explicit=answer.explicit,
                observable_behavior=answer.observable_behavior.strip(),
                source_spans=[by_id[cid].span for cid in cited],
                claims=[Reference(kind="claim", id=cid) for cid in cited],
                provenance="stated",
                required_evidence=evidence,
                required_evidence_reason=evidence_reason,
                satisfied_by_absence=obligation_type is ObligationType.SCOPE_EXCLUSION,
            )
        )
    if unusable_answers is not None:
        unusable_answers.record(problems)
    return out


def _user_prompt(claim_set: ClaimSet) -> str:
    """One entry per claim: id, line, heading, text. Typed fields, not markdown."""
    headings = {unit.id: unit.heading for unit in claim_set.units}
    lines = ["The mandate's claims, in order:", ""]
    for claim in claim_set.claims:
        heading = headings.get(claim.unit_id)
        lines.append(
            f"[{claim.id}] line {claim.line}, under: "
            f"{heading if heading is not None else '(no heading)'}"
        )
        lines.append(f"    {normalise(claim.text)}")
    return "\n".join(lines)


def _slug(value: str) -> str:
    """A kebab-case slug, never empty."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "obligation"


def _unique(candidate: str, seen: set[str]) -> str:
    """Suffix a repeated id with -2, -3, … in answer order."""
    unique_id = candidate
    suffix = 2
    while unique_id in seen:
        unique_id = f"{candidate}-{suffix}"
        suffix += 1
    seen.add(unique_id)
    return unique_id
