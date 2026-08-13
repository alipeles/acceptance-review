"""Discrimination judgment (M5.2, §9.3 central question).

The core of test-semantic analysis: *would the mapped tests actually FAIL if the
implementation violated this criterion in a plausible way?* A test only
evidences a criterion if a realistic defect would make it fail — not because it
invokes the code, is named for it, or lives in a green suite (§9.3).

Per criterion, the model names one or more PLAUSIBLE defects (realistic mistakes
a competent-but-fallible developer might ship that violate that criterion), and
judges whether the mapped tests would catch each — reasoning over the three
§9.3 dimensions: do the test INPUTS distinguish the correct behavior from the
defect (or coincidentally give the same result?), are boundaries/negatives
exercised, do the ASSERTIONS target the required result. A criterion is
DISCRIMINATING iff its tests catch at least one plausible defect — §9.3's bright
line separating real evidence from nominal.

This is a semantic judgment (a static PREDICTION of which mapped mutants a test
would kill, §8.2), so it is a schema-constrained model call through the M0.4
harness — recorded for replay, never a live call in tests. M5.3 maps these
raw caught/survived verdicts onto the §9.3 strength classes; M8 later confirms
the predictions by execution.

## Two calls, not one (#191)

It used to be one call carrying every obligation's every defect verdict. DR-180
localised this reviewer's instability to exactly that call: across two #167 runs
one commit apart, the mapped test set was byte-identical, the same defect was
named, and `would_be_caught` came back true and then false.

The pre-change baseline in `docs/experiments/191-discrimination-partition/`
measured the shape of it. One call covering 19 obligations returned exactly two
defects for each and judged all 38 caught, three runs running — the DR-164
signature of a schema-constrained call staying valid while shedding the work.
And the defect set itself did not repeat: 114 distinct (obligation, wording)
keys across three runs, each appearing exactly once. Pinning verdicts is not
enough when the set they range over is re-rolled every time.

So the stage is now two steps, keyed differently:

**Enumeration** asks what could plausibly go wrong, from the obligation text and
the changed code alone. It never sees a test. That is what makes "adding a test
leaves this obligation's defects unchanged" true *by construction* rather than
by hope: the request bytes are identical, so the transcript replays.

**Verdict** asks, per defect, whether the mapped tests would catch it. It sees
the criterion, the named defects, the mapped tests **and the changed code**.

The first cut of this change dropped the code from the verdict call, on the
reasoning that the enumerated defect already carried what the diff had to say,
and that partitioning would then be nearly free. That was wrong twice over. It
was never asked for — the mandate constrains what enumeration is determined by
and how the verdict is batched, and says nothing about taking an input away from
the judge — and it made the judgement worse: measured against the pre-change
baseline, evidence-class movement across resample runs went from 2 to 16.
Deciding whether a test fails under a defect is a question about the code the
test exercises, and it cannot be answered well from the defect sentence and the
assertion text alone.

So both calls carry the diff, and both are partitioned by obligation with their
own size control folded into the hashed request. Repeating the diff per batch is
the cost DR-164 decision 2 declined to pay on the diff-dominated stages; it is
paid here deliberately and pushed into the provider's prompt cache by putting
the invariant block first in every request (see `_render_verdict_prompt`). Two
size controls rather than one because the two calls still differ in what else
they carry, and because the right batch size for each is an open measurement
rather than a shared guess.

Enumeration covers **every** obligation, not only those with mapped tests. That
is deliberate and load-bearing: gating it on the mapping would put the mapping
back inside the enumeration request by the back door, since adding the first
test to one obligation would change which obligations are in the batch and so
change every other batch's bytes. Judging is still confined to obligations with
mapped evidence, exactly as before — criteria with no mapped test are
unsupported, and M5.3 classifies them.
"""

from __future__ import annotations

from acceptance.config import (
    DEFAULT_DEFECT_ENUMERATION_BATCH_SIZE,
    DEFAULT_DEFECT_VERDICT_BATCH_SIZE,
)
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.partition import partition
from acceptance.supplied_ids import UnusableAnswerLog, constrain, scan
from acceptance.model_base import PersistableModel
from acceptance.review_state import ChangeSet, Obligation, TestEvidence

_ENUMERATION_STAGE = "defect enumeration"
_VERDICT_STAGE = "defect verdict"

_ENUMERATION_SYSTEM_PROMPT = """\
You name the PLAUSIBLE defects that would violate a criterion.

A plausible defect is a realistic mistake a competent but fallible developer
might actually ship — not an arbitrary or absurd mutation, and not a violation
of some other criterion. State each one as what the code would do wrong, in one
sentence, specifically enough that someone could later decide whether a given
test would fail under it.

You are given the criteria and the changed production code. You are NOT given
the tests, and you must not speculate about them: this step is about what could
go wrong, not about whether anything would catch it. Do not mention tests,
coverage, or whether a defect would be detected.

Return, for each criterion id given, its list of defects. Use only the criterion
ids provided."""

_VERDICT_SYSTEM_PROMPT = """\
You judge whether a criterion's mapped tests would actually FAIL under a defect
that has already been named. A test evidences a criterion only if a realistic
defect would make it fail — not merely because it invokes the code or is named
for it.

For each defect id given, decide whether some mapped test would FAIL under that
defect (catch it). Reason about: do the test INPUTS distinguish the correct
behavior from the defect, or do they coincidentally produce the same result? Are
boundary / negative cases exercised? Do the ASSERTIONS target the required
result (e.g. does asserting a whole-number result exercise rounding)?

Set `would_be_caught` true only if some mapped test would genuinely fail under
the defect. A defect that produces the same output as the correct code for the
tested inputs is NOT caught (the input fails to discriminate).

Give a short `reason`. Answer for every defect id given, and for no other. Do
not add defects: the set is fixed and you are judging it, not extending it."""


class PlausibleDefect(PersistableModel):
    """A realistic violation of a criterion, and whether its tests catch it."""

    description: str
    would_be_caught: bool
    reason: str


class ObligationDiscrimination(PersistableModel):
    obligation_id: str
    defects: list[PlausibleDefect]
    # §9.3 bright line: do the mapped tests catch at least one plausible defect?
    discriminating: bool


class EnumeratedDefect(PersistableModel):
    """A named defect before anything has been asked about the tests.

    Carries an id rather than being matched back by its wording. The verdict
    call echoes the id, which is constrained to the ids that call supplied, so a
    reworded defect is a detectable unusable answer instead of a silently
    dropped judgment.
    """

    id: str
    obligation_id: str
    description: str


class _EnumeratedDefect(StrictResponseModel):
    description: str


class _ObligationDefects(StrictResponseModel):
    obligation_id: str
    defects: list[_EnumeratedDefect]


class _Enumeration(StrictResponseModel):
    obligations: list[_ObligationDefects]


class _DefectVerdict(StrictResponseModel):
    defect_id: str
    would_be_caught: bool
    reason: str


class _DefectVerdicts(StrictResponseModel):
    verdicts: list[_DefectVerdict]


def _evidence_by_obligation(
    obligations: list[Obligation], test_evidence: list[TestEvidence]
) -> dict[str, list[TestEvidence]]:
    by_obligation: dict[str, list[TestEvidence]] = {o.id: [] for o in obligations}
    for evidence in test_evidence:
        for obligation_id in evidence.mapped_obligations:
            if obligation_id in by_obligation:
                by_obligation[obligation_id].append(evidence)
    return by_obligation


def _render_criteria(obligations: list[Obligation]) -> list[str]:
    lines: list[str] = []
    for obligation in obligations:
        lines.append(f"### criterion id={obligation.id}: {obligation.description}")
        if obligation.observable_behavior:
            lines.append(f"observable behavior: {obligation.observable_behavior}")
        lines.append("")
    return lines


def _render_changed_code(change_set: ChangeSet) -> list[str]:
    lines = ["## Changed production code"]
    for file_change in change_set.files:
        if file_change.category != "source":
            continue
        lines.append(f"### {file_change.path}")
        for hunk in file_change.hunks:
            lines.append(hunk.content)
    return lines


def _render_enumeration_prompt(obligations: list[Obligation], change_set: ChangeSet) -> str:
    """Changed code first, criteria second — same reason as the verdict prompt.

    Enumeration repeats the diff once per batch too, so the invariant block
    belongs in the shared prefix here as well.
    """
    lines = _render_changed_code(change_set)
    lines.append("")
    lines.append("## Criteria")
    lines.append("")
    lines += _render_criteria(obligations)
    return "\n".join(lines)


_MAX_TEST_SOURCE_CHARS = 4000


def _render_verdict_prompt(
    obligations: list[Obligation],
    defects_by_obligation: dict[str, list[EnumeratedDefect]],
    evidence_by_obligation: dict[str, list[TestEvidence]],
    change_set: ChangeSet,
    test_sources: dict[str, str] | None = None,
) -> str:
    """The changed code FIRST, then this batch's criteria.

    Order is load-bearing, not cosmetic. The code block is identical across every
    verdict call in a run and the criteria block is not, so putting the invariant
    part first makes each call a longer prefix of the same string — which is what
    a provider's prompt cache keys on. Reversed, every call is a cache miss and
    the diff is paid for once per criterion.

    Each mapped test is given as its **source**, not only as the assertion
    strings the extractor pulled out of it. Those strings routinely cannot settle
    the question being asked. A defect of the form *"the cleanup runs against the
    current working directory rather than the repository under review"* is not
    decidable from `assert not stale.exists()` — whether that assertion
    discriminates depends on where `stale` points, which lives in the fixture
    setup. Asked to judge from evidence that cannot settle it, a model produces
    something plausible, and that is indistinguishable from instability.
    `DiscoveredTest.source` has carried this all along, for exactly this purpose
    — its docstring says so — and the stage simply never received it.
    """
    lines = _render_changed_code(change_set)
    lines.append("")
    lines.append("## Criteria, their plausible defects, and their mapped tests")
    lines.append("")
    for obligation in obligations:
        lines.append(f"### criterion id={obligation.id}: {obligation.description}")
        if obligation.observable_behavior:
            lines.append(f"observable behavior: {obligation.observable_behavior}")
        lines.append("plausible defects:")
        for defect in defects_by_obligation.get(obligation.id, []):
            lines.append(f"- defect id={defect.id}: {defect.description}")
        lines.append("mapped tests:")
        for evidence in evidence_by_obligation.get(obligation.id, []):
            lines.append(f"- {evidence.identifier}")
            if evidence.inputs:
                lines.append(f"    inputs: {'; '.join(evidence.inputs)}")
            if evidence.assertions:
                lines.append(f"    assertions: {'; '.join(evidence.assertions)}")
            if evidence.expected_value_provenance:
                lines.append(f"    expected-value provenance: {evidence.expected_value_provenance}")
            source = (test_sources or {}).get(evidence.identifier)
            if source:
                # Truncated at a fixed length rather than summarised: a summary
                # is another judgment to get wrong, and the bound has to be
                # deterministic or two runs build different requests.
                if len(source) > _MAX_TEST_SOURCE_CHARS:
                    source = source[:_MAX_TEST_SOURCE_CHARS] + "\n# ... truncated"
                lines.append("    source:")
                lines += [f"      {line}" for line in source.splitlines()]
        lines.append("")
    return "\n".join(lines)


def enumerate_defects(
    obligations: list[Obligation],
    change_set: ChangeSet,
    client: ModelClient,
    batch_size: int = DEFAULT_DEFECT_ENUMERATION_BATCH_SIZE,
    unusable: UnusableAnswerLog | None = None,
) -> list[EnumeratedDefect]:
    """Name the plausible defects for each criterion, from its text and the diff.

    The request carries no test evidence at all — see the module docstring. Two
    runs over the same obligations and the same changed code therefore build the
    same request bytes, which is what makes the enumeration replay rather than
    be re-rolled.
    """
    enumerated: list[EnumeratedDefect] = []
    for batch in partition(obligations, batch_size, key=lambda obligation: obligation.id):
        batch_obligations = list(batch.items)
        messages = [
            {"role": "system", "content": _ENUMERATION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _render_enumeration_prompt(batch_obligations, change_set),
            },
        ]
        allowed = {"obligation_id": [obligation.id for obligation in batch_obligations]}
        result = client.complete(
            messages,
            constrain(_Enumeration, allowed),
            batch.request_partition(),
            parse_as=_Enumeration,
            stage=_ENUMERATION_STAGE,
        )
        if unusable is not None:
            unusable.record(scan(result, allowed, _ENUMERATION_STAGE))

        batch_ids = set(allowed["obligation_id"])
        for item in result.obligations:
            if item.obligation_id not in batch_ids:
                # A batch may only speak for its own criteria, exactly as a
                # mapping batch may only speak for its own tests: without this a
                # model echoing a neighbouring batch's criterion would have its
                # defects merged in alongside the real ones, and the merged set
                # would depend on which batch answered last.
                continue
            enumerated.extend(defects_of(item))
    return enumerated


def defect_id(obligation_id: str, index: int) -> str:
    """The id a defect is judged under, from its criterion and its 1-based
    position in that criterion's enumerated list.

    Positional rather than content-derived on purpose: the verdict call echoes
    this id back, and an id derived from the wording would change whenever the
    wording did, which is the coupling the split exists to remove.
    """
    return f"{obligation_id}::d{index}"


def defects_of(item: _ObligationDefects) -> list[EnumeratedDefect]:
    """One criterion's enumerated defects, with their ids.

    Separate from `enumerate_defects` so anything reading the stage's responses
    back off the wire — the #189 instability harness does — mints the same ids
    from the same rule rather than reimplementing it.
    """
    return [
        EnumeratedDefect(
            id=defect_id(item.obligation_id, index),
            obligation_id=item.obligation_id,
            description=defect.description,
        )
        for index, defect in enumerate(item.defects, start=1)
    ]


def judge_defect_verdicts(
    obligations: list[Obligation],
    defects: list[EnumeratedDefect],
    test_evidence: list[TestEvidence],
    change_set: ChangeSet,
    client: ModelClient,
    batch_size: int = DEFAULT_DEFECT_VERDICT_BATCH_SIZE,
    unusable: UnusableAnswerLog | None = None,
    test_sources: dict[str, str] | None = None,
) -> list[ObligationDiscrimination]:
    """Decide, per already-named defect, whether the mapped tests would catch it.

    Criteria with no mapped test are not judged here — they are unsupported,
    classified by M5.3 — and neither are criteria for which nothing was
    enumerated.

    The changed code is part of this request and must stay that way. Deciding
    whether a test would fail under a defect is a question about the code the
    test exercises: what the assertion pins, whether the input reaches the
    changed branch, whether the defect would even alter the value asserted on.
    Asking it from the defect sentence and the assertion text alone is a
    strictly harder question, and #191's first cut did exactly that — it dropped
    the diff here so that partitioning would be cheap. Measured against the
    pre-change baseline, evidence-class movement across resample runs went from
    2 to 16. The saving is not worth it and the cost belongs in the prompt cache
    instead; see `_render_verdict_prompt` on why the code block comes first.
    """
    evidence_by_obligation = {
        oid: evidences
        for oid, evidences in _evidence_by_obligation(obligations, test_evidence).items()
        if evidences
    }
    if not evidence_by_obligation:
        return []

    defects_by_obligation: dict[str, list[EnumeratedDefect]] = {}
    for defect in defects:
        if defect.obligation_id in evidence_by_obligation:
            defects_by_obligation.setdefault(defect.obligation_id, []).append(defect)

    by_id = {o.id: o for o in obligations}
    judgeable = [
        by_id[oid]
        for oid in evidence_by_obligation
        if defects_by_obligation.get(oid) and oid in by_id
    ]

    verdicts: dict[str, _DefectVerdict] = {}
    for batch in partition(judgeable, batch_size, key=lambda obligation: obligation.id):
        batch_obligations = list(batch.items)
        batch_defects = [
            defect
            for obligation in batch_obligations
            for defect in defects_by_obligation[obligation.id]
        ]
        messages = [
            {"role": "system", "content": _VERDICT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _render_verdict_prompt(
                    batch_obligations,
                    defects_by_obligation,
                    evidence_by_obligation,
                    change_set,
                    test_sources,
                ),
            },
        ]
        allowed = {"defect_id": [defect.id for defect in batch_defects]}
        result = client.complete(
            messages,
            constrain(_DefectVerdicts, allowed),
            batch.request_partition(),
            parse_as=_DefectVerdicts,
            stage=_VERDICT_STAGE,
        )
        if unusable is not None and unusable.record(scan(result, allowed, _VERDICT_STAGE)):
            # A defect we asked about but got no usable judgment for is not "no
            # defect survives" — it is a judgment we never obtained. Saying
            # otherwise would let a re-run claim discrimination it never
            # assessed.
            answered = {verdict.defect_id for verdict in result.verdicts}
            unusable.mark_indeterminate(
                obligation.id
                for obligation in batch_obligations
                if any(defect.id not in answered for defect in defects_by_obligation[obligation.id])
            )

        allowed_ids = set(allowed["defect_id"])
        for verdict in result.verdicts:
            if verdict.defect_id in allowed_ids and verdict.defect_id not in verdicts:
                verdicts[verdict.defect_id] = verdict

    discriminations: list[ObligationDiscrimination] = []
    for obligation_id in evidence_by_obligation:
        judged = [
            PlausibleDefect(
                description=defect.description,
                would_be_caught=verdicts[defect.id].would_be_caught,
                reason=verdicts[defect.id].reason,
            )
            for defect in defects_by_obligation.get(obligation_id, [])
            if defect.id in verdicts
        ]
        discriminations.append(
            ObligationDiscrimination(
                obligation_id=obligation_id,
                defects=judged,
                discriminating=any(defect.would_be_caught for defect in judged),
            )
        )
    return discriminations


def judge_discrimination(
    obligations: list[Obligation],
    test_evidence: list[TestEvidence],
    change_set: ChangeSet,
    client: ModelClient,
    enumeration_batch_size: int = DEFAULT_DEFECT_ENUMERATION_BATCH_SIZE,
    verdict_batch_size: int = DEFAULT_DEFECT_VERDICT_BATCH_SIZE,
    unusable: UnusableAnswerLog | None = None,
    test_sources: dict[str, str] | None = None,
) -> list[ObligationDiscrimination]:
    """Judge, per criterion with mapped tests, whether those tests would fail
    under a plausible defect (§9.3), in two keyed steps.

    The stage boundary is here rather than in the pipeline so that the two calls
    cannot be wired up separately, or one of them skipped, by a caller that only
    wanted a discrimination result.

    Enumeration then covers every criterion, including those with no mapped test
    — see the module docstring on why gating it on the mapping would put the
    mapping back into the enumeration request. What is gated is the *stage*: with
    nothing mapped at all there is no verdict to reach, so no call is made, and
    enumerating defects no one would judge is work bought for nothing.
    """
    if not any(_evidence_by_obligation(obligations, test_evidence).values()):
        return []
    defects = enumerate_defects(obligations, change_set, client, enumeration_batch_size, unusable)
    return judge_defect_verdicts(
        obligations,
        defects,
        test_evidence,
        change_set,
        client,
        verdict_batch_size,
        unusable,
        test_sources,
    )
