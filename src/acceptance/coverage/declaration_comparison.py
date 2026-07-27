"""Declaration-vs-evidence comparison (M6.2, §7.4, issue #31).

Compares a builder declaration's claims — mandate as understood, implementation,
tests, scope exclusions, assumptions, limitations, behavioral changes — against
what the review actually found: the obligations (M1), the diff (M2), and the
test evidence (M5). A claim matching neither the task nor the code/tests is a
`declaration_mismatch` finding.

Two situations are deliberately kept apart (issue #31 design note):

- A claim of work that was **actually done** (real code changed outside the
  mandate) is an `unrequested_change` (M3.2), not our concern — it weighs on
  acceptance because real scope expanded. We must NOT re-flag it here.
- A claim of work that was **claimed but not done** (no code path, no test) is
  the `declaration_mismatch` this capability produces. It is **advisory /
  low-weight**: nothing was actually mis-delivered in the code, so a bogus
  claim flags the declaration as untrustworthy without blocking acceptance of
  the real change. Archetype #7's shape: the declaration claims `get_user`
  raises `KeyError` on a missing id, but the code returns `None` and no test
  exercises the missing-id path.

A semantic judgment, so a schema-constrained model call through the M0.4
harness — recorded for replay, never a live call in tests. Findings are a
claim, not proof (§7.4): they carry the BUILDER_CLAIM tier, the weakest rung
of the ladder.
"""

from __future__ import annotations

from acceptance.coverage.prompt import render_diff_section
from acceptance.evidence_tier import Component, EvidenceTier
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.model_base import PersistableModel
from acceptance.review_state import (
    DECLARATION_MISMATCH,
    BuilderDeclaration,
    ChangeSet,
    Finding,
    Link,
    Obligation,
    TestEvidence,
)

_SYSTEM_PROMPT = """\
You compare a BUILDER DECLARATION against what a review actually found. The
declaration is the builder's own end-of-cycle account of what they believe was
requested and completed — a CLAIM, not proof. You are given the obligations the
task actually required, the diff that was actually made, and the tests that
actually exist.

Find declaration claims that match NEITHER the task NOR the code/tests — most
importantly, a claim of BEHAVIOR OR WORK THAT WAS NOT ACTUALLY DONE: the
declaration asserts the code does something (handles an error, enforces a
limit, covers a case) that no diff hunk implements and no test exercises.

For each such claim return the `claim` (what the declaration asserts, quoted or
closely paraphrased) and a short `rationale` (why it is unsupported — what the
code actually does instead, and that no test covers it).

Do NOT report:
- A claim that the obligations, diff, or tests DO support — a truthful claim is
  not a discrepancy.
- A claim of work that WAS actually done but wasn't requested. Real
  unrequested code is handled by a separate analysis; only report claims with
  NO backing code and NO backing test.
- Vague or stylistic wording differences. Report a claim only when the code and
  tests genuinely fail to support a concrete asserted behavior.

If every claim is supported, return an empty list."""


class DeclarationMismatch(PersistableModel):
    """A declaration claim matching neither the task nor the code/tests."""

    claim: str
    rationale: str


class _Mismatch(StrictResponseModel):
    claim: str
    rationale: str


class _Mismatches(StrictResponseModel):
    mismatches: list[_Mismatch]


def _render_prompt(
    declaration: BuilderDeclaration,
    obligations: list[Obligation],
    change_set: ChangeSet,
    test_evidence: list[TestEvidence],
) -> str:
    lines = ["## Builder declaration", ""]
    for label, value in _declaration_sections(declaration):
        if value:
            lines.append(f"### {label}")
            lines.append(value)
            lines.append("")

    lines.append("## Obligations the task actually required")
    if obligations:
        for obligation in obligations:
            lines.append(f"- {obligation.description}")
    else:
        lines.append("(none)")
    lines.append("")

    lines.extend(render_diff_section(change_set))
    lines.append("")

    lines.append("## Tests that actually exist")
    if test_evidence:
        for evidence in test_evidence:
            assertions = "; ".join(evidence.assertions) or "(no assertions parsed)"
            lines.append(f"- {evidence.identifier}: {assertions}")
    else:
        lines.append("(none)")
    return "\n".join(lines)


def _declaration_sections(declaration: BuilderDeclaration) -> list[tuple[str, str]]:
    return [
        ("Mandate as understood", declaration.mandate_as_understood),
        ("Implementation summary", declaration.implementation_summary),
        ("Scope exclusions", declaration.scope_exclusions),
        ("Assumptions", declaration.assumptions),
        ("Changed components", declaration.changed_components),
        ("Test evidence", declaration.test_evidence),
        ("Regression evidence", declaration.regression_evidence),
        ("Known limitations", declaration.known_limitations),
        ("Additional behavioral changes", declaration.additional_behavioral_changes),
    ]


def compare_declaration(
    declaration: BuilderDeclaration,
    obligations: list[Obligation],
    change_set: ChangeSet,
    test_evidence: list[TestEvidence],
    client: ModelClient,
) -> list[DeclarationMismatch]:
    """Flag declaration claims matching neither the task nor the code/tests."""
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": _render_prompt(declaration, obligations, change_set, test_evidence),
        },
    ]
    result = client.complete(messages, _Mismatches)
    return [
        DeclarationMismatch(claim=m.claim, rationale=m.rationale) for m in result.mismatches
    ]


def declaration_mismatch_finding(mismatch: DeclarationMismatch) -> Finding:
    """A §7.4 declaration-vs-evidence discrepancy, as an advisory, obligation-
    less finding. Low severity and the BUILDER_CLAIM tier: it flags the
    declaration as inaccurate, but nothing was mis-delivered in the code, so it
    does not block acceptance of the actual change (issue #31)."""
    return Finding(
        type=DECLARATION_MISMATCH,
        severity="low",
        description=f"Declaration claim unsupported by code or tests: {mismatch.rationale}",
        evidence_tier=EvidenceTier.BUILDER_CLAIM,
        produced_by=Component.BUILDER_DECLARATION,
        links=[Link(kind="declaration", ref="declaration", text=mismatch.claim)],
    )
