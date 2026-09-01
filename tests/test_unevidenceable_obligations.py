"""#266: which evidence an obligation requires is decided once, at decomposition.

The stage-level contract lives beside each stage. These are the wiring tests —
that the decision reaches review state, that the stages which gather evidence
receive only the obligations that require it, that the verdict and the report
treat "not required" as an answer rather than a gap.

Defect injection has repeatedly found a well-tested helper the pipeline never
calls (CLAUDE.md), and the filtering here is exactly that shape: `requires_tests`
is a one-line property, and every guarantee in this change depends on the
pipeline consulting it at four separate points. So the assertions run through
`run_review`, and two of them look at what the stage was actually *given* rather
than at what came back.
"""

import subprocess

import pytest

from acceptance.change.diff import extract_change_set
from acceptance.pipeline import run_review
from acceptance.report import render_report
from acceptance.review_state import RequiredEvidence, Review
from tests.support import client_dispatching

_TASK = (
    "# Task\nThe build is clean.\n\n"
    "## Constraints\n"
    "- The checkout action is not on a Node 20 major version\n"
    "- Alpha behaves\n"
)

_PIN_REASON = "a property of the workflow file's action pin, which no pytest observes"


def _obligation(obligation_id: str, behavior: str, required: str, reason: str) -> dict:
    return {
        "id": obligation_id,
        "description": f"{behavior} (as a requirement)",
        "type": "functional",
        "importance": "critical",
        "explicit": True,
        "observable_behavior": behavior,
        "source_quote": behavior,
        "required_evidence": required,
        "required_evidence_reason": reason,
    }


def _judgments(*, checkout: str = "code_only", alpha: str = "code_and_tests") -> dict:
    """A full pipeline response set, with each obligation's required evidence
    parameterised so a test states only the part it is about."""
    return {
        "_Decomposition": {
            "obligations": [
                _obligation(
                    "checkout-action",
                    "the workflow pins actions/checkout at v5",
                    checkout,
                    _PIN_REASON if checkout != "code_and_tests" else "",
                ),
                _obligation(
                    "alpha",
                    "alpha() returns 1",
                    alpha,
                    "the repository cannot observe this" if alpha != "code_and_tests" else "",
                ),
            ],
            "open_questions": [],
            "requirement_dispositions": [],
        },
        # One enumerated way to fail per criterion, uncovered, so the
        # recommendation stage has something to be called about at all — which is
        # what the filtering test below reads its request from.
        "_Enumeration": {
            "obligation_id": "",
            "defects": [
                {
                    "slug": "returns-a-constant",
                    "type": "other",
                    "description": "returns a constant regardless of input",
                    "code_refs": [],
                }
            ],
            "reason": "",
        },
        "_Coverage": {
            "classifications": [
                {
                    "obligation_id": obligation_id,
                    "status": "addressed",
                    "rationale": "the diff implements it.",
                    "diff_refs": [],
                }
                for obligation_id in ("checkout-action", "alpha")
            ]
        },
        "_Detections": {"unrequested_changes": []},
        "_Judgments": {"resolutions": []},
        "_Recommendations": {"recommendations": []},
        "_Mismatches": {"mismatches": []},
    }


def _build_repo(tmp_path, *, touch_source: bool):
    """A two-commit repo. `touch_source=False` gives the configuration-only
    change from `dogfood-logs/261-gate2-run1/`, the shape the original abort was
    seen on.

    `touch_source=True` moves `alpha.py` as well, which is what makes test
    discovery return anything: discovery is driven by changed code, so under a
    config-only change the mapping stage is never called at all and a test about
    what the mapper was GIVEN would pass vacuously.
    """

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=tmp_path, capture_output=True, text=True, check=True
        ).stdout.strip()

    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    workflow = tmp_path / ".github" / "workflows"
    workflow.mkdir(parents=True)
    (workflow / "ci.yml").write_text(
        "jobs:\n  test:\n    steps:\n      - uses: actions/checkout@v3\n"
    )
    (tmp_path / "alpha.py").write_text("def alpha():\n    return 0\n")
    (tmp_path / "test_alpha.py").write_text(
        "from alpha import alpha\n\n\ndef test_alpha():\n    assert alpha() is not None\n"
    )
    git("add", "-A")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    (workflow / "ci.yml").write_text(
        "jobs:\n  test:\n    steps:\n      - uses: actions/checkout@v5\n"
    )
    if touch_source:
        (tmp_path / "alpha.py").write_text("def alpha():\n    return 1\n")
    git("add", "-A")
    git("commit", "-qm", "head")
    return base, git("rev-parse", "HEAD")


def _review(tmp_path, judgments, capture=None, touch_source=False) -> Review:
    base, head = _build_repo(tmp_path, touch_source=touch_source)
    return run_review(
        task_text=_TASK,
        change_set=extract_change_set(tmp_path, base, head),
        repo=tmp_path,
        client=client_dispatching(judgments, capture=capture),
        reviewed_revision=head,
    )


@pytest.fixture
def mixed_review(tmp_path) -> Review:
    """One obligation requiring code alone, one requiring both — so every
    assertion about the narrowed one has a control beside it in the same run."""
    return _review(tmp_path, _judgments())


def test_the_required_evidence_reaches_review_state_with_its_reason(mixed_review):
    """Decided at decomposition and persisted, so no later stage has to ask
    again — which is the whole restructure. When the question was asked twice,
    two stages disagreed about the same obligation on a real run."""
    by_id = {o.id: o for o in mixed_review.obligation_map}

    assert by_id["checkout-action"].required_evidence is RequiredEvidence.CODE_ONLY
    assert by_id["checkout-action"].required_evidence_reason == _PIN_REASON
    # The control: an ordinary obligation requires both and states no reason,
    # so "narrowed" stays visibly different from "not narrowed".
    assert by_id["alpha"].required_evidence is RequiredEvidence.CODE_AND_TESTS
    assert by_id["alpha"].required_evidence_reason == ""


def test_it_survives_persistence(mixed_review):
    """Review state is the interchange format between runs (§12), so a decision
    that exists only in memory is one a re-run silently loses."""
    restored = Review.from_dict(mixed_review.to_dict())

    assert [o.to_dict() for o in restored.obligation_map] == [
        o.to_dict() for o in mixed_review.obligation_map
    ]


def test_an_obligation_requiring_no_test_evidence_is_left_unrated(mixed_review):
    """`unsupported` would read as a gap; `None` says the axis was never applied.

    The rating is not merely hidden at render time — it is never produced, which
    is what the next test pins from the other side."""
    by_id = {o.id: o for o in mixed_review.obligation_map}

    assert by_id["checkout-action"].evidence_class is None
    assert by_id["checkout-action"].test_evidence == []


def test_an_obligation_requiring_no_test_evidence_never_reaches_the_prescriber(tmp_path):
    """The ordering change, asserted against what the stage was GIVEN.

    Every stage used to receive every obligation, and the ones no test could
    bear on were filtered out three stages later. Two costs, both observed on
    real runs: the stage chose between obligations that were never candidates,
    and ratings were produced for obligations whose ratings the report discards
    — surfacing as rating movement nobody could account for.

    **The stage this holds for is now the prescriber.** It used to be the
    test-to-criterion mapper, which #316 deleted; the remaining model call on
    the test-evidence axis that is keyed on criteria is the recommendation
    stage, and prescribing a test for a criterion no test is owed for demands
    evidence that cannot exist (#146, #153).

    Asserting the absence in the *request* is the only form of this that holds.
    A test on the output would pass just as well if the obligation were offered
    and then dropped, which is the behaviour being replaced."""
    capture = []
    _review(tmp_path, _judgments(), capture=capture, touch_source=True)

    calls = [c for c in capture if c["schema"] == "_Recommendations"]
    assert calls, "the recommendation stage was never called"
    for call in calls:
        assert "checkout-action" not in call["prompt"]
        # The control: the obligation that DOES require test evidence is there,
        # so this is not passing because the stage was given nothing at all.
        assert "alpha" in call["prompt"]


def test_an_obligation_requiring_no_code_evidence_never_reaches_the_coverage_stage(tmp_path):
    """The same filter from the other direction. Asking whether the change
    addresses something the change was never asked to contain produces a verdict
    about nothing."""
    capture = []
    _review(tmp_path, _judgments(checkout="tests_only"), capture=capture)

    coverage_calls = [c for c in capture if c["schema"] == "_Coverage"]
    assert coverage_calls, "the coverage stage was never called"
    for call in coverage_calls:
        assert "checkout-action" not in call["prompt"]
        assert "alpha" in call["prompt"]


def test_an_addressed_code_only_obligation_is_satisfied_not_unmeasured(tmp_path):
    """The verdict rule this issue settles, and a reversal of its own earlier
    answer. `Indeterminate` was right only while the tool could not tell "no test
    is owed here" from "we failed to judge this". Once the requirement is decided
    deliberately and recorded with a reason, nothing is outstanding — calling it
    unmeasured would claim a failure that did not occur."""
    review = _review(tmp_path, _judgments(checkout="code_only", alpha="code_only"))

    completion = review.completion
    assert completion is not None
    assert completion.verdict.value == "no_material_gaps"
    assert completion.escalation_candidates == []


def test_an_obligation_requiring_neither_kind_needs_review_this_cannot_give(tmp_path):
    """`neither` must never read as a pass. It says the repository cannot settle
    the obligation at all, which is a call for evidence the review has no way to
    gather — the §3.7 bound applied to the verdict itself.

    Both obligations are `neither` so the verdict is reading them and nothing
    else. With one ordinary obligation beside them the answer is `incomplete`,
    because a definite evidence gap outranks a call for other evidence — correct,
    unchanged, and covered in `test_verdict.py`, but it would mask this."""
    review = _review(tmp_path, _judgments(checkout="neither", alpha="neither"))

    completion = review.completion
    assert completion is not None
    assert completion.verdict.value == "needs_non_code_review"


def test_a_config_only_change_produces_a_report(tmp_path):
    """The original symptom, end to end. This raised out of the recommendation
    stage and `check` exited 1 with no report at all — a configuration-only
    change could not be reviewed."""
    review = _review(tmp_path, _judgments(checkout="code_only", alpha="code_only"))

    report = render_report(review)

    assert review.completion is not None
    assert "Obligations:" in report
    # Not merely "it did not raise": the obligations the abort used to destroy
    # are present, carrying the coverage judgement that had already been made.
    assert "the workflow pins actions/checkout at v5" in report
    assert [o.coverage_status for o in review.obligation_map] == ["addressed", "addressed"]


def test_the_report_says_test_evidence_is_not_required_and_why(mixed_review):
    report = render_report(mixed_review)

    assert "test evidence: not required" in report
    assert _PIN_REASON in report


def test_the_report_renders_that_differently_from_a_missing_test(mixed_review):
    """The distinction the report exists to draw, from the other side. An
    obligation that DOES require test evidence and has none renders
    `(no mapped test)`; only a narrowed one says "not required". Without this, a
    report printing the "not required" wording unconditionally would pass the
    test above."""
    report = render_report(mixed_review)

    assert "(no mapped test)" in report
    # And the two never describe the same obligation.
    for block in report.split("\n\n"):
        assert not ("not required" in block and "(no mapped test)" in block)


def test_two_runs_over_the_same_mandate_record_the_same_required_kinds(tmp_path):
    """The determinism invariant over the new field."""
    one, two = tmp_path / "one", tmp_path / "two"
    one.mkdir()
    two.mkdir()

    first = _review(one, _judgments())
    second = _review(two, _judgments())

    assert [
        (o.id, o.required_evidence, o.required_evidence_reason) for o in first.obligation_map
    ] == [(o.id, o.required_evidence, o.required_evidence_reason) for o in second.obligation_map]
