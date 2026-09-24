"""Exercise the audit driver's rendering and the scorer, with no model calls.

Run it after touching either script:

    .venv/bin/python dogfood-logs/45-injection-audits/check_audit_scripts.py

It builds synthetic attempts, renders them, and scores them against synthetic
labels whose rates are known by hand. It is not a pytest test: the audit
harness is apparatus beside the audits, not part of the package, and putting it
under `tests/` would make CI carry it.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import ClassVar

AUDITS = Path(__file__).resolve().parent
REPO = AUDITS.parents[1]
HERE = Path(tempfile.mkdtemp(prefix="audit-check-"))
sys.path.insert(0, str(AUDITS))
sys.path.insert(0, str(REPO / "src"))

import run_audit

from acceptance.llm import SERVED_FROM_PROVIDER, SERVED_FROM_RECORDING
from acceptance.mutation.attempt import (
    CandidateCause,
    MutationAttempt,
    MutationDescriptor,
    MutationOutcomeKind,
    RepairCorroboration,
    SetAsideCandidate,
    VerificationStep,
)
from acceptance.review_state import Defect


def defect(name, **kw):
    return Defect(
        id=name,
        obligation_id="obligation-1",
        type=kw.get("type", "condition_inverted"),
        description=f"{name} description",
        expected_behavior=f"{name} expected",
        defective_behavior=f"{name} defective",
        code_refs=[],
    )


def descriptor(path="src/a.py"):
    return MutationDescriptor(
        path=path,
        start_line=1,
        end_line=2,
        replacement="if not ok:\n    return",
        region_label="a",
        original="if ok:\n    return",
    )


attempts = [
    # a good edit the verifier accepted
    MutationAttempt(
        defect_id="good-killed",
        outcome=MutationOutcomeKind.KILLED,
        descriptor=descriptor(),
        killing_tests=["tests/test_a.py::test_one"],
        tests_run=["tests/test_a.py::test_one"],
        verified=True,
        verification_reason="makes the defect true",
        candidates_asked=1,
        candidate_used=1,
    ),
    # a bad edit the verifier refused on the first question
    MutationAttempt(
        defect_id="noop-survived",
        outcome=MutationOutcomeKind.SURVIVED,
        descriptor=descriptor("src/b.py"),
        tests_run=["tests/test_a.py::test_one"],
        verified=False,
        verification_reason="no behaviour change",
        refused_by=VerificationStep.BEHAVIOUR_CHANGE,
        candidates_asked=3,
        candidate_used=3,
        set_aside_candidates=[
            SetAsideCandidate(cause=CandidateCause.CHANGED_NOTHING, reason="identical"),
            SetAsideCandidate(cause=CandidateCause.FAILED_CHECK, reason="outside the region"),
        ],
    ),
    # a bad edit the verifier let through: a false negative for #335
    MutationAttempt(
        defect_id="wrong-killed",
        outcome=MutationOutcomeKind.KILLED,
        descriptor=descriptor("src/c.py"),
        killing_tests=["tests/test_a.py::test_two"],
        tests_run=["tests/test_a.py::test_two"],
        verified=True,
        verification_reason="looks right",
        candidates_asked=2,
        candidate_used=2,
        set_aside_candidates=[
            SetAsideCandidate(cause=CandidateCause.FAILED_CHECK, reason="over the size bound")
        ],
    ),
    # every candidate refused
    MutationAttempt(
        defect_id="no-usable",
        outcome=MutationOutcomeKind.NO_USABLE_EDIT,
        reason="all three candidates refused",
        candidates_asked=3,
        set_aside_candidates=[
            SetAsideCandidate(cause=CandidateCause.CHANGED_NOTHING, reason="identical"),
            SetAsideCandidate(cause=CandidateCause.CHANGED_NOTHING, reason="identical again"),
            SetAsideCandidate(cause=CandidateCause.FAILED_CHECK, reason="outside the region"),
        ],
    ),
    # an already-present claim with a repair
    MutationAttempt(
        defect_id="already-there",
        outcome=MutationOutcomeKind.ALREADY_PRESENT,
        reason="the code already does this",
        repair=descriptor("src/d.py"),
        repair_corroboration=RepairCorroboration.A_TEST_ASSERTS_DEFECTIVE,
        repair_failing_tests=["tests/test_a.py::test_three"],
    ),
]
defects = {a.defect_id: defect(a.defect_id) for a in attempts}

md = run_audit.render(
    attempts, defects, audit="vTEST", head="518f876", note="synthetic", usable_tests=339
)
(HERE / "audit.md").write_text(md)

# the verifier's answer must not appear in what the judge reads
for forbidden in ("no behaviour change", "makes the defect true", "looks right", "verified"):
    assert forbidden not in md, f"verification leaked into the judge's input: {forbidden!r}"
assert "## `killed` — good-killed" in md
assert "**candidate 1 set aside:** `changed_nothing`" in md
assert "**repair** — `src/d.py`" in md
print("render: ok, verification does not leak into the judged Markdown")


class FakeClient:
    # The provenance strings come from `llm.py`, not from this file: writing the
    # word by hand is how a live run was reported as fully replayed, at a cost
    # of $0.00, because both the driver and this check used "live" — a word the
    # client never emits.
    observed_calls: ClassVar[list[dict]] = [
        {
            "stage": "mutation descriptor",
            "served_from": SERVED_FROM_PROVIDER,
            "usage": {"cost_usd": 0.02, "reasoning_tokens": 40},
            "seconds": 3.0,
        },
        {
            "stage": "mutation descriptor",
            "served_from": SERVED_FROM_RECORDING,
            "usage": {"cost_usd": 0.01},
            "seconds": None,
        },
        {
            "stage": "mutation verification: defect match",
            "served_from": SERVED_FROM_PROVIDER,
            "usage": {"cost_usd": 0.005},
            "seconds": 1.0,
        },
    ]


rows = run_audit.spend(FakeClient())
assert rows["mutation descriptor"]["calls"] == 2
assert rows["mutation descriptor"]["live"] == 1
assert abs(rows["mutation descriptor"]["cost_usd"] - 0.03) < 1e-9
assert rows["mutation descriptor"]["seconds"] == 3.0
assert rows["mutation descriptor"]["reasoning_tokens"] == 40
assert rows["mutation verification: defect match"]["reasoning_tokens"] == 0
print("spend: ok, replayed calls counted but not timed, reasoning tokens summed")

assert run_audit.parse_reasoning(["mutation descriptor=low", "a=b=high"]) == {
    "mutation descriptor": "low",
    "a=b": "high",
}
print("parse_reasoning: ok")

attempts_doc = {
    "audit": "vTEST",
    "revision": "518f876",
    "base": "61c5a3c",
    "descriptor_model": "openai/gpt-5.4-mini",
    "verifier_model": "openai/gpt-5.4",
    "max_candidates": 3,
    "criteria": 22,
    "usable_tests": 339,
    "wall_clock_seconds": 120.0,
    "spend": rows,
    "attempts": [a.to_dict() for a in attempts],
}
(HERE / "attempts.json").write_text(json.dumps(attempts_doc, indent=2))

labels_doc = {
    "audit": "vTEST",
    "source": "audit.md",
    "revision": "518f876",
    "descriptor_model": "openai/gpt-5.4-mini",
    "protocol": "docs/audit-protocol.md",
    "labels": [
        {
            "defect_id": "good-killed",
            "outcome": "killed",
            "edit": "injects",
            "changes_behaviour": True,
        },
        {
            "defect_id": "noop-survived",
            "outcome": "survived",
            "edit": "unrelated",
            "changes_behaviour": False,
        },
        {
            "defect_id": "wrong-killed",
            "outcome": "killed",
            "edit": "unrelated",
            "changes_behaviour": True,
        },
        {"defect_id": "no-usable", "outcome": "no_usable_edit"},
        {
            "defect_id": "already-there",
            "outcome": "already_present",
            "claim": "right",
            "repair": "repairs",
        },
    ],
}
(HERE / "labels.json").write_text(json.dumps(labels_doc, indent=2))

result = subprocess.run(
    check=False,
    args=[
        sys.executable,
        str(AUDITS / "score_audit.py"),
        "--labels",
        str(HERE / "labels.json"),
        "--attempts",
        str(HERE / "attempts.json"),
    ],
    capture_output=True,
    text=True,
)
print(result.stdout, result.stderr)
assert result.returncode == 0, "scorer failed"
assert "put the named defect into the code: 1/3 (33%)" in result.stdout
assert "change no behaviour at all: 1/3 (33%)" in result.stdout
assert "bad edits refused: 1/2 (50%)" in result.stdout
assert "good edits refused: 0/1 (0%)" in result.stdout
assert "NOT met" in result.stdout
assert "real kills: 1/2 (50%)" in result.stdout
print("score: ok")
