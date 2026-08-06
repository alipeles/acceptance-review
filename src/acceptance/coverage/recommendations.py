"""Structured test recommendations (M7.1, §9.5).

For each criterion whose evidence is missing or weak — anything the §9.3
strength classifier (M5.3) rates below `strongly_supported` — prescribe the
test that would strengthen it, as machine-readable data a coding agent can
pick up and implement in a single iteration. "Add more tests" is insufficient
(§9.5, principle 9): every recommendation ties to a specific obligation, the
plausible defect it must detect, a discriminating setup, and required
assertions.

The plausible defect (§9.5 field 6) is not re-derived here — it is the
SURVIVING defect the M5.2 discrimination judge already named (the one the
current tests fail to catch). Reusing it keeps the recommendation pointed at
the exact weakness §8.2 found, so a green run of the added test demonstrably
closes the gap (§8.4) rather than nominally addressing it.

A semantic judgment (what test, with what inputs/assertions, catches this
defect), so a schema-constrained model call through the M0.4 harness —
recorded for replay, never a live call in tests. The product recommends; it
never modifies code (§9.5).
"""

from __future__ import annotations

from acceptance.coverage.prompt import render_diff_section
from acceptance.evidence.discrimination import ObligationDiscrimination
from acceptance.llm import ModelClient, SchemaValidationError, StrictResponseModel
from acceptance.supplied_ids import UnusableAnswerLog, constrain, scan
from acceptance.review_state import ChangeSet, Obligation, TestRecommendation

# §9.3 classes that represent a real evidence gap — anything short of
# strongly_supported earns a recommendation (the M7.1 trigger). An obligation
# with no evidence_class set yet (not classified) is not recommended for here.
_STRONG = "strongly_supported"

_STAGE = "test recommendation"

_SYSTEM_PROMPT = """\
You prescribe ADDITIONAL TESTS for criteria whose current test evidence is
missing or weak. For each criterion you are given the plausible DEFECT that its
current tests fail to catch — the test you prescribe must catch exactly that
defect.

"Add more tests" is not acceptable. For each criterion return a structured
recommendation with these discrete fields:
- required_inputs: the input characteristics the test must use — chosen so a
  CORRECT and an INCORRECT (defective) implementation produce DIFFERENT
  results. This is the crux: inputs where the defect changes the outcome.
- boundary_conditions: the boundary or negative conditions to cover (empty,
  zero, max, the error path), if any.
- expected_output: the expected output or relationship the test asserts.
- required_assertions: the specific assertions the test must make (a list).
- plausible_defect: restate the defect this test is designed to detect — the
  test must fail if that defect is present.
- repo_conventions: relevant conventions or fixtures from the diff to follow
  (test file, naming, existing fixtures) so the added test fits the repo.

Return one recommendation per criterion you are given, keyed by its
`obligation_id`. If given no criteria, return an empty list."""


class _Recommendation(StrictResponseModel):
    obligation_id: str
    required_inputs: str
    boundary_conditions: str
    expected_output: str
    required_assertions: list[str]
    plausible_defect: str
    repo_conventions: str


class _Recommendations(StrictResponseModel):
    recommendations: list[_Recommendation]


def _weak_obligations(obligations: list[Obligation]) -> list[Obligation]:
    """Obligations with a real evidence gap — evidence_class set and below
    strongly_supported (the M7.1 trigger)."""
    return [
        obligation
        for obligation in obligations
        if obligation.evidence_class is not None and obligation.evidence_class != _STRONG
    ]


def _surviving_defects(discrimination: ObligationDiscrimination | None) -> list[str]:
    if discrimination is None:
        return []
    return [d.description for d in discrimination.defects if not d.would_be_caught]


def _render_prompt(
    weak: list[Obligation],
    discriminations_by_obligation: dict[str, ObligationDiscrimination],
    change_set: ChangeSet,
) -> str:
    lines = ["## Criteria needing stronger test evidence", ""]
    for obligation in weak:
        lines.append(f"### id={obligation.id}")
        lines.append(f"criterion: {obligation.observable_behavior or obligation.description}")
        lines.append(f"evidence class: {obligation.evidence_class}")
        defects = _surviving_defects(discriminations_by_obligation.get(obligation.id))
        if defects:
            lines.append("plausible defects the current tests do NOT catch:")
            lines.extend(f"  - {d}" for d in defects)
        lines.append("")
    lines.extend(render_diff_section(change_set))
    return "\n".join(lines)


def recommend_tests(
    obligations: list[Obligation],
    discriminations: list[ObligationDiscrimination],
    change_set: ChangeSet,
    client: ModelClient,
    unusable: UnusableAnswerLog | None = None,
) -> list[TestRecommendation]:
    """Prescribe a §9.5 test recommendation for each not-strongly-supported
    obligation. No weak obligations -> no model call."""
    weak = _weak_obligations(obligations)
    if not weak:
        return []

    discriminations_by_obligation = {d.obligation_id: d for d in discriminations}
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": _render_prompt(weak, discriminations_by_obligation, change_set),
        },
    ]
    # Only the WEAK obligations are supplied — those are the ones the call is
    # about, so a recommendation for any other obligation is unusable by
    # construction, not merely unmatched.
    allowed = {"obligation_id": [obligation.id for obligation in weak]}
    result = client.complete(
        messages, constrain(_Recommendations, allowed), parse_as=_Recommendations
    )
    if unusable is not None:
        unusable.record(scan(result, allowed, _STAGE))

    criterion_by_id = {
        obligation.id: (obligation.observable_behavior or obligation.description)
        for obligation in weak
    }

    # A recommendation exists for a weak obligation, and only for a weak one.
    # The "only" half was already enforced — `weak` is what the call supplies,
    # and a foreign id is unrepresentable under constrained decoding. The
    # "always" half was not: this loop used to iterate the response and skip
    # what it could not place, so a response answering 3 of 5 weak obligations
    # produced a report where two carried no recommendation and nothing
    # distinguished it from a complete answer. That is M1.2.r1's missing
    # disposition, one stage downstream, and it is rejected the same way.
    returned: dict[str, _Recommendation] = {}
    for rec in result.recommendations:
        if rec.obligation_id in returned:
            raise SchemaValidationError(
                f"obligation '{rec.obligation_id}' was recommended for more than once"
            )
        if rec.obligation_id not in criterion_by_id:
            raise SchemaValidationError(
                f"recommendation named obligation '{rec.obligation_id}', which the call "
                "did not supply as weak"
            )
        returned[rec.obligation_id] = rec

    missing = [obligation.id for obligation in weak if obligation.id not in returned]
    if missing:
        raise SchemaValidationError(
            f"no recommendation for {len(missing)} of {len(weak)} weak "
            f"obligation(s): {', '.join(missing)}"
        )

    return [
        TestRecommendation(
            obligation_id=obligation.id,
            criterion=criterion_by_id[obligation.id],
            required_inputs=returned[obligation.id].required_inputs,
            boundary_conditions=returned[obligation.id].boundary_conditions,
            expected_output=returned[obligation.id].expected_output,
            required_assertions=returned[obligation.id].required_assertions,
            plausible_defect=returned[obligation.id].plausible_defect,
            repo_conventions=returned[obligation.id].repo_conventions,
        )
        for obligation in weak
    ]
