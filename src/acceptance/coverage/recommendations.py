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
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.review_state import ChangeSet, Obligation, TestRecommendation

# §9.3 classes that represent a real evidence gap — anything short of
# strongly_supported earns a recommendation (the M7.1 trigger). An obligation
# with no evidence_class set yet (not classified) is not recommended for here.
_STRONG = "strongly_supported"

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
    result = client.complete(messages, _Recommendations)

    criterion_by_id = {
        obligation.id: (obligation.observable_behavior or obligation.description)
        for obligation in weak
    }
    recommendations = []
    for rec in result.recommendations:
        criterion = criterion_by_id.get(rec.obligation_id)
        if criterion is None:
            continue  # model named an obligation that isn't weak / doesn't exist
        recommendations.append(
            TestRecommendation(
                obligation_id=rec.obligation_id,
                criterion=criterion,
                required_inputs=rec.required_inputs,
                boundary_conditions=rec.boundary_conditions,
                expected_output=rec.expected_output,
                required_assertions=rec.required_assertions,
                plausible_defect=rec.plausible_defect,
                repo_conventions=rec.repo_conventions,
            )
        )
    return recommendations
