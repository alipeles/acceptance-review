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
        id=obligation_id, description=f"{obligation_id} obligation",
        type=ObligationType.FUNCTIONAL, importance="critical", explicit=True,
        observable_behavior="...",
    )


def _hunk(header: str = "@@ -1 +1 @@") -> DiffHunk:
    return DiffHunk(header=header, old_start=1, old_lines=1, new_start=1, new_lines=1, content="+x")


def _change(file: str, header: str = "@@ -1 +1 @@", kind=UnrequestedChangeKind.ADJACENT_BEHAVIOR):
    return UnrequestedChange(
        kind=kind, rationale=f"unrequested change in {file}",
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
    change_set = ChangeSet(base_revision="a", head_revision="b", files=[
        FileChange(path="pkg.py", status="modified", category="source", hunks=[_hunk()]),
    ])
    coverages = [ImplementationCoverage(
        obligation_id="ob-1", status=CoverageStatus.ADDRESSED, rationale="here",
        diff_refs=[DiffRef(file="pkg.py", hunk_header="@@ -1 +1 @@")],
    )]
    changes = [_change("pkg.py")]

    result = classify_dispositions(
        changes, [_obligation("ob-1")], coverages, change_set,
        ScopeExpansionPolicy.STRICT, _exploding_client(),
    )

    assert result[0].disposition is UnrequestedChangeDisposition.IN_SERVICE
    assert result[0].decided_by == "structural"
    assert result[0].recommendation is None


def test_pure_new_file_addition_is_separable_without_a_model_call():
    change_set = ChangeSet(base_revision="a", head_revision="b", files=[
        FileChange(path="extra.py", status="added", category="source", hunks=[_hunk()]),
    ])
    changes = [_change("extra.py")]

    result = classify_dispositions(
        changes, [_obligation("ob-1")], [], change_set,
        ScopeExpansionPolicy.STRICT, _exploding_client(),
    )

    assert result[0].disposition is UnrequestedChangeDisposition.SEPARABLE
    assert result[0].decided_by == "structural"
    assert "splitting" in result[0].recommendation


def test_partially_addressed_overlap_does_not_shortcut_to_in_service():
    # A partially_addressed region can be the one that *violates* a leave-as-is
    # obligation (archetype #8), so it must NOT deterministically become
    # in_service — it escalates to the model.
    change_set = ChangeSet(base_revision="a", head_revision="b", files=[
        FileChange(path="cart.py", status="modified", category="source", hunks=[_hunk()]),
    ])
    coverages = [ImplementationCoverage(
        obligation_id="leave-existing", status=CoverageStatus.PARTIALLY_ADDRESSED,
        rationale="default still ok", diff_refs=[DiffRef(file="cart.py", hunk_header="@@ -1 +1 @@")],
    )]
    changes = [_change("cart.py", kind=UnrequestedChangeKind.PUBLIC_INTERFACE)]
    client = client_dispatching({"_DispositionJudgment": {
        "disposition": "risky", "rationale": "edits existing public signature",
    }})

    result = classify_dispositions(
        changes, [_obligation("leave-existing")], coverages, change_set,
        ScopeExpansionPolicy.STRICT, client,
    )

    assert result[0].disposition is UnrequestedChangeDisposition.RISKY
    assert result[0].decided_by == "model"
    assert "Scrutinize" in result[0].recommendation


def test_modifies_existing_escalates_to_the_model():
    change_set = ChangeSet(base_revision="a", head_revision="b", files=[
        FileChange(path="mod.py", status="modified", category="source", hunks=[_hunk()]),
    ])
    changes = [_change("mod.py")]
    client = client_dispatching({"_DispositionJudgment": {
        "disposition": "separable", "rationale": "distinct helper, task complete without it",
    }})

    result = classify_dispositions(
        changes, [_obligation("ob-1")], [], change_set,
        ScopeExpansionPolicy.LOOSE, client,
    )

    assert result[0].disposition is UnrequestedChangeDisposition.SEPARABLE
    assert result[0].decided_by == "model"


def test_policy_is_surfaced_to_the_model_judgment():
    # strict vs loose changes the adjacent-behavior verdict, so the model must
    # see the policy. Capture the prompt and assert the policy is in it.
    change_set = ChangeSet(base_revision="a", head_revision="b", files=[
        FileChange(path="mod.py", status="modified", category="source", hunks=[_hunk()]),
    ])
    changes = [_change("mod.py")]
    seen = {}

    def capture(**kwargs):
        seen["prompt"] = kwargs["messages"][-1]["content"]
        content = json.dumps({"disposition": "risky", "rationale": "adjacent edit"})
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

    client = ModelClient(model="x", mode=Mode.RECORD,
                         store=TranscriptStore(tempfile.mkdtemp()), completion_fn=capture)

    classify_dispositions(changes, [_obligation("ob-1")], [], change_set,
                          ScopeExpansionPolicy.LOOSE, client)

    assert "loose" in seen["prompt"]


def test_dispositioned_change_round_trips():
    change_set = ChangeSet(base_revision="a", head_revision="b", files=[
        FileChange(path="extra.py", status="added", category="source", hunks=[_hunk()]),
    ])
    result = classify_dispositions(
        [_change("extra.py")], [_obligation("ob-1")], [], change_set,
        ScopeExpansionPolicy.STRICT, _exploding_client(),
    )[0]

    assert DispositionedChange.from_dict(result.to_dict()) == result
