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

from typing import NamedTuple

from acceptance.coverage.prompt import render_diff_section
from acceptance.evidence.discrimination import ObligationDiscrimination
from acceptance.llm import ModelClient, SchemaValidationError, StrictResponseModel
from acceptance.review_state import (
    AdmissibleEvidence,
    ChangeSet,
    Obligation,
    TestRecommendation,
    UnevidenceableObligation,
)
from acceptance.supplied_ids import UnusableAnswer, UnusableAnswerLog, constrain, scan

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

Some criteria cannot be evidenced by a test at all — a property of a build
step, a pinned dependency version, an action's major version, or the behavior
of a whole test run rather than of one test. For those, do NOT invent a
recommendation. Return the criterion in `unevidenceable` instead, with a
`reason` saying why no test is the right instrument for it. Prescribing a test
that cannot exist is worse than prescribing nothing.

Account for EVERY criterion you are given, in exactly one of the two lists —
`recommendations` if a test could close the gap, `unevidenceable` if none
could. Omitting a criterion from both is not an answer. If given no criteria,
return two empty lists."""


class _Recommendation(StrictResponseModel):
    obligation_id: str
    required_inputs: str
    boundary_conditions: str
    expected_output: str
    required_assertions: list[str]
    plausible_defect: str
    repo_conventions: str


class _Unevidenceable(StrictResponseModel):
    obligation_id: str
    reason: str


class _Recommendations(StrictResponseModel):
    recommendations: list[_Recommendation]
    # Required, not defaulted: strict mode has no optional field, and the prompt
    # asks for an explicit empty list rather than an omission. That is also the
    # point of the change — a criterion accounted for nowhere must stay
    # distinguishable from one the model deliberately declined.
    unevidenceable: list[_Unevidenceable]


def _weak_obligations(obligations: list[Obligation]) -> list[Obligation]:
    """Obligations with a real evidence gap — evidence_class set and below
    strongly_supported (the M7.1 trigger).

    Code-evidence-only obligations are excluded (#153). Theirs is not a gap a
    test could close: they are satisfied by the absence of excluded work, and no
    test can assert that work was not done. Recommending one would prescribe
    evidence that cannot exist, which is worse than recommending nothing —
    #146's review demanded a test for "we didn't also do something else".
    """
    return [
        obligation
        for obligation in obligations
        if obligation.admissible_evidence is not AdmissibleEvidence.CODE_ONLY
        and obligation.evidence_class is not None
        and obligation.evidence_class != _STRONG
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


class RecommendationOutcome(NamedTuple):
    """What the stage decided for the weak obligations, split by kind.

    Two lists rather than one, because they are different answers: a
    recommendation says a test would close the gap, a refusal says no test is
    the right instrument. Collapsing them would put the stage back where #266
    found it, unable to tell a correct refusal from a missing answer.
    """

    recommendations: list[TestRecommendation]
    unevidenceable: list[UnevidenceableObligation]


def recommend_tests(
    obligations: list[Obligation],
    discriminations: list[ObligationDiscrimination],
    change_set: ChangeSet,
    client: ModelClient,
    unusable: UnusableAnswerLog | None = None,
) -> RecommendationOutcome:
    """Prescribe a §9.5 test recommendation for each not-strongly-supported
    obligation, or record that no test can evidence it. No weak obligations ->
    no model call."""
    weak = _weak_obligations(obligations)
    if not weak:
        return RecommendationOutcome([], [])

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

    # Every weak obligation is accounted for, in exactly one of the two lists,
    # and only weak ones are. The "only" half was already enforced — `weak` is
    # what the call supplies, and a foreign id is unrepresentable under
    # constrained decoding. The "always" half was not: this loop used to iterate
    # the response and skip what it could not place, so a response answering 3
    # of 5 weak obligations produced a report where two carried no
    # recommendation and nothing distinguished it from a complete answer. That
    # is M1.2.r1's missing disposition, one stage downstream, and it is rejected
    # the same way.
    #
    # What #266 adds is the third state the check had no room for. Silence is
    # still rejected; a REFUSAL — "no test is the right instrument here" — is now
    # an answer, so a mandate whose obligations are properties of build steps or
    # version pins can be reviewed at all. The two must not collapse into each
    # other, which is why an obligation in both lists is an error rather than a
    # precedence rule: the response contradicted itself and neither answer can
    # be trusted over the other.
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

    declined: dict[str, _Unevidenceable] = {}
    for refusal in result.unevidenceable:
        if refusal.obligation_id in declined:
            raise SchemaValidationError(
                f"obligation '{refusal.obligation_id}' was declined more than once"
            )
        if refusal.obligation_id not in criterion_by_id:
            raise SchemaValidationError(
                f"refusal named obligation '{refusal.obligation_id}', which the call "
                "did not supply as weak"
            )
        declined[refusal.obligation_id] = refusal

    # Two ways a refusal can be present but unusable. Neither raises, and the
    # reason they do not is the whole of #266: this stage used to destroy a
    # review over one obligation it could not place, and an answer we cannot
    # honour is not a better excuse for that than an answer we never got. They
    # become `UnusableAnswer`s — the established shape for "we asked, and what
    # came back cannot be used" — which leaves the obligation `indeterminate`,
    # raises a major finding naming it, and lets the other 33 be reported.
    #
    # The asymmetry with an OMITTED obligation, which still raises, is
    # deliberate and is the issue's settled decision: silence is
    # indistinguishable from truncation or a shed batch, so it stays fatal.
    unusable_ids: dict[str, str] = {}
    for obligation_id in list(declined):
        if obligation_id in returned:
            # The response contradicted itself. Not resolved by precedence:
            # picking a side would report a judgement the model did not make.
            unusable_ids[obligation_id] = "was both recommended for and declined as unevidenceable"
        elif not declined[obligation_id].reason.strip():
            # A refusal is only better than silence because it is auditable, and
            # the reason is the whole of what makes it so. Required-ness in the
            # schema does not get here: "" is a valid str, so the structure can
            # be satisfied while the judgement is withheld.
            unusable_ids[obligation_id] = "was declined as unevidenceable with no reason given"

    for obligation_id in unusable_ids:
        declined.pop(obligation_id, None)
        returned.pop(obligation_id, None)
    if unusable_ids and unusable is not None:
        unusable.record(
            UnusableAnswer(
                stage=_STAGE, field="obligation_id", returned_id=obligation_id, reason=why
            )
            for obligation_id, why in sorted(unusable_ids.items())
        )
        unusable.mark_indeterminate(unusable_ids)

    # An obligation whose answer was unusable is NOT missing. It was answered —
    # badly, and it is already recorded as such, with the obligation left
    # indeterminate and a major finding naming it. Counting it here as well
    # would abort the review over an answer we have already reported on, which
    # is the double jeopardy that makes the omission guard look like the defect
    # it is not.
    missing = [
        obligation.id
        for obligation in weak
        if obligation.id not in returned
        and obligation.id not in declined
        and obligation.id not in unusable_ids
    ]
    if missing:
        raise SchemaValidationError(
            f"no recommendation and no refusal for {len(missing)} of {len(weak)} weak "
            f"obligation(s): {', '.join(missing)}"
        )

    return RecommendationOutcome(
        recommendations=[
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
            if obligation.id in returned
        ],
        unevidenceable=[
            UnevidenceableObligation(
                obligation_id=obligation.id,
                criterion=criterion_by_id[obligation.id],
                reason=declined[obligation.id].reason,
            )
            for obligation in weak
            if obligation.id in declined
        ],
    )
