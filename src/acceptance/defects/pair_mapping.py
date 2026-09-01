"""Judge each (defect, test) pair: would this test fail if the code had this defect?

The second stage of the defect-first shape (#312, #314), and the one that
replaces the question #312 exists to retire. The old mapping stage asked whether
a test *purports to evidence* an obligation — a judgement with no fact of the
matter, so a miss was unrecoverable and no rating could be traced back to it.
This asks something existential with an answer, per pair.

**These verdicts are the review's test-evidence rating** (#316). The stage ran in
shadow for one milestone — recording and reporting while the old mapping chain
still produced the rating — which is DR-312 decision 5's staged migration: with
the surrounding pipeline fixed, a carry defect showed up as a discrepancy against
a stable baseline instead of being one of three candidate causes for a rating
that moved. `defects/support.py` now reduces these verdicts to the class itself,
and the chain they were compared against is deleted.

## The response shape, and why this one

Each test carries an explicit verdict for EVERY defect offered with it, rather
than listing only the ones it catches. DR-314 piloted both against #315's
human-reviewed kill labels over three seeds each. The listing shape's recall
swung across 4 labelled kills between seeds; this one swung across 1, and its
worst seed beat the other's mean. It costs about twice the output tokens, which
never amortize — the caching discount is input-only — and that was accepted for
the stability and for shedding being detectable at all: a missing entry here is
visibly missing, where in the listing shape a shed judgement is indistinguishable
from a verdict of *survives* and silently un-covers a defect (DR-164's trap).

DR-173's failure mode did not reproduce, which is worth remembering if this is
ever revisited: its dense shape won by answering *no* more often, and the guard
metric says this one does not.

## Batching and carry

Pairs are partitioned so no request carries more judgements than the configured
limit — DR-164's mechanism, applied to the unit that actually varies here.

Carry is per pair, and its key deliberately excludes everything about the batch a
pair happened to land in (DR-269): a verdict must not re-derive because an
unrelated pair joined its request. The unit carries while the defect's own
content and that test's source digest are both unchanged — per TEST, never per
file (DR-293).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from acceptance.carry import carry_key, decide
from acceptance.concurrency import map_calls
from acceptance.defects.reachability import Pair, form_pairs, prefilter
from acceptance.evidence.discovery import DiscoveredTest
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.model_base import PersistableModel
from acceptance.partition import Batch
from acceptance.request_blocks import Block, BlockKind, assemble
from acceptance.review_state import (
    ChangeSet,
    Defect,
    DefectSet,
    PairVerdict,
    UnjudgedCause,
    UnjudgedPair,
)
from acceptance.serialization import canonical_json
from acceptance.supplied_ids import UnusableAnswer, UnusableAnswerLog, constrain, scan

__all__ = [
    "PAIR_STAGE_LOGIC_VERSION",
    "PairMappingResult",
    "defect_text",
    "judge_pairs",
    "source_digest",
]

_STAGE = "defect-to-test pair mapping"

# Bumped when this stage's own logic changes in a way that makes a stored verdict
# untrustworthy even though the defect and the test are untouched. Same contract
# as the enumeration stage's.
PAIR_STAGE_LOGIC_VERSION = 1

# Judgements per request. Below DR-164's shedding limit of roughly a thousand by
# a wide margin, and deliberately so: this response carries a verdict per pair
# rather than a list per test, so the same number of judgements produces more
# output than the mapping stage's did.
DEFAULT_PAIR_BATCH_SIZE = 40

# How many tests may share one request. This used to be fixed at 1 — see
# `_batches` for why that was chosen and why it changed.
#
# **The judgement budget is unchanged.** `DEFAULT_PAIR_BATCH_SIZE` still caps
# judgements per response, so four tests share a call by being offered a quarter
# as many defects each, not by making the response four times larger. That keeps
# DR-164's shedding argument intact: what binds is how many independent
# judgements one response carries, and that number has not moved.
#
# 4 rather than some larger number because the evidence supports the DIRECTION
# and not the magnitude. `docs/experiments/pair-response-shape/` measured 2-3
# tests per call against 1 and found 0.9688 recall against 0.8785 over nine draws
# each, but its calls carried at most 15 judgements where these carry 40, and it
# never varied the shape of the rectangle at a fixed budget. Treat 4 as the
# smallest step that gets the measured effect, not as a tuned value.
DEFAULT_TESTS_PER_BATCH = 4

_SYSTEM_PROMPT = """\
You are given concrete DEFECTS — specific ways the delivered code could be wrong
— and TESTS from the same codebase.

THE QUESTION, applied to one (defect, test) pair at a time:

    If the delivered code contained THIS DEFECT, would THIS TEST fail?

Answer it as a matter of fact about the test's assertions, not about what the
test is named or what it appears to be about. A test fails on a defect only when
the defect changes something the test actually asserts on. A test that exercises
the defective code but asserts nothing affected by the defect does NOT fail, and
neither does one that stubs out the defective behaviour.

Judge every pair independently. Do not assume a test that catches one defect
catches its neighbours, and do not assume a defect no test seems aimed at is
therefore uncaught.

For each test you are given, return one entry per DEFECT OFFERED WITH IT — every
one, not only the ones it catches — with `fails` true if that test would fail on
that defect and false if it would not. A test offered five defects returns five
entries.

An entry whose `fails` is true also carries `reason`: one short sentence naming
what the test asserts that the defect would change. An entry whose `fails` is
false carries NO `reason` field at all — not an empty one."""


class PairMappingResult(PersistableModel):
    """Every pair judged, every pair left unjudged, and every unusable answer.

    Kept together because they are one accounting of the pairs the stage was
    given: a pair in neither list was never formed, which is a third thing and
    not the same claim as either.
    """

    __test__ = False  # not a pytest test class

    verdicts: list[PairVerdict] = Field(default_factory=list)
    unjudged: list[UnjudgedPair] = Field(default_factory=list)
    unusable_answers: list[UnusableAnswer] = Field(default_factory=list)


class _Survives(StrictResponseModel):
    """A pair the test does not fail on. There is no `reason` field to pay for.

    **Why a union rather than an empty string.** `StrictResponseModel` forbids
    optional fields, because OpenAI strict mode has no notion of one, so an
    instruction to leave a reason blank can only ever make it empty — and an
    empty key is not free. Measured over the 68-pair pilot corpus, a written
    reason costs 18.5 output tokens and `"reason":""` still costs 10.0, so
    emptying recovers under half of what the field costs. Removing the field for
    this disposition recovers the rest.

    `fails` is `Literal[False]` rather than `bool` so the two members are told
    apart by a value the answer must carry anyway, not by which keys happen to be
    present. An answer claiming a test survives while carrying a reason fails
    validation instead of being quietly accepted as one shape or the other.
    """

    defect_id: str
    fails: Literal[False]


class _Kills(StrictResponseModel):
    """A pair the test does fail on, and the one short sentence saying why.

    Kept where `_Survives` drops it: a killing verdict is what becomes a coverage
    claim, and #312's premise is that a claim needs a traceable basis. A
    surviving verdict claims nothing, and the 12,323 surviving reasons #314's
    Gate 2 run recorded are the low-information half — 65.9% of them say either
    that the test does not assert on the defect or that it does not exercise it.
    """

    defect_id: str
    fails: Literal[True]
    reason: str


class _TestVerdicts(StrictResponseModel):
    test_id: str
    # `_Kills` first: pydantic resolves left to right, so the member with more
    # required fields is tried before the one with fewer.
    defects: list[_Kills | _Survives]


class _PairVerdicts(StrictResponseModel):
    tests: list[_TestVerdicts]


class _LenientJudged(BaseModel):
    """One judgement as *parsed*, admitting shapes the sent schema forbids.

    The union above is what the call ASKS for; this is what the reply is read
    with, and the gap between them is recorded rather than dropped. Same seam and
    same reason as `supplied_ids.py`: `ModelClient._validate` parses the whole
    response object, so parsing with the strict union would turn one wrongly
    shaped entry into an aborted review and discard the other thirty-nine usable
    judgements in its batch. The harness also runs against providers whose
    structured-output support differs, and one that ignores the schema would
    otherwise take the review down rather than lose one pair.

    `reason` is `None` when the entry carried no such key and `""` when it
    carried an empty one. `_ask` treats both as *no reason given*, and the
    distinction is kept here only so that the parse does not invent one.

    **An empty reason on a surviving pair is accepted, not rejected**, and the
    difference is not cosmetic. `""` is what the shape this union replaced
    emitted on every surviving pair, and what a provider honouring the schema
    only loosely would emit. Rejecting it would send every surviving pair of such
    a run to `unjudged` — roughly 99 pairs in 100 on the corpus this was measured
    against — turning a harmless deviation into a review with almost no verdicts.
    A *non-empty* reason where the schema offered no field for one is a different
    matter and is still refused.
    """

    defect_id: str
    fails: bool
    reason: str | None = None


class _LenientTestVerdicts(BaseModel):
    test_id: str
    defects: list[_LenientJudged]


class _LenientPairVerdicts(BaseModel):
    tests: list[_LenientTestVerdicts]


def defect_text(defect: Defect) -> str:
    """The identity a verdict is carried on.

    Everything about the defect the prompt renders, and only that. The `id` is
    excluded on purpose: ids are composed from the obligation id, so rewording a
    requirement moves every defect id beneath it, and keying on one would
    re-judge defects whose content never changed. Same reasoning as
    `DefectSet.obligation_text`.
    """
    return canonical_json(
        {
            "type": defect.type.value,
            "description": defect.description,
            "code_refs": sorted(defect.code_refs),
        }
    )


def source_digest(test: DiscoveredTest) -> str:
    """Content digest of one test's own source.

    Per test, never per file (DR-293): a file-level digest re-judges every test
    in a module when any one of them is edited, and #314's headline behaviour is
    that adding one test costs only that test's pairs.
    """
    return hashlib.sha256((test.source or "").encode("utf-8")).hexdigest()


def _key(client: ModelClient, defect: Defect, test: DiscoveredTest) -> str:
    """What a stored verdict is valid under.

    The UNCONSTRAINED schema, for the same reason the enumeration stage uses one:
    the schema actually sent carries per-call enum sets of this batch's defect and
    test ids, and folding those in would make a pair's key move because an
    unrelated pair joined its request. That is precisely the neighbouring-context
    dependence DR-269 forbids. What the key needs from the schema is its SHAPE,
    which is what moves when the response model changes.
    """
    return carry_key(
        system_prompt=_SYSTEM_PROMPT,
        response_schema=_PairVerdicts.model_json_schema(),
        model=client.model_for(_STAGE),
        temperature=client.temperature,
        seed=client.seed,
        stage_logic_version=PAIR_STAGE_LOGIC_VERSION,
        inputs={"defect_text": defect_text(defect), "source_digest": source_digest(test)},
    )


def _defects_block(batch_pairs: list[Pair]) -> Block:
    """The defects this call judges against — the part that does not move.

    Its own block, ahead of the per-test subject, because a provider reuses a
    PREFIX: it matches from the first byte and stops at the first difference.
    This list is identical across every call carrying the same defect chunk —
    166 of the 332 calls #314's Gate 2 run issued — while each call's test source
    is unique to it. Written into the subject alongside the test, as it was
    first, the shared list sat behind the unique source and could be reused by
    nothing: that run recorded a 0.0% cached-prompt share against the mapping
    stage's 38.2%.

    `evidence/mapping.py::_obligations_block` is the same move for the same
    reason, and `request_blocks.py` exists to make the ordering automatic.
    """
    lines = ["## Defects", ""]
    for defect in sorted(
        {pair.defect.id: pair.defect for pair in batch_pairs}.values(), key=lambda d: d.id
    ):
        lines.append(f"- id={defect.id} [{defect.type.value}]: {defect.description}")
    return Block(BlockKind.DEFECTS, "\n".join(lines))


def _subject(batch_pairs: list[Pair]) -> str:
    """This call's own content: the test, and which defects are offered with it.

    The defects are NAMED here and described above. That split is what lets the
    description list be shared; the names still appear beside the test so the
    model is told exactly which of the listed defects this test is being judged
    against, rather than left to infer that it is all of them.
    """
    by_test: dict[str, list[Pair]] = {}
    for pair in batch_pairs:
        by_test.setdefault(pair.test.test_id, []).append(pair)

    lines = ["## Tests to judge", ""]
    for test_id in sorted(by_test):
        pairs = by_test[test_id]
        offered = ", ".join(sorted(pair.defect.id for pair in pairs))
        lines.append(f"### test {test_id}")
        lines.append("")
        lines.append(pairs[0].test.source or "(source unavailable)")
        lines.append("")
        lines.append(f"Judge this test against these defects: {offered}")
        lines.append("")
    return "\n".join(lines)


def _batches(pairs: list[Pair], size: int, tests_per_batch: int = DEFAULT_TESTS_PER_BATCH):
    """Partition `pairs` into requests, each one a full rectangle.

    **A batch is a rectangle: every test in it is offered every defect in it.**
    That invariant is the whole design, and it is what the original one-test-per-
    request rule was really protecting. `constrain` narrows each id field
    independently, so a batch spanning several tests offers a schema in which
    every test x every defect is expressible. If the offered pairs are a ragged
    subset of that cross product, the prompt asks for fewer answers than the
    schema invites and the extras have to be dropped on the way back — a silent
    filter of exactly the kind DR-164 forbids. When the batch IS the cross
    product, there is nothing to drop, and the number of tests stops mattering.

    One test per request was the simplest way to guarantee a rectangle, not a
    finding that one test was better. Measurement says it is worse:
    `docs/experiments/pair-response-shape/` scored 2-3 tests per call at 0.9688
    mean recall against 0.8785 for one, over nine draws each against #315's
    human-reviewed kill labels, with the gap falling entirely on the cases where
    the two batched differently. Read its *Dropping `test_id`* section before
    changing this; in particular the shape of the rectangle at a fixed judgement
    budget is NOT measured, so `tests_per_batch` is a deliberate knob.

    Tests owed the SAME set of defects can share a call while keeping the
    rectangle; tests owed different sets cannot, so they are grouped by the
    defects they are still owed. That set is ragged in practice — `judge_pairs`
    drops pairs the prefilter proves unreachable and pairs carried from a prior
    run — which is why this groups rather than simply slicing the test list.

    `size` still caps judgements per response, so more tests in a call means
    fewer defects with each. A group whose tests are owed more defects than fit
    is split across several requests, as before.
    """
    by_test: dict[str, list[Pair]] = {}
    for pair in pairs:
        by_test.setdefault(pair.test.test_id, []).append(pair)

    # Tests owed an identical defect set, keyed by that set so the grouping is a
    # pure function of the input — batch composition must not depend on
    # iteration order or replay misses (see `partition.partition`).
    groups: dict[tuple[str, ...], list[str]] = {}
    for test_id, test_pairs in by_test.items():
        groups.setdefault(tuple(sorted({p.defect.id for p in test_pairs})), []).append(test_id)

    width = max(1, min(tests_per_batch, size))
    grouped: list[list[Pair]] = []
    for defect_ids in sorted(groups):
        test_ids = sorted(groups[defect_ids])
        for start in range(0, len(test_ids), width):
            tests_here = test_ids[start : start + width]
            # Whole defect set where it fits, otherwise as many as the judgement
            # budget allows once it is shared between this call's tests.
            depth = max(1, size // len(tests_here))
            for first in range(0, len(defect_ids), depth):
                wanted = set(defect_ids[first : first + depth])
                grouped.append(
                    sorted(
                        (
                            pair
                            for test_id in tests_here
                            for pair in by_test[test_id]
                            if pair.defect.id in wanted
                        ),
                        key=lambda pair: pair.key,
                    )
                )

    return [
        Batch(items=tuple(items), index=index, count=len(grouped), size=size)
        for index, items in enumerate(grouped)
    ]


def _scanned_ids(batch_pairs: list[Pair]) -> dict[str, list[str]]:
    """What this call supplied — the set `scan` checks the answer against.

    Both id fields, including `test_id`, which `_constrained_ids` deliberately
    leaves out of the schema. The two halves of the supplied-id guarantee are
    separable and this is the seam: `constrain` makes a wrong id unrepresentable,
    `scan` makes one detectable, and `supplied_ids.py::scan` says in its own
    docstring that it runs even where `constrain` already bound the field.
    """
    return {
        "test_id": sorted({pair.test.test_id for pair in batch_pairs}),
        "defect_id": sorted({pair.defect.id for pair in batch_pairs}),
    }


def _constrained_ids(batch_pairs: list[Pair]) -> dict[str, list[str]]:
    """What goes into the SCHEMA — the defect ids, and no longer the test ids.

    **Why `test_id` came out.** It was the only part of a pair request that
    changed from one call to the next, and a provider's prompt cache keys on a
    prefix that includes the response schema: #316's Gate 2 run measured a 0.0%
    cached share across all seven stages and 1,012 calls, with 1,762 distinct
    schemas across 1,762 pair calls, collapsing to 7 with this enum removed
    (#324). Leaving the field a plain `str` is what makes a call's schema
    identical to its neighbour's.

    **The judge is not thereby trusted.** `_scanned_ids` still supplies the test
    ids and `scan` still checks every answer against them, so an id that was
    never offered is recorded as an `UnusableAnswer` rather than believed, and
    `_ask` drops any pair the batch did not offer. `docs/experiments/
    pair-response-shape/` measured the risk over nine draws of each arm: with
    several tests in a call the judge wrote a real node id on 95.65-100% of
    entries, the single exception being one mangling of a real id that cost 3
    pair judgements on 1 draw, and recall was 0.9653 against the enumerated
    arm's 0.9688 — indistinguishable at that sample size.

    **This is why the two changes shipped together.** Leaving the field free
    while a call still carried ONE test measured 0.8021 against 0.8785, with no
    bad ids at all. Dropping the enum is safe with several tests in a call and
    was measured to be unsafe with one.
    """
    return {"defect_id": sorted({pair.defect.id for pair in batch_pairs})}


def _ask(
    batch_pairs: list[Pair],
    batch,
    client: ModelClient,
    tests_per_batch: int = DEFAULT_TESTS_PER_BATCH,
) -> tuple[
    dict[tuple[str, str], tuple[bool, str]],
    dict[tuple[str, str], str],
    list[UnusableAnswer],
]:
    """One request. The verdicts it answered usably, the ones it did not, and
    the ids it named that were never offered.

    **Records nothing.** Batches are issued concurrently, so anything appended
    to shared state in here would land in completion order and two runs over the
    same input would differ — see `concurrency.py`, rule 2. The unusable answers
    are handed back and recorded by the caller, in batch order.

    A pair in neither map was SHED — offered and not answered. The caller records
    it rather than defaulting it, because defaulting a shed judgement to
    *survives* is the silent un-covering this shape was chosen to make visible.

    A pair in the second map WAS answered, in a shape that cannot be honoured: a
    failing verdict with no reason, or a surviving one carrying a reason the
    schema does not offer it. Neither is a verdict, and neither is silence, so
    both are handed back with the sentence saying which — the caller records them
    as unjudged rather than guessing which half of the answer to believe.
    """
    messages = assemble(
        [
            _defects_block(batch_pairs),
            Block(BlockKind.INSTRUCTIONS, _SYSTEM_PROMPT),
            Block(BlockKind.SUBJECT, _subject(batch_pairs)),
        ]
    )
    result = client.complete(
        messages,
        constrain(_PairVerdicts, _constrained_ids(batch_pairs)),
        # `tests_per_batch` folded in beside `size` for the reason
        # `Batch.request_partition` gives about `size`: it is a run control, so
        # changing it must invalidate every recorded transcript, and it would not
        # otherwise — two values produce identical batches whenever a group holds
        # fewer tests than either.
        {**batch.request_partition(), "tests_per_batch": tests_per_batch},
        parse_as=_LenientPairVerdicts,
        stage=_STAGE,
    )
    answered: dict[tuple[str, str], tuple[bool, str]] = {}
    unusable_shape: dict[tuple[str, str], str] = {}
    offered = {pair.key for pair in batch_pairs}
    for entry in result.tests:
        for judged in entry.defects:
            key = (judged.defect_id, entry.test_id)
            # An answer about a pair this batch never offered is not a verdict
            # about anything: the ids are valid individually, so the schema
            # cannot reject the combination, and accepting it would attach a
            # judgement to a pair nobody asked about.
            if key not in offered:
                continue
            reason = (judged.reason or "").strip()
            if judged.fails and not reason:
                unusable_shape[key] = (
                    "answered as failing but carrying no reason; the answer does not "
                    "match either shape the request offered, so no verdict was produced"
                )
            elif not judged.fails and reason:
                unusable_shape[key] = (
                    "answered as not failing but carrying a reason; the answer does not "
                    "match either shape the request offered, so no verdict was produced"
                )
            else:
                answered[key] = (judged.fails, reason)
    return answered, unusable_shape, scan(result, _scanned_ids(batch_pairs), _STAGE)


# `DerivedSupport` and `derive_support` used to live here, deriving a support
# class for the report to show BESIDE the rating the review actually gave — the
# shadow comparison that made #314's landing attributable. #316 flipped the
# review onto that derivation, so it moved to `defects/support.py` and became
# the rating rather than a column next to it. Two functions of one name doing
# different things is the drift this file exists to avoid, so the shadow copy
# was deleted rather than left for a caller to pick the wrong one.


def judge_pairs(
    defect_sets: list[DefectSet],
    tests: list[DiscoveredTest],
    change_set: ChangeSet,
    client: ModelClient,
    repo: Path = Path("."),
    batch_size: int = DEFAULT_PAIR_BATCH_SIZE,
    unusable: UnusableAnswerLog | None = None,
    prior: list[PairVerdict] | None = None,
    tests_per_batch: int = DEFAULT_TESTS_PER_BATCH,
) -> PairMappingResult:
    """Judge every pair the prefilter does not prove unreachable.

    With `prior`, a verdict whose defect content and test source are both
    unchanged is reused and no judgement is issued for it — so adding one test
    between two continued runs costs that test's pairs and nothing else.
    """
    defects = [defect for entry in defect_sets for defect in entry.defects]
    pairs = form_pairs(defects, tests)
    judged, unjudged = prefilter(pairs, repo, change_set)

    prior_by_identity = {(entry.defect_text, entry.test_id): entry for entry in (prior or [])}

    carried: list[PairVerdict] = []
    to_ask: list[Pair] = []
    keys: dict[tuple[str, str], str] = {}
    for pair in judged:
        current = _key(client, pair.defect, pair.test)
        keys[pair.key] = current
        candidate = prior_by_identity.get((defect_text(pair.defect), pair.test.test_id))
        decision = decide(
            f"{pair.defect.id}/{pair.test.test_id}",
            prior=candidate,
            prior_key=candidate.carry_key if candidate else None,
            current_key=current,
        )
        if decision.carried:
            # Re-identified onto this run's defect id, which may differ from the
            # one the verdict was recorded under: the carry matched on content.
            carried.append(
                candidate.model_copy(
                    update={"defect_id": pair.defect.id, "carried_from": candidate.carry_key}
                )
            )
        else:
            to_ask.append(pair)

    # Batches are issued CONCURRENTLY and their answers consumed in batch
    # order. Each batch judges its own pairs and reads no other batch's answer,
    # so there was never a reason to wait for one before sending the next — and
    # this stage issues by far the most calls of any, 332 of one review's 375 at
    # #314's Gate 2 and several thousand on a large diff.
    #
    # The request is untouched, so every recorded transcript still replays.
    batches = _batches(to_ask, batch_size, tests_per_batch)
    answers = map_calls(
        batches, lambda batch: _ask(list(batch.items), batch, client, tests_per_batch)
    )

    fresh: list[PairVerdict] = []
    for batch, (answered, unusable_shape, scanned) in zip(batches, answers):
        batch_pairs = list(batch.items)
        # Recorded here rather than inside the call, so the log reads in batch
        # order however the calls finished (`concurrency.py`, rule 2).
        if unusable is not None:
            unusable.record(scanned)
        for pair in batch_pairs:
            if pair.key not in answered:
                # Offered and no usable verdict came back — either nothing at all
                # (shed) or something that is not a verdict. Recorded either way,
                # rather than defaulted to `survives`, which is the whole reason
                # DR-314 took the shape where this is detectable at all.
                #
                # Both carry `UNANSWERED`, because from the review's side no
                # answer was obtained, and the sentence says which happened. They
                # arguably want separate causes — the remedies differ, a shed
                # judgement meaning the batch is too large and a misshapen one
                # meaning the provider is not honouring the schema — but that is
                # a third value in a persisted enum, which is not a change to
                # make in passing.
                unjudged.append(
                    UnjudgedPair(
                        defect_id=pair.defect.id,
                        test_id=pair.test.test_id,
                        cause=UnjudgedCause.UNANSWERED,
                        reason=unusable_shape.get(
                            pair.key,
                            "offered to the judge and not answered; no verdict was produced",
                        ),
                    )
                )
                continue
            fails, reason = answered[pair.key]
            fresh.append(
                PairVerdict(
                    defect_id=pair.defect.id,
                    test_id=pair.test.test_id,
                    kills=fails,
                    reason=reason,
                    defect_text=defect_text(pair.defect),
                    test_digest=source_digest(pair.test),
                    carry_key=keys[pair.key],
                )
            )

    # Sorted on the pair identity rather than on the order pairs were formed in,
    # so a carried verdict and a fresh one land in the same place. Byte-identical
    # reruns depend on it: the two runs partition the same pairs differently the
    # moment one of them carries.
    return PairMappingResult(
        verdicts=sorted(carried + fresh, key=lambda entry: (entry.defect_id, entry.test_id)),
        unjudged=sorted(unjudged, key=lambda entry: (entry.defect_id, entry.test_id)),
        unusable_answers=[],
    )
