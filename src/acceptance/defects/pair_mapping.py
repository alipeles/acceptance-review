"""Judge each (defect, test) pair: would this test fail if the code had this defect?

The second stage of the defect-first shape (#312, #314), and the one that
replaces the question #312 exists to retire. The old mapping stage asked whether
a test *purports to evidence* an obligation — a judgement with no fact of the
matter, so a miss was unrecoverable and no rating could be traced back to it.
This asks something existential with an answer, per pair.

**Shadow, in this milestone.** The stage runs, records and reports; nothing reads
its verdicts. No rating moves, no recommendation changes, the completion verdict
is untouched. That is DR-312 decision 5's staged migration: with the surrounding
pipeline fixed, a carry defect shows up as a discrepancy against a stable
baseline instead of being one of three candidate causes for a rating that moved.

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

from pydantic import Field

from acceptance.carry import carry_key, decide
from acceptance.defects.reachability import Pair, form_pairs, prefilter
from acceptance.evidence.discovery import DiscoveredTest
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.model_base import PersistableModel
from acceptance.partition import partition
from acceptance.request_blocks import Block, BlockKind, assemble
from acceptance.review_state import (
    ChangeSet,
    Defect,
    DefectSet,
    EvidenceClassification,
    PairVerdict,
    UnjudgedCause,
    UnjudgedPair,
)
from acceptance.serialization import canonical_json
from acceptance.supplied_ids import UnusableAnswer, UnusableAnswerLog, constrain, scan

__all__ = [
    "PAIR_STAGE_LOGIC_VERSION",
    "DerivedSupport",
    "PairMappingResult",
    "defect_text",
    "derive_support",
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
entries. Keep `reason` to one short sentence."""


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


class _Judged(StrictResponseModel):
    defect_id: str
    fails: bool
    reason: str


class _TestVerdicts(StrictResponseModel):
    test_id: str
    defects: list[_Judged]


class _PairVerdicts(StrictResponseModel):
    tests: list[_TestVerdicts]


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


def _batches(pairs: list[Pair], size: int):
    """Partition `pairs` into requests, one test per request.

    **Per test rather than across tests, and the reason is the limit's meaning.**
    `constrain` narrows each id field independently, so a batch spanning several
    tests offers a schema in which every test x every defect is expressible — a
    batch of 3 pairs over 2 tests and 3 defects permits 6 answers. The prompt
    would ask for 3 and the schema would invite 6, and the extras would have to
    be dropped on the way back in, which is a silent filter of exactly the kind
    DR-164 exists to forbid.

    With one test per request the schema's cross product IS the offered set, so
    the limit counts the judgements the response is actually asked to carry.
    A test with more open defects than `size` is split across several requests.

    The cost is more requests than a test-major batch would issue. It is smaller
    than it looks — the system prompt and the shared prefix are what caching
    discounts, and the alternative restates every defect under every test in the
    prompt anyway — but it is a real figure for #316 to watch as pair counts grow.
    """
    by_test: dict[str, list[Pair]] = {}
    for pair in pairs:
        by_test.setdefault(pair.test.test_id, []).append(pair)
    batches = []
    for test_id in sorted(by_test):
        batches.extend(partition(by_test[test_id], size, key=lambda pair: pair.key))
    return batches


def _allowed(batch_pairs: list[Pair]) -> dict[str, list[str]]:
    return {
        "test_id": sorted({pair.test.test_id for pair in batch_pairs}),
        "defect_id": sorted({pair.defect.id for pair in batch_pairs}),
    }


def _ask(
    batch_pairs: list[Pair],
    batch,
    client: ModelClient,
    unusable: UnusableAnswerLog | None,
) -> dict[tuple[str, str], tuple[bool, str]]:
    """One request. Returns the verdicts it actually answered, by pair key.

    A pair missing from the return value was SHED — offered and not answered.
    The caller records it rather than defaulting it, because defaulting a shed
    judgement to *survives* is the silent un-covering this shape was chosen to
    make visible.
    """
    messages = assemble(
        [
            _defects_block(batch_pairs),
            Block(BlockKind.INSTRUCTIONS, _SYSTEM_PROMPT),
            Block(BlockKind.SUBJECT, _subject(batch_pairs)),
        ]
    )
    allowed = _allowed(batch_pairs)
    result = client.complete(
        messages,
        constrain(_PairVerdicts, allowed),
        batch.request_partition(),
        parse_as=_PairVerdicts,
        stage=_STAGE,
    )
    if unusable is not None:
        unusable.record(scan(result, allowed, _STAGE))

    answered: dict[tuple[str, str], tuple[bool, str]] = {}
    offered = {pair.key for pair in batch_pairs}
    for entry in result.tests:
        for judged in entry.defects:
            key = (judged.defect_id, entry.test_id)
            # An answer about a pair this batch never offered is not a verdict
            # about anything: the ids are valid individually, so the schema
            # cannot reject the combination, and accepting it would attach a
            # judgement to a pair nobody asked about.
            if key in offered:
                answered[key] = (judged.fails, judged.reason.strip())
    return answered


class DerivedSupport(PersistableModel):
    """What one criterion's pair verdicts imply about its support, and on what base.

    **Derived for comparison only in this milestone.** #316 flips the review's
    ratings onto this join; here it exists so the report can put it beside the
    rating the review actually gives, and so a discrepancy is visible while the
    baseline is still stable (DR-312 decision 5).

    `killed` and `total` are always rendered with the class, never the class
    alone. That is DR-312's resolved question 3: a bare "strongly supported" over
    an enumeration of one claims far more than it has, and disclosing the
    denominator lets a reader weigh a thin enumeration instead of trusting a
    threshold nobody can justify.
    """

    obligation_id: str
    evidence_class: EvidenceClassification
    killed: int
    total: int
    unjudged: int = 0


def derive_support(
    defect_sets: list[DefectSet],
    verdicts: list[PairVerdict],
    unjudged: list[UnjudgedPair],
) -> list[DerivedSupport]:
    """Reduce pair verdicts to one support class per criterion.

    Deterministic arithmetic over the carried parts, recomputed every run rather
    than stored — DR-312 decision 6 puts it in the "always recomputed" row for
    exactly that reason: it is free, and a stored copy is one more thing that can
    disagree with its inputs.

    A criterion whose enumeration is a reasoned empty set is `indeterminate`
    rather than `strongly_supported`: vacuously killing all zero of its defects
    is arithmetic, not evidence, and #316 gives that case a terminal state of its
    own. Calling it strongly supported here would flatter the comparison in
    precisely the direction #252 warns about.
    """
    killers: dict[str, set[str]] = {}
    for verdict in verdicts:
        if verdict.kills:
            killers.setdefault(verdict.defect_id, set()).add(verdict.test_id)
    unjudged_by_defect: dict[str, int] = {}
    for entry in unjudged:
        unjudged_by_defect[entry.defect_id] = unjudged_by_defect.get(entry.defect_id, 0) + 1

    derived: list[DerivedSupport] = []
    for entry in defect_sets:
        total = len(entry.defects)
        killed = sum(1 for defect in entry.defects if killers.get(defect.id))
        pending = sum(unjudged_by_defect.get(defect.id, 0) for defect in entry.defects)
        if total == 0:
            evidence_class: EvidenceClassification = "indeterminate"
        elif killed == total:
            evidence_class = "strongly_supported"
        elif killed:
            evidence_class = "partially_supported"
        else:
            evidence_class = "unsupported"
        derived.append(
            DerivedSupport(
                obligation_id=entry.obligation_id,
                evidence_class=evidence_class,
                killed=killed,
                total=total,
                unjudged=pending,
            )
        )
    return derived


def judge_pairs(
    defect_sets: list[DefectSet],
    tests: list[DiscoveredTest],
    change_set: ChangeSet,
    client: ModelClient,
    repo: Path = Path("."),
    batch_size: int = DEFAULT_PAIR_BATCH_SIZE,
    unusable: UnusableAnswerLog | None = None,
    prior: list[PairVerdict] | None = None,
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

    fresh: list[PairVerdict] = []
    for batch in _batches(to_ask, batch_size):
        batch_pairs = list(batch.items)
        answered = _ask(batch_pairs, batch, client, unusable)
        for pair in batch_pairs:
            if pair.key not in answered:
                # Shed: offered and unanswered. Recorded so it stays visible,
                # rather than defaulted to `survives` — the whole reason DR-314
                # took the shape where this is detectable at all.
                unjudged.append(
                    UnjudgedPair(
                        defect_id=pair.defect.id,
                        test_id=pair.test.test_id,
                        cause=UnjudgedCause.UNANSWERED,
                        reason="offered to the judge and not answered; no verdict was produced",
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
