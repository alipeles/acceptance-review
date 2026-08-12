"""Test-evidence strength classification (M5.3, §9.3).

Maps M5.2's per-criterion discrimination verdicts onto the §9.3 evidence
classes. This is a deterministic reduce, not a fresh judgment: M5.2 already did
the hard semantic work (which plausible defects each mapped test would catch);
M5.3 turns that into a class over the single bright line "catches at least one
plausible violation":

    all named defects caught     -> strongly_supported
    some (>=1) but not all       -> partially_supported
    a mapped test, none caught   -> nominally_supported
    no mapped test at all        -> unsupported
    mapped test, no defect judged -> indeterminate

`requires_other_evidence` is NOT produced here — the discrimination verdicts
carry no signal that a criterion needs non-code evidence (docs, visual, deploy);
that routing is left to coverage's `requires_non_code_evidence` status
downstream (M5.5/M7), not invented from test discrimination.

Each classification links to the exact mapped tests (their pytest nodeids) and
explains itself — for a nominal test that bypasses the behavior via a mock, the
mock is cited (from M5.1's extracted `TestEvidence.mocks`), per §9.4.

Classification is at the `static` evidence tier: these are static predictions;
M8 execution can later confirm them and raise the tier. `apply_evidence_strength`
(M5.5) writes each obligation's class into `Obligation.evidence_class` — the
field the §11.1 evidence-classification-agreement metric (scoring.py) reads.
"""

from __future__ import annotations

from pydantic import Field

from acceptance.evidence.discrimination import ObligationDiscrimination
from acceptance.evidence_tier import EvidenceTier
from acceptance.model_base import PersistableModel
from acceptance.review_state import EvidenceClassification, Obligation, TestEvidence


class EvidenceStrength(PersistableModel):
    """One criterion's §9.3 strength class, with a linked, self-justifying
    explanation (M5.3)."""

    obligation_id: str
    evidence_class: EvidenceClassification
    explanation: str
    # pytest nodeids of the mapped tests
    test_links: list[str] = Field(default_factory=list)


def _evidence_by_obligation(
    obligations: list[Obligation], test_evidence: list[TestEvidence]
) -> dict[str, list[TestEvidence]]:
    by_obligation: dict[str, list[TestEvidence]] = {o.id: [] for o in obligations}
    for evidence in test_evidence:
        for obligation_id in evidence.mapped_obligations:
            if obligation_id in by_obligation:
                by_obligation[obligation_id].append(evidence)
    return by_obligation


def _defect_list(descriptions: list[str]) -> str:
    return "; ".join(descriptions) if descriptions else "(none)"


def _mock_note(tests: list[TestEvidence]) -> str:
    mocks = sorted({mock for ev in tests for mock in ev.mocks})
    if not mocks:
        return ""
    return f" The mapped test mocks {', '.join(mocks)}, bypassing the behavior under review."


def _explain(
    evidence_class: EvidenceClassification,
    discrimination: ObligationDiscrimination,
    tests: list[TestEvidence],
) -> str:
    caught = [d.description for d in discrimination.defects if d.would_be_caught]
    survived = [d.description for d in discrimination.defects if not d.would_be_caught]
    if evidence_class == "strongly_supported":
        return f"The mapped test would fail under every plausible defect considered: {_defect_list(caught)}."
    if evidence_class == "partially_supported":
        return (
            f"The mapped test catches some plausible defects ({_defect_list(caught)}) "
            f"but not others ({_defect_list(survived)})."
        )
    # nominally_supported
    return (
        f"A present, relevant test that catches no plausible defect; these survive it: "
        f"{_defect_list(survived)}.{_mock_note(tests)}"
    )


def classify_strength(
    obligations: list[Obligation],
    test_evidence: list[TestEvidence],
    discriminations: list[ObligationDiscrimination],
) -> list[EvidenceStrength]:
    """Classify each obligation's §9.3 evidence strength from M5.1 extraction and
    M5.2 discrimination."""
    evidence_by_obligation = _evidence_by_obligation(obligations, test_evidence)
    discrimination_by_obligation = {d.obligation_id: d for d in discriminations}

    results: list[EvidenceStrength] = []
    for obligation in obligations:
        tests = evidence_by_obligation.get(obligation.id, [])
        links = sorted({ev.identifier for ev in tests})

        if not tests:
            results.append(
                EvidenceStrength(
                    obligation_id=obligation.id,
                    evidence_class="unsupported",
                    explanation="No mapped test evidences this criterion.",
                    test_links=[],
                )
            )
            continue

        discrimination = discrimination_by_obligation.get(obligation.id)
        if discrimination is None or not discrimination.defects:
            results.append(
                EvidenceStrength(
                    obligation_id=obligation.id,
                    evidence_class="indeterminate",
                    explanation=(
                        "A mapped test exists but no plausible defect was judged against it, "
                        "so its discriminating power cannot be decided statically."
                    ),
                    test_links=links,
                )
            )
            continue

        caught = sum(1 for d in discrimination.defects if d.would_be_caught)
        total = len(discrimination.defects)
        if caught == total:
            evidence_class: EvidenceClassification = "strongly_supported"
        elif caught:
            evidence_class = "partially_supported"
        else:
            evidence_class = "nominally_supported"

        results.append(
            EvidenceStrength(
                obligation_id=obligation.id,
                evidence_class=evidence_class,
                explanation=_explain(evidence_class, discrimination, tests),
                test_links=links,
            )
        )
    return results


def apply_evidence_strength(
    obligations: list[Obligation], results: list[EvidenceStrength]
) -> list[Obligation]:
    """Return copies of `obligations` with `evidence_class` (and the `static`
    achieved tier) set from the classification — the join the §11.1
    evidence-classification-agreement metric scores (M5.5)."""
    by_id = {r.obligation_id: r for r in results}
    updated = []
    for obligation in obligations:
        result = by_id.get(obligation.id)
        if result is None:
            updated.append(obligation)
            continue
        updated.append(
            obligation.model_copy(
                update={
                    "evidence_class": result.evidence_class,
                    "achieved_evidence_tier": EvidenceTier.STATIC,
                }
            )
        )
    return updated
