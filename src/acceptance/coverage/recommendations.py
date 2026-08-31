"""Structured test recommendations (M7.1, §9.5).

**A recommendation is an uncovered defect** (DR-312 decision 4, #316). The unit
is one `Defect` record that no candidate test was judged to fail on, and the
§9.5 payload is composed around it. What this stage still asks a model for is
the prescription — inputs, boundaries, assertions — because *what test catches
this defect* is a semantic judgement. What it no longer asks for is which
criterion is weak, or what the defect is: both are already recorded, typed and
linked, and re-deriving them was where a prescription could come loose from its
evidence.

Two named failures stop being possible rather than becoming things to check for:

- **#250 and #287 — prescribing a test that already exists.** The input is
  `defects.support.uncovered_defects`, which never yields a defect some verdict
  says a test would fail on. A redundant prescription has nothing to be composed
  from.
- **#283 — a prescription resting on nothing traceable.** `TestRecommendation`
  requires `defect_id`, and the `Defect` it names carries the `obligation_id`
  and the `code_refs` that reach the criterion's text and the exact lines
  (§13.6). A recommendation citing no way of failing does not typecheck.

`plausible_defect` (§9.5 field 6) is copied from the defect record rather than
restated by the model. Copying is what keeps the prescription pointed at the
exact enumerated weakness, so a green run of the added test demonstrably closes
that gap (§8.4); asking for a restatement bought a paraphrase that could drift
from the record it was supposed to name, and cost output on every prescription.

The product recommends; it never modifies code (§9.5).
"""

from __future__ import annotations

from pydantic import Field

from acceptance.concurrency import map_calls
from acceptance.coverage.prompt import diff_block
from acceptance.defects.support import uncovered_defects
from acceptance.llm import ModelClient, SchemaValidationError, StrictResponseModel
from acceptance.model_base import PersistableModel
from acceptance.partition import partition
from acceptance.request_blocks import Block, BlockKind, assemble
from acceptance.review_state import (
    ChangeSet,
    Defect,
    DefectSet,
    Obligation,
    PairVerdict,
    TestRecommendation,
    UnobtainedRecommendation,
)
from acceptance.supplied_ids import UnusableAnswer, UnusableAnswerLog, constrain, scan

_STAGE = "test recommendation"

# Uncovered defects per call. Held well under DR-164's shedding limit because a
# prescription's response is large — six fields of prose each — and it is output
# that never amortizes under the input-only caching discount. The old stage sent
# one call for the whole review; that was safe when the unit was a weak
# criterion and is not when it is a defect, since #314's Gate 2 enumerated 75 of
# them for one review.
DEFAULT_RECOMMENDATION_BATCH_SIZE = 10

_SYSTEM_PROMPT = """\
You prescribe ADDITIONAL TESTS. Each item you are given is one DEFECT — a
concrete way the delivered code could fail a criterion — that no existing test
was judged to catch. Prescribe the test that would catch exactly that defect.

"Add more tests" is not acceptable. For each defect return a structured
recommendation with these discrete fields:
- required_inputs: the input characteristics the test must use — chosen so a
  CORRECT and an INCORRECT (defective) implementation produce DIFFERENT
  results. This is the crux: inputs where the defect changes the outcome.
- boundary_conditions: the boundary or negative conditions to cover (empty,
  zero, max, the error path), if any.
- expected_output: the expected output or relationship the test asserts.
- required_assertions: the specific assertions the test must make (a list).
- repo_conventions: relevant conventions or fixtures from the diff to follow
  (test file, naming, existing fixtures) so the added test fits the repo.

Do not restate the defect; it is already recorded and will be attached to your
answer. Every defect you are given needs a test — that was settled before this
call and is not yours to revisit. Return one recommendation per defect, keyed by
its `defect_id`. If given no defects, return an empty list."""


class RecommendationResult(PersistableModel):
    """What the stage prescribed, and what it was asked for and did not get.

    Two lists rather than one, for the reason `MappingResult` keeps `unmapped`
    and `indeterminate` apart: a prescription is a substantive answer, and an
    omission is the absence of one. Collapsing them is what makes a partial
    response read as a complete one."""

    recommendations: list[TestRecommendation] = Field(default_factory=list)
    unobtained: list[UnobtainedRecommendation] = Field(default_factory=list)


class _Recommendation(StrictResponseModel):
    defect_id: str
    required_inputs: str
    boundary_conditions: str
    expected_output: str
    required_assertions: list[str]
    repo_conventions: str


class _Recommendations(StrictResponseModel):
    recommendations: list[_Recommendation]


def _subject_block(defects: tuple[Defect, ...], criterion_by_obligation: dict[str, str]) -> Block:
    """The uncovered defects this call must prescribe for.

    Grouped under their criterion so the criterion text is written once per
    group rather than once per defect — several defects of one criterion in one
    batch is the common case, since `uncovered_defects` walks defect sets in
    order.
    """
    lines = ["## Uncovered defects needing a test", ""]
    current: str | None = None
    for defect in defects:
        if defect.obligation_id != current:
            current = defect.obligation_id
            lines.append(f"### criterion {current}")
            lines.append(criterion_by_obligation.get(current, ""))
            lines.append("")
        lines.append(f"- defect_id={defect.id}")
        lines.append(f"  {defect.description}")
        if defect.code_refs:
            lines.append(f"  implicated code: {', '.join(defect.code_refs)}")
    return Block(BlockKind.SUBJECT, "\n".join(lines).rstrip())


def recommend_tests(
    obligations: list[Obligation],
    defect_sets: list[DefectSet],
    verdicts: list[PairVerdict],
    change_set: ChangeSet,
    client: ModelClient,
    unusable: UnusableAnswerLog | None = None,
    batch_size: int = DEFAULT_RECOMMENDATION_BATCH_SIZE,
) -> RecommendationResult:
    """Prescribe a §9.5 test for every enumerated defect no test would fail on.

    No uncovered defects -> no model call, which is the shape a fully covered
    review takes and the reason a clean run costs nothing here.
    """
    defects_by_id = {
        defect.id: defect for defect_set in defect_sets for defect in defect_set.defects
    }
    # Obligations that do not require test evidence never reach here (#266), and
    # the guard is kept rather than trusted: prescribing a test for a criterion
    # no test is owed for demands evidence that cannot exist, which is worse than
    # prescribing nothing (#146's review asked for a test proving "we didn't also
    # do something else"). The question has one answer and was settled at
    # decomposition; this only declines to act against it.
    owed = {o.id for o in obligations if o.required_evidence.requires_tests}
    criterion_by_obligation = {o.id: (o.observable_behavior or o.description) for o in obligations}

    pending = [
        defects_by_id[defect_id]
        for obligation_id, defect_id in uncovered_defects(defect_sets, verdicts)
        if obligation_id in owed and defect_id in defects_by_id
    ]
    if not pending:
        return RecommendationResult()

    # Batches are issued CONCURRENTLY and consumed in batch order. Each batch
    # prescribes for its own defects and reads no other batch's answer.
    batches = partition(pending, batch_size, key=lambda defect: defect.id)
    answers = map_calls(
        batches, lambda batch: _ask(batch, criterion_by_obligation, change_set, client)
    )

    recommendations: list[TestRecommendation] = []
    missing: list[Defect] = []
    for batch, (returned, scanned) in zip(batches, answers):
        # Recorded here rather than inside the call, so the log reads in batch
        # order however the calls finished (`concurrency.py`, rule 2).
        if unusable is not None:
            unusable.record(scanned)
        for defect in batch.items:
            answer = returned.get(defect.id)
            if answer is None:
                missing.append(defect)
                continue
            recommendations.append(
                TestRecommendation(
                    obligation_id=defect.obligation_id,
                    defect_id=defect.id,
                    criterion=criterion_by_obligation.get(defect.obligation_id, ""),
                    required_inputs=answer.required_inputs,
                    boundary_conditions=answer.boundary_conditions,
                    expected_output=answer.expected_output,
                    required_assertions=answer.required_assertions,
                    # From the record, not the response. See the module docstring.
                    plausible_defect=defect.description,
                    repo_conventions=answer.repo_conventions,
                )
            )

    if missing and unusable is not None:
        # The evidence axis is where this has to land. `indeterminate` says "we
        # did not obtain this judgment", `pipeline._apply_indeterminate` writes
        # it onto the obligation, and `verdict.py` routes it to
        # `unable_to_determine` and lists it as an escalation candidate — so a
        # review missing a prescription cannot come back clean.
        unusable.mark_indeterminate(sorted({defect.obligation_id for defect in missing}))

    return RecommendationResult(
        recommendations=recommendations,
        unobtained=[
            UnobtainedRecommendation(
                obligation_id=defect.obligation_id,
                defect_id=defect.id,
                criterion=criterion_by_obligation.get(defect.obligation_id, ""),
                reason=(
                    f"the recommendation stage was given {len(pending)} uncovered defect(s) "
                    f"and returned {len(recommendations)}; no prescription was produced for "
                    "this one"
                ),
            )
            for defect in missing
        ],
    )


def _ask(
    batch,
    criterion_by_obligation: dict[str, str],
    change_set: ChangeSet,
    client: ModelClient,
) -> tuple[dict[str, _Recommendation], list[UnusableAnswer]]:
    """One batch's prescriptions keyed by defect id, and the ids it invented.

    **Records nothing** — see `concurrency.py`, rule 2.

    #275: an omission is an INDETERMINATE result about the defect it concerns,
    not grounds for abandoning the review — rejecting it by raising discarded
    every honoured prescription, the verdict, and every finding the earlier
    stages had produced, to report that one was missing. The duplicate and
    foreign id cases below still raise: those are answers we cannot place at
    all, not answers we did not receive.
    """
    messages = assemble(
        [
            diff_block(change_set),
            Block(BlockKind.INSTRUCTIONS, _SYSTEM_PROMPT),
            _subject_block(batch.items, criterion_by_obligation),
        ]
    )
    allowed = {"defect_id": [defect.id for defect in batch.items]}
    result = client.complete(
        messages,
        constrain(_Recommendations, allowed),
        parse_as=_Recommendations,
        stage=_STAGE,
        partition=batch.request_partition(),
    )
    offered = {defect.id for defect in batch.items}
    returned: dict[str, _Recommendation] = {}
    for rec in result.recommendations:
        if rec.defect_id in returned:
            raise SchemaValidationError(
                f"defect '{rec.defect_id}' was recommended for more than once"
            )
        if rec.defect_id not in offered:
            raise SchemaValidationError(
                f"recommendation named defect '{rec.defect_id}', which the call did not supply"
            )
        returned[rec.defect_id] = rec
    return returned, scan(result, allowed, _STAGE)
