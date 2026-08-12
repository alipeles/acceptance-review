"""M3.5.3 acceptance: separability classification for unrequested changes.

The classifier is a hybrid (M3.5.3 / DR-081): deterministic fast-paths for the
unambiguous cases (coverage-overlap -> in_service; pure new-file addition ->
separable) with no model call, and a schema-constrained model judgment for the
ambiguous "modifies existing code" rest — recorded for replay, no live calls.
A client that raises on use proves the fast-paths take no model call.
"""

import json
import tempfile
from types import SimpleNamespace

from acceptance.config import ScopeExpansionPolicy
from acceptance.coverage.classify import CoverageStatus, DiffRef, ImplementationCoverage
from acceptance.coverage.disposition import DispositionedChange, classify_dispositions
from acceptance.coverage.unrequested import UnrequestedChange, UnrequestedChangeKind
from acceptance.llm import Mode, ModelClient, TranscriptStore
from acceptance.review_state import (
    ChangeSet,
    DiffHunk,
    FileChange,
    Obligation,
    ObligationType,
    UnrequestedChangeDisposition,
)
from tests.support import client_dispatching


def _obligation(obligation_id: str) -> Obligation:
    return Obligation(
        id=obligation_id,
        description=f"{obligation_id} obligation",
        type=ObligationType.FUNCTIONAL,
        importance="critical",
        explicit=True,
        observable_behavior="...",
    )


def _hunk(header: str = "@@ -1 +1 @@") -> DiffHunk:
    return DiffHunk(header=header, old_start=1, old_lines=1, new_start=1, new_lines=1, content="+x")


def _change(file: str, header: str = "@@ -1 +1 @@", kind=UnrequestedChangeKind.ADJACENT_BEHAVIOR):
    return UnrequestedChange(
        kind=kind,
        rationale=f"unrequested change in {file}",
        diff_refs=[DiffRef(file=file, hunk_header=header)],
    )


def _exploding_client() -> ModelClient:
    """A client whose completion_fn must never be called — proves a
    deterministic fast-path issued no model call."""

    def boom(**kwargs):
        raise AssertionError("a model call was issued on a deterministic fast-path")

    return ModelClient(
        model="x", mode=Mode.RECORD, store=TranscriptStore(tempfile.mkdtemp()), completion_fn=boom
    )


def test_load_bearing_change_is_in_service_without_a_model_call():
    # The change's region is exactly where an obligation is `addressed`.
    change_set = ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(path="pkg.py", status="modified", category="source", hunks=[_hunk()]),
        ],
    )
    coverages = [
        ImplementationCoverage(
            obligation_id="ob-1",
            status=CoverageStatus.ADDRESSED,
            rationale="here",
            diff_refs=[DiffRef(file="pkg.py", hunk_header="@@ -1 +1 @@")],
        )
    ]
    changes = [_change("pkg.py")]

    result = classify_dispositions(
        changes,
        [_obligation("ob-1")],
        coverages,
        change_set,
        ScopeExpansionPolicy.STRICT,
        _exploding_client(),
    )

    assert result[0].disposition is UnrequestedChangeDisposition.IN_SERVICE
    assert result[0].decided_by == "structural"
    assert result[0].recommendation is None


def test_pure_new_file_addition_is_separable_without_a_model_call():
    change_set = ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(path="extra.py", status="added", category="source", hunks=[_hunk()]),
        ],
    )
    changes = [_change("extra.py")]

    result = classify_dispositions(
        changes,
        [_obligation("ob-1")],
        [],
        change_set,
        ScopeExpansionPolicy.STRICT,
        _exploding_client(),
    )

    assert result[0].disposition is UnrequestedChangeDisposition.SEPARABLE
    assert result[0].decided_by == "structural"
    assert "splitting" in result[0].recommendation


def test_docstring_update_of_in_service_change_is_in_service_without_a_model_call():
    # #122: a PR edits a function (in-service, addressed) AND updates a
    # module docstring describing it, in a separate hunk. The docstring hunk
    # must classify in_service, not separable-with-a-split-recommendation.
    code_hunk = _hunk(header="@@ -10,3 +10,3 @@")
    doc_hunk = DiffHunk(
        header="@@ -1,2 +1,4 @@",
        old_start=1,
        old_lines=2,
        new_start=1,
        new_lines=4,
        content='+"""Module docstring.\n+\n+Now also describes the new behavior.\n+"""',
    )
    change_set = ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(
                path="pkg.py", status="modified", category="source", hunks=[code_hunk, doc_hunk]
            ),
        ],
    )
    coverages = [
        ImplementationCoverage(
            obligation_id="ob-1",
            status=CoverageStatus.ADDRESSED,
            rationale="here",
            diff_refs=[DiffRef(file="pkg.py", hunk_header=code_hunk.header)],
        )
    ]
    changes = [_change("pkg.py", header=doc_hunk.header, kind=UnrequestedChangeKind.OTHER)]

    result = classify_dispositions(
        changes,
        [_obligation("ob-1")],
        coverages,
        change_set,
        ScopeExpansionPolicy.STRICT,
        _exploding_client(),
    )

    assert result[0].disposition is UnrequestedChangeDisposition.IN_SERVICE
    assert result[0].decided_by == "structural"
    assert result[0].recommendation is None


def test_comment_only_hunk_in_unaddressed_file_still_escalates_to_the_model():
    # The docstring heuristic only fires when the SAME file also has an
    # addressed hunk (#122's "documentation OF an in-service change"); a
    # comment-only change with no in-service sibling in that file is still
    # genuinely ambiguous and escalates.
    doc_hunk = DiffHunk(
        header="@@ -1 +1 @@",
        old_start=1,
        old_lines=1,
        new_start=1,
        new_lines=1,
        content="+# just a comment, no addressed code in this file",
    )
    change_set = ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(path="notes.py", status="modified", category="source", hunks=[doc_hunk]),
        ],
    )
    changes = [_change("notes.py", header=doc_hunk.header, kind=UnrequestedChangeKind.OTHER)]
    client = client_dispatching(
        {
            "_DispositionJudgment": {
                "disposition": "separable",
                "rationale": "unrelated comment",
            }
        }
    )

    result = classify_dispositions(
        changes,
        [_obligation("ob-1")],
        [],
        change_set,
        ScopeExpansionPolicy.STRICT,
        client,
    )

    assert result[0].decided_by == "model"


def test_hunk_mixing_code_and_comments_does_not_shortcut_to_in_service():
    # A hunk that changes real code (not just comments/docstring) must not be
    # mistaken for documentation, even if co-located with an addressed hunk.
    code_hunk = _hunk(header="@@ -10,3 +10,3 @@")
    mixed_hunk = DiffHunk(
        header="@@ -20,2 +20,3 @@",
        old_start=20,
        old_lines=2,
        new_start=20,
        new_lines=3,
        content="+# a helpful comment\n+result = compute(x) + 1",
    )
    change_set = ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(
                path="pkg.py", status="modified", category="source", hunks=[code_hunk, mixed_hunk]
            ),
        ],
    )
    coverages = [
        ImplementationCoverage(
            obligation_id="ob-1",
            status=CoverageStatus.ADDRESSED,
            rationale="here",
            diff_refs=[DiffRef(file="pkg.py", hunk_header=code_hunk.header)],
        )
    ]
    changes = [_change("pkg.py", header=mixed_hunk.header, kind=UnrequestedChangeKind.OTHER)]
    client = client_dispatching(
        {
            "_DispositionJudgment": {
                "disposition": "separable",
                "rationale": "extra computation",
            }
        }
    )

    result = classify_dispositions(
        changes,
        [_obligation("ob-1")],
        coverages,
        change_set,
        ScopeExpansionPolicy.STRICT,
        client,
    )

    assert result[0].decided_by == "model"


def test_symbol_renamed_and_imported_by_another_changed_file_is_in_service():
    # #126: file A renames/exports a symbol; file B (changed in the same diff)
    # imports and uses it. The rename in file A must classify in_service, not
    # separable -- reverting it would break file B's changes.
    rename_hunk = DiffHunk(
        header="@@ -100,3 +100,3 @@",
        old_start=100,
        old_lines=3,
        new_start=100,
        new_lines=3,
        content="+def parse_test_function(source: str):\n+    ...",
    )
    import_hunk = DiffHunk(
        header="@@ -1,2 +1,3 @@",
        old_start=1,
        old_lines=2,
        new_start=1,
        new_lines=3,
        content="+from acceptance.evidence.extraction import parse_test_function\n+\n+detect_weak_patterns()",
    )
    change_set = ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(
                path="src/acceptance/evidence/extraction.py",
                status="modified",
                category="source",
                hunks=[rename_hunk],
            ),
            FileChange(
                path="src/acceptance/evidence/weak_patterns.py",
                status="added",
                category="source",
                hunks=[import_hunk],
            ),
        ],
    )
    changes = [
        _change(
            "src/acceptance/evidence/extraction.py",
            header=rename_hunk.header,
            kind=UnrequestedChangeKind.INTERNAL,
        )
    ]

    result = classify_dispositions(
        changes,
        [_obligation("ob-1")],
        [],
        change_set,
        ScopeExpansionPolicy.STRICT,
        _exploding_client(),
    )

    assert result[0].disposition is UnrequestedChangeDisposition.IN_SERVICE
    assert result[0].decided_by == "structural"
    assert result[0].recommendation is None


def test_defined_symbol_not_imported_elsewhere_still_escalates_to_the_model():
    # A renamed symbol that nothing else in the diff imports is genuinely
    # ambiguous (could still be in_service via coverage, or a distinct helper)
    # and must still escalate rather than false-positive to in_service.
    rename_hunk = DiffHunk(
        header="@@ -100,2 +100,2 @@",
        old_start=100,
        old_lines=2,
        new_start=100,
        new_lines=2,
        content="+def unused_helper():\n+    ...",
    )
    other_hunk = DiffHunk(
        header="@@ -1,1 +1,1 @@",
        old_start=1,
        old_lines=1,
        new_start=1,
        new_lines=1,
        content="+x = 1",
    )
    change_set = ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(path="a.py", status="modified", category="source", hunks=[rename_hunk]),
            FileChange(path="b.py", status="modified", category="source", hunks=[other_hunk]),
        ],
    )
    changes = [_change("a.py", header=rename_hunk.header, kind=UnrequestedChangeKind.INTERNAL)]
    client = client_dispatching(
        {
            "_DispositionJudgment": {
                "disposition": "separable",
                "rationale": "unused new helper",
            }
        }
    )

    result = classify_dispositions(
        changes,
        [_obligation("ob-1")],
        [],
        change_set,
        ScopeExpansionPolicy.STRICT,
        client,
    )

    assert result[0].decided_by == "model"


def test_partially_addressed_overlap_does_not_shortcut_to_in_service():
    # A partially_addressed region can be the one that *violates* a leave-as-is
    # obligation (archetype #8), so it must NOT deterministically become
    # in_service — it escalates to the model.
    change_set = ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(path="cart.py", status="modified", category="source", hunks=[_hunk()]),
        ],
    )
    coverages = [
        ImplementationCoverage(
            obligation_id="leave-existing",
            status=CoverageStatus.PARTIALLY_ADDRESSED,
            rationale="default still ok",
            diff_refs=[DiffRef(file="cart.py", hunk_header="@@ -1 +1 @@")],
        )
    ]
    changes = [_change("cart.py", kind=UnrequestedChangeKind.PUBLIC_INTERFACE)]
    client = client_dispatching(
        {
            "_DispositionJudgment": {
                "disposition": "risky",
                "rationale": "edits existing public signature",
            }
        }
    )

    result = classify_dispositions(
        changes,
        [_obligation("leave-existing")],
        coverages,
        change_set,
        ScopeExpansionPolicy.STRICT,
        client,
    )

    assert result[0].disposition is UnrequestedChangeDisposition.RISKY
    assert result[0].decided_by == "model"
    assert "Scrutinize" in result[0].recommendation


def test_modifies_existing_escalates_to_the_model():
    change_set = ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(path="mod.py", status="modified", category="source", hunks=[_hunk()]),
        ],
    )
    changes = [_change("mod.py")]
    client = client_dispatching(
        {
            "_DispositionJudgment": {
                "disposition": "separable",
                "rationale": "distinct helper, task complete without it",
            }
        }
    )

    result = classify_dispositions(
        changes,
        [_obligation("ob-1")],
        [],
        change_set,
        ScopeExpansionPolicy.LOOSE,
        client,
    )

    assert result[0].disposition is UnrequestedChangeDisposition.SEPARABLE
    assert result[0].decided_by == "model"


def test_policy_is_surfaced_to_the_model_judgment():
    # strict vs loose changes the adjacent-behavior verdict, so the model must
    # see the policy. Capture the prompt and assert the policy is in it.
    change_set = ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(path="mod.py", status="modified", category="source", hunks=[_hunk()]),
        ],
    )
    changes = [_change("mod.py")]
    seen = {}

    def capture(**kwargs):
        seen["prompt"] = kwargs["messages"][-1]["content"]
        content = json.dumps({"disposition": "risky", "rationale": "adjacent edit"})
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

    client = ModelClient(
        model="x",
        mode=Mode.RECORD,
        store=TranscriptStore(tempfile.mkdtemp()),
        completion_fn=capture,
    )

    classify_dispositions(
        changes, [_obligation("ob-1")], [], change_set, ScopeExpansionPolicy.LOOSE, client
    )

    assert "loose" in seen["prompt"]


def test_dispositioned_change_round_trips():
    change_set = ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(path="extra.py", status="added", category="source", hunks=[_hunk()]),
        ],
    )
    result = classify_dispositions(
        [_change("extra.py")],
        [_obligation("ob-1")],
        [],
        change_set,
        ScopeExpansionPolicy.STRICT,
        _exploding_client(),
    )[0]

    assert DispositionedChange.from_dict(result.to_dict()) == result


def test_test_fixture_updates_required_by_a_source_change_are_in_service():
    """#139: wiring a capability into a shared pipeline forces existing tests to
    add fixture/dispatch entries. Removing them breaks the suite, so the
    removability litmus says in_service -- and nobody ships "add a fixture" as
    its own PR. This recurred across #122/#126/#139, so it is caught
    structurally, with no model call."""
    source_hunk = _hunk(header="@@ -10,3 +10,4 @@")
    fixture_hunk = DiffHunk(
        header="@@ -20,2 +20,3 @@",
        old_start=20,
        old_lines=2,
        new_start=20,
        new_lines=3,
        content='+            "_Recommendations": {"recommendations": []},',
    )
    change_set = ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(
                path="src/pkg/pipeline.py",
                status="modified",
                category="source",
                hunks=[source_hunk],
            ),
            FileChange(
                path="tests/test_pipeline.py",
                status="modified",
                category="test",
                hunks=[fixture_hunk],
            ),
        ],
    )
    changes = [
        _change(
            "tests/test_pipeline.py", header=fixture_hunk.header, kind=UnrequestedChangeKind.OTHER
        )
    ]

    result = classify_dispositions(
        changes,
        [_obligation("ob-1")],
        [],
        change_set,
        ScopeExpansionPolicy.STRICT,
        _exploding_client(),
    )

    assert result[0].disposition is UnrequestedChangeDisposition.IN_SERVICE
    assert result[0].decided_by == "structural"
    assert result[0].recommendation is None


def test_new_test_functions_still_escalate_to_the_model():
    """The discriminator: adding a `def test_...` may be genuinely distinct test
    work, so it must NOT be swept into in_service by the fixture fast-path."""
    source_hunk = _hunk(header="@@ -10,3 +10,4 @@")
    new_test_hunk = DiffHunk(
        header="@@ -30,1 +30,4 @@",
        old_start=30,
        old_lines=1,
        new_start=30,
        new_lines=4,
        content="+def test_an_unrelated_new_behavior():\n+    assert compute() == 3",
    )
    change_set = ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(
                path="src/pkg/pipeline.py",
                status="modified",
                category="source",
                hunks=[source_hunk],
            ),
            FileChange(
                path="tests/test_pipeline.py",
                status="modified",
                category="test",
                hunks=[new_test_hunk],
            ),
        ],
    )
    changes = [
        _change(
            "tests/test_pipeline.py", header=new_test_hunk.header, kind=UnrequestedChangeKind.OTHER
        )
    ]
    client = client_dispatching(
        {
            "_DispositionJudgment": {
                "disposition": "separable",
                "rationale": "an unrelated new test",
            }
        }
    )

    result = classify_dispositions(
        changes,
        [_obligation("ob-1")],
        [],
        change_set,
        ScopeExpansionPolicy.STRICT,
        client,
    )

    assert result[0].decided_by == "model"


def test_test_only_diff_is_not_swept_into_in_service():
    """With no source change in the diff, test edits are ordinary test work and
    must still be judged, not assumed to be scaffolding for something else."""
    test_hunk = DiffHunk(
        header="@@ -20,2 +20,3 @@",
        old_start=20,
        old_lines=2,
        new_start=20,
        new_lines=3,
        content="+    helper_value = 3",
    )
    change_set = ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(
                path="tests/test_pipeline.py", status="modified", category="test", hunks=[test_hunk]
            ),
        ],
    )
    changes = [
        _change("tests/test_pipeline.py", header=test_hunk.header, kind=UnrequestedChangeKind.OTHER)
    ]
    client = client_dispatching(
        {
            "_DispositionJudgment": {
                "disposition": "separable",
                "rationale": "standalone test refactor",
            }
        }
    )

    result = classify_dispositions(
        changes,
        [_obligation("ob-1")],
        [],
        change_set,
        ScopeExpansionPolicy.STRICT,
        client,
    )

    assert result[0].decided_by == "model"


def test_a_small_opportunistic_edit_is_still_separable():
    """A drive-by comment or safeguard on an unrelated function is unrequested
    scope the reviewer should see. It is NOT in_service (nothing in the diff
    depends on it), so it must not be swept there just because it is too small
    to warrant its own PR — size governs the recommendation, not the
    classification. Guards against re-tightening `separable` to mean
    "PR-worthy" (the taxonomy gap tracked in #145)."""
    source_hunk = _hunk(header="@@ -10,3 +10,4 @@")
    drive_by_hunk = DiffHunk(
        header="@@ -80,2 +80,4 @@",
        old_start=80,
        old_lines=2,
        new_start=80,
        new_lines=4,
        content="+    # guard against a negative balance while we're in here\n+    if balance < 0:\n+        raise ValueError(balance)",
    )
    change_set = ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(
                path="src/pkg/pipeline.py",
                status="modified",
                category="source",
                hunks=[source_hunk],
            ),
            FileChange(
                path="src/pkg/unrelated.py",
                status="modified",
                category="source",
                hunks=[drive_by_hunk],
            ),
        ],
    )
    changes = [
        _change(
            "src/pkg/unrelated.py", header=drive_by_hunk.header, kind=UnrequestedChangeKind.OTHER
        )
    ]
    client = client_dispatching(
        {
            "_DispositionJudgment": {
                "disposition": "separable",
                "rationale": "an unrelated safeguard added in passing; nothing here depends on it",
            }
        }
    )

    result = classify_dispositions(
        changes,
        [_obligation("ob-1")],
        [],
        change_set,
        ScopeExpansionPolicy.STRICT,
        client,
    )

    assert result[0].disposition is UnrequestedChangeDisposition.SEPARABLE
    assert result[0].decided_by == "model"


def test_the_escalation_prompt_asks_both_limbs_of_the_litmus():
    """The fast-paths above cover the structural half of the litmus; this
    guards the other half — the prompt used for ambiguous cases.

    Asking only "would every obligation still be satisfied?" and never "would
    the rest of the diff still work?" is precisely what let #122, #126 and #139
    recur, so limb (b) must not silently disappear from the prompt.

    Limitation, stated plainly: this asserts the model SEES both limbs, not
    that it OBEYS them — the weakness tracked in #138. Real behavioural
    evidence needs a recorded model response (#146); the archetype
    `08-unrequested-change-test-support` carries the ground truth for it.
    """
    change_set = ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(path="mod.py", status="modified", category="source", hunks=[_hunk()]),
        ],
    )
    changes = [_change("mod.py")]
    seen = {}

    def capture(**kwargs):
        seen["system"] = kwargs["messages"][0]["content"]
        content = json.dumps({"disposition": "separable", "rationale": "."})
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

    client = ModelClient(
        model="x",
        mode=Mode.RECORD,
        store=TranscriptStore(tempfile.mkdtemp()),
        completion_fn=capture,
    )

    classify_dispositions(
        changes, [_obligation("ob-1")], [], change_set, ScopeExpansionPolicy.STRICT, client
    )

    assert "Would every obligation still be satisfied" in seen["system"]  # limb (a)
    assert "Would the rest of the diff still WORK" in seen["system"]  # limb (b)
