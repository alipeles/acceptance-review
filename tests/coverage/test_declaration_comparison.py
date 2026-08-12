"""M6.2 acceptance: a builder-declaration claim matching neither the task nor
the code/tests is produced as an advisory `declaration_mismatch` finding.

Comparison is a schema-constrained model call; per the replay-first invariant
these tests inject the recorded response via completion_fn — no live calls.
Comparison *accuracy* against the real model is shown by the PR's record run."""

from acceptance.coverage.declaration_comparison import (
    DeclarationMismatch,
    compare_declaration,
    declaration_mismatch_finding,
)
from acceptance.evidence_tier import Component, EvidenceTier
from acceptance.review_state import (
    DECLARATION_MISMATCH,
    BuilderDeclaration,
    ChangeSet,
    DiffHunk,
    FileChange,
    ObligationType,
    TestEvidence,
)
from tests.support import client_returning as _client_returning
from tests.support import make_obligation as _obligation


def _declaration(**overrides: str) -> BuilderDeclaration:
    base = {name: "" for name in BuilderDeclaration.model_fields}
    base.update(overrides)
    return BuilderDeclaration(**base)


def _archetype_7_inputs():
    # get_user returns None on a miss; the declaration claims it raises KeyError.
    declaration = _declaration(
        mandate_as_understood="Provide a lookup that returns a user record by its id.",
        implementation_summary="Added `get_user(users, user_id)`.",
        known_limitations="Raises `KeyError` with a clear message when the id is not present.",
    )
    obligations = [
        _obligation("lookup", "Return the user record matching user_id", ObligationType.FUNCTIONAL),
    ]
    change_set = ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(
                path="users.py",
                status="modified",
                category="source",
                hunks=[
                    DiffHunk(
                        header="@@ -1,2 +1,2 @@",
                        old_start=1,
                        old_lines=2,
                        new_start=1,
                        new_lines=2,
                        content="-    raise NotImplementedError\n+    return users.get(user_id)",
                    )
                ],
            ),
        ],
    )
    test_evidence = [
        TestEvidence(
            identifier="test_users.py::test_existing_id_returns_the_record",
            location="test_users.py",
            assertions=["get_user(users, 1) == {'name': 'Ada'}"],
        ),
    ]
    return declaration, obligations, change_set, test_evidence


def test_overclaimed_error_condition_is_flagged():
    declaration, obligations, change_set, test_evidence = _archetype_7_inputs()
    response = {
        "mismatches": [
            {
                "claim": "get_user raises KeyError with a clear message on a missing id",
                "rationale": (
                    "The implementation returns None on a missing id and no test exercises "
                    "the missing-id path; no code path or test supports the claim."
                ),
            }
        ]
    }

    mismatches = compare_declaration(
        declaration, obligations, change_set, test_evidence, _client_returning(response)
    )

    assert len(mismatches) == 1
    assert "KeyError" in mismatches[0].claim


def test_truthful_declaration_flags_nothing():
    declaration, obligations, change_set, test_evidence = _archetype_7_inputs()

    mismatches = compare_declaration(
        declaration,
        obligations,
        change_set,
        test_evidence,
        _client_returning({"mismatches": []}),
    )

    assert mismatches == []


def test_mismatch_finding_is_advisory_and_obligation_less():
    mismatch = DeclarationMismatch(
        claim="get_user raises KeyError on a missing id",
        rationale="The code returns None and no test covers the missing-id path.",
    )
    finding = declaration_mismatch_finding(mismatch)

    assert finding.type == DECLARATION_MISMATCH
    assert finding.severity == "low"  # advisory / low-weight (issue #31)
    assert finding.evidence_tier == EvidenceTier.BUILDER_CLAIM  # a claim, not proof
    assert finding.produced_by == Component.BUILDER_DECLARATION
    assert finding.related_obligation is None  # obligation-less by construction
    assert finding.links[0].kind == "declaration"
    assert "KeyError" in finding.links[0].text


def test_declaration_mismatch_round_trips_through_persistence():
    mismatch = DeclarationMismatch(claim="c", rationale="r")
    assert DeclarationMismatch.from_dict(mismatch.to_dict()) == mismatch
