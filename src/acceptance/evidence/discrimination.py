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
"""

from __future__ import annotations

from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.model_base import PersistableModel
from acceptance.review_state import ChangeSet, Obligation, TestEvidence
from acceptance.supplied_ids import UnusableAnswerLog, constrain, scan

_STAGE = "discrimination judgment"

_SYSTEM_PROMPT = """\
You judge whether a criterion's mapped tests would actually FAIL if the
implementation violated that criterion in a PLAUSIBLE way. A test evidences a
criterion only if a realistic defect would make it fail — not merely because it
invokes the code or is named for it.

For each criterion (obligation):
1. Name one or more PLAUSIBLE defects: realistic mistakes a competent but
   fallible developer might actually ship that violate THIS criterion
   specifically — not arbitrary or absurd mutations.
2. For each defect decide whether the mapped test(s) would FAIL under it
   (catch it). Reason about: do the test INPUTS distinguish the correct
   behavior from the defect, or do they coincidentally produce the same result?
   Are boundary / negative cases exercised? Do the ASSERTIONS target the
   required result (e.g. does asserting a whole-number result exercise
   rounding)?
3. Give a short `reason`.

Set `would_be_caught` true only if some mapped test would genuinely fail under
the defect. A defect that produces the same output as the correct code for the
tested inputs is NOT caught (the input fails to discriminate).

Return, for each obligation id given, its list of defects with verdicts. Use
only the obligation ids provided."""


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


class _Defect(StrictResponseModel):
    description: str
    would_be_caught: bool
    reason: str


class _ObligationDiscrimination(StrictResponseModel):
    obligation_id: str
    defects: list[_Defect]


class _Discrimination(StrictResponseModel):
    obligations: list[_ObligationDiscrimination]


def _evidence_by_obligation(
    obligations: list[Obligation], test_evidence: list[TestEvidence]
) -> dict[str, list[TestEvidence]]:
    by_obligation: dict[str, list[TestEvidence]] = {o.id: [] for o in obligations}
    for evidence in test_evidence:
        for obligation_id in evidence.mapped_obligations:
            if obligation_id in by_obligation:
                by_obligation[obligation_id].append(evidence)
    return by_obligation


def _render_prompt(
    obligations: list[Obligation],
    evidence_by_obligation: dict[str, list[TestEvidence]],
    change_set: ChangeSet,
) -> str:
    by_id = {o.id: o for o in obligations}
    lines = ["## Criteria and their mapped tests", ""]
    for obligation_id, evidences in evidence_by_obligation.items():
        obligation = by_id[obligation_id]
        lines.append(f"### criterion id={obligation.id}: {obligation.description}")
        if obligation.observable_behavior:
            lines.append(f"observable behavior: {obligation.observable_behavior}")
        lines.append("mapped tests:")
        for evidence in evidences:
            lines.append(f"- {evidence.identifier}")
            if evidence.inputs:
                lines.append(f"    inputs: {'; '.join(evidence.inputs)}")
            if evidence.assertions:
                lines.append(f"    assertions: {'; '.join(evidence.assertions)}")
            if evidence.expected_value_provenance:
                lines.append(f"    expected-value provenance: {evidence.expected_value_provenance}")
        lines.append("")

    lines.append("## Changed production code")
    for file_change in change_set.files:
        if file_change.category != "source":
            continue
        lines.append(f"### {file_change.path}")
        for hunk in file_change.hunks:
            lines.append(hunk.content)
    return "\n".join(lines)


def judge_discrimination(
    obligations: list[Obligation],
    test_evidence: list[TestEvidence],
    change_set: ChangeSet,
    client: ModelClient,
    unusable: UnusableAnswerLog | None = None,
) -> list[ObligationDiscrimination]:
    """Judge, per criterion with mapped tests, whether those tests would fail
    under a plausible defect (§9.3). Criteria with no mapped test are not
    judged here — they are unsupported, classified by M5.3."""
    evidence_by_obligation = {
        oid: evidences
        for oid, evidences in _evidence_by_obligation(obligations, test_evidence).items()
        if evidences
    }
    if not evidence_by_obligation:
        return []

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": _render_prompt(obligations, evidence_by_obligation, change_set),
        },
    ]
    allowed = {"obligation_id": list(evidence_by_obligation)}
    result = client.complete(
        messages, constrain(_Discrimination, allowed), parse_as=_Discrimination, stage=_STAGE
    )
    if unusable is not None and unusable.record(scan(result, allowed, _STAGE)):
        # An obligation we asked about but got no usable judgment for is not
        # "no defect survives" — it is a judgment we never obtained. Saying
        # otherwise would let a re-run claim discrimination it never assessed.
        unusable.mark_indeterminate(
            obligation_id
            for obligation_id in evidence_by_obligation
            if obligation_id not in {item.obligation_id for item in result.obligations}
        )

    returned = {
        item.obligation_id: item.defects
        for item in result.obligations
        if item.obligation_id in evidence_by_obligation
    }

    discriminations: list[ObligationDiscrimination] = []
    for obligation_id in evidence_by_obligation:
        raw_defects = returned.get(obligation_id, [])
        defects = [
            PlausibleDefect(
                description=d.description, would_be_caught=d.would_be_caught, reason=d.reason
            )
            for d in raw_defects
        ]
        discriminations.append(
            ObligationDiscrimination(
                obligation_id=obligation_id,
                defects=defects,
                discriminating=any(d.would_be_caught for d in defects),
            )
        )
    return discriminations
