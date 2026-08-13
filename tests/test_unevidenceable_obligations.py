"""#266: a weak obligation no test can evidence is answered, not fatal.

The stage-level contract lives in `tests/coverage/test_recommendations.py`.
These are the wiring tests — that the refusal reaches review state, moves the
obligation onto the §9.3 `indeterminate` evidence axis, renders distinguishably,
and lets a review that can prescribe nothing at all still produce a report.

Defect injection has repeatedly found a well-tested helper the pipeline never
calls (CLAUDE.md), and this change adds two: the refusal has to survive
`recommend_tests` AND be applied to the obligations AND be persisted AND be
rendered. Every one of those is asserted through `run_review`, not against the
helper.
"""

import subprocess

import pytest

from acceptance.change.diff import extract_change_set
from acceptance.pipeline import run_review
from acceptance.report import render_report
from acceptance.review_state import Review
from tests.support import client_dispatching

_TASK = (
    "# Task\nThe build is clean.\n\n"
    "## Constraints\n"
    "- The checkout action is not on a Node 20 major version\n"
    "- Alpha behaves\n"
)

_REASON = "a property of the workflow file's action pin, which no pytest observes"


def _judgments(*, decline: list[str], recommend: list[str]) -> dict:
    """A full pipeline response set with the recommendation stage's answer
    parameterised, so each test states only the part it is about."""
    return {
        "_Decomposition": {
            "obligations": [
                {
                    "id": "checkout-action",
                    "description": "The checkout action is not on a Node 20 major version",
                    "type": "functional",
                    "importance": "critical",
                    "explicit": True,
                    "observable_behavior": "the workflow pins actions/checkout at v5",
                    "source_quote": "The checkout action is not on a Node 20 major version",
                },
                {
                    "id": "alpha",
                    "description": "Alpha behaves",
                    "type": "functional",
                    "importance": "critical",
                    "explicit": True,
                    "observable_behavior": "alpha() == 1",
                    "source_quote": "Alpha behaves",
                },
            ],
            "open_questions": [],
            "requirement_dispositions": [],
        },
        "_Mappings": {"mappings": []},
        "_Discrimination": {"discriminations": []},
        # Both obligations are ADDRESSED — the code is there and the coverage
        # stage says so. That is the whole point: the evidence axis is what has
        # no instrument, and #266's abort threw this classification away too.
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
        "_Recommendations": {
            "recommendations": [
                {
                    "obligation_id": obligation_id,
                    "required_inputs": "a month whose length is not 30",
                    "boundary_conditions": "none",
                    "expected_output": "the criterion holds",
                    "required_assertions": ["asserts the criterion"],
                    "plausible_defect": "the criterion is not met",
                    "repo_conventions": "test_alpha.py",
                }
                for obligation_id in recommend
            ],
            "unevidenceable": [
                {"obligation_id": obligation_id, "reason": _REASON} for obligation_id in decline
            ],
        },
        "_Mismatches": {"mismatches": []},
    }


def _repo_with_a_config_only_change(tmp_path):
    """A change touching only configuration — the shape from
    `dogfood-logs/261-gate2-run1/`, where the abort was first seen. No source
    file moves, so there is nothing a test could be pointed at."""

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
    (tmp_path / "alpha.py").write_text("def alpha():\n    return 1\n")
    git("add", "-A")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    (workflow / "ci.yml").write_text(
        "jobs:\n  test:\n    steps:\n      - uses: actions/checkout@v5\n"
    )
    git("add", "-A")
    git("commit", "-qm", "head")
    return base, git("rev-parse", "HEAD")


def _review(tmp_path, judgments) -> Review:
    base, head = _repo_with_a_config_only_change(tmp_path)
    return run_review(
        task_text=_TASK,
        change_set=extract_change_set(tmp_path, base, head),
        repo=tmp_path,
        client=client_dispatching(judgments),
        reviewed_revision=head,
    )


@pytest.fixture
def mixed_review(tmp_path) -> Review:
    """One obligation declined, one recommended — so every assertion about the
    declined one has a control sitting beside it in the same report."""
    return _review(tmp_path, _judgments(decline=["checkout-action"], recommend=["alpha"]))


def test_a_config_only_change_produces_a_report(tmp_path):
    """#266's headline acceptance, end to end. Before the fix this raised out of
    the recommendation stage and `check` exited 1 with no report at all — a
    configuration-only change could not be reviewed."""
    review = _review(tmp_path, _judgments(decline=["checkout-action", "alpha"], recommend=[]))

    report = render_report(review)

    assert review.completion is not None
    assert "Obligations:" in report
    # Not merely "it did not raise": the obligations the abort used to destroy
    # are present, with the coverage judgement that had already been made.
    assert "The checkout action is not on a Node 20 major version" in report
    assert [o.coverage_status for o in review.obligation_map] == ["addressed", "addressed"]


def test_the_refusal_reaches_review_state_attributed_to_its_obligation(mixed_review):
    """Recorded, not dropped. An unrecorded refusal would leave the obligation's
    `indeterminate` rating with nothing behind it — the reader could see that
    the review gave up, but not why, which is the state #266 was diagnosed in."""
    assert [entry.obligation_id for entry in mixed_review.unevidenceable] == ["checkout-action"]
    entry = mixed_review.unevidenceable[0]
    assert entry.reason == _REASON
    assert entry.criterion == "the workflow pins actions/checkout at v5"


def test_the_refusal_survives_persistence(mixed_review):
    """Review state is the interchange format between runs (§12), so a refusal
    that only exists in memory is one a re-run silently loses."""
    restored = Review.from_dict(mixed_review.to_dict())

    assert [e.to_dict() for e in restored.unevidenceable] == [
        e.to_dict() for e in mixed_review.unevidenceable
    ]


def test_a_declined_obligation_is_indeterminate_on_the_evidence_axis(mixed_review):
    """The design decision #266 settles. `addressed` on the coverage axis and
    `indeterminate` on the evidence axis — neither satisfied nor a gap, because
    the instrument the evidence axis measures with does not apply."""
    by_id = {o.id: o for o in mixed_review.obligation_map}

    assert by_id["checkout-action"].coverage_status == "addressed"
    assert by_id["checkout-action"].evidence_class == "indeterminate"
    # The control: the obligation that got a real recommendation keeps the weak
    # rating that earned it one. The reclassification is targeted, not blanket.
    assert by_id["alpha"].evidence_class != "indeterminate"


def test_a_declined_obligation_is_an_escalation_candidate(mixed_review):
    """`indeterminate` must not read as success. A refusal says part of the
    mandate could not be measured, and §3.7 bounds what a positive verdict may
    claim — so the obligation is listed as needing a higher tier, not passed."""
    completion = mixed_review.completion

    assert completion is not None
    assert completion.verdict.value != "no_material_gaps"
    assert "checkout-action" in completion.escalation_candidates
    # The control: the obligation with a real recommendation is a GAP, not an
    # escalation candidate. The two axes must not blur into each other.
    assert "alpha" not in completion.escalation_candidates


def test_a_review_of_only_declined_obligations_is_unable_to_determine(tmp_path):
    """The verdict rule this issue settles, isolated. Every obligation addressed
    and every one unevidenceable: not `no_material_gaps`, because no test tier
    was achievable, and not `incomplete`, because nothing is missing.

    Isolated deliberately. In `mixed_review` the verdict is `incomplete` — the
    recommended obligation is a real evidence gap, and a definite gap outranks
    uncertainty. That precedence is correct and unchanged here; asserting the
    rule against that fixture would have been asserting the wrong stage."""
    review = _review(tmp_path, _judgments(decline=["checkout-action", "alpha"], recommend=[]))

    completion = review.completion

    assert completion is not None
    assert completion.verdict.value == "unable_to_determine"
    assert sorted(completion.escalation_candidates) == ["alpha", "checkout-action"]


def test_the_report_says_no_test_can_evidence_the_criterion(mixed_review):
    report = render_report(mixed_review)

    assert "no test can evidence this criterion" in report
    assert _REASON in report


def test_the_report_says_no_such_thing_for_an_obligation_that_merely_lacks_one(tmp_path):
    """The distinction the report exists to draw, asserted from the other side.
    A weak obligation with no recommendation renders `(no mapped test)`; only a
    declined one earns the refusal line. Without this, a report that printed the
    refusal wording unconditionally would pass the test above."""
    review = _review(tmp_path, _judgments(decline=[], recommend=["checkout-action", "alpha"]))

    report = render_report(review)

    assert "no test can evidence this criterion" not in report
    assert "(no mapped test)" in report


def test_two_runs_over_the_same_change_produce_byte_identical_state(tmp_path):
    """The determinism invariant, over the new field. Two runs, two repos built
    the same way — the refusal must not carry ordering or identity from the
    response into the persisted form."""
    one, two = tmp_path / "one", tmp_path / "two"
    one.mkdir()
    two.mkdir()
    first = _review(one, _judgments(decline=["checkout-action"], recommend=["alpha"]))
    second = _review(two, _judgments(decline=["checkout-action"], recommend=["alpha"]))

    assert [e.to_dict() for e in first.unevidenceable] == [
        e.to_dict() for e in second.unevidenceable
    ]
