"""The pipeline actually feeds the verdict its mandate coverage (#214).

Separate from `test_mandate_coverage.py` deliberately. Those tests call
`assess_mandate_coverage` and `derive_obligations` directly, and every one of
them would still pass if `run_review` never called either — which is the exact
shape of hole defect injection keeps finding here: a well-tested helper the
pipeline does not use. These two tests fail if the wiring is removed.
"""

from __future__ import annotations

import subprocess

from acceptance.change.diff import extract_change_set
from acceptance.coverage.open_questions import derived_obligation_id
from acceptance.pipeline import run_review
from tests.support import client_dispatching

_TASK = (
    "# Task\nThe formatter handles negative amounts.\n\n"
    "## Constraints\n- Negative amounts are formatted\n- Amounts round somehow\n"
)

_JUDGMENTS = {
    "_Decomposition": {
        "obligations": [
            {
                "id": "formats-negatives",
                "description": "Negative amounts are formatted",
                "type": "functional",
                "importance": "critical",
                "explicit": True,
                "observable_behavior": "format(-1) is defined",
                "source_quote": "Negative amounts are formatted",
            }
        ],
        "open_questions": [
            {
                "id": "q-rounding",
                "question": "Round half up or half even?",
                "importance": "normal",
                "source_quote": "Amounts round somehow",
            }
        ],
        "requirement_dispositions": [
            {
                "requirement_id": "task-01",
                "disposition": "no_obligation",
                "reason": "Restates the constraints below; imposes nothing of its own.",
            },
            {
                "requirement_id": "constraint-01",
                "disposition": "yielded",
                "obligation_id": "formats-negatives",
                "more_obligation_ids": [],
            },
            {
                "requirement_id": "constraint-02",
                "disposition": "open_question",
                "open_question_id": "q-rounding",
                "more_open_question_ids": [],
            },
        ],
    },
    "_Mappings": {"mappings": []},
    "_Coverage": {
        "classifications": [
            {
                "obligation_id": "formats-negatives",
                "status": "addressed",
                "rationale": "money.py implements it.",
                "diff_refs": [],
            }
        ]
    },
    "_Detections": {"unrequested_changes": []},
    "_Judgments": {
        "resolutions": [
            {
                "question_id": "q-rounding",
                "resolved": True,
                "rationale": "The diff rounds half to even.",
                "diff_refs": ["money.py#0"],
                "implemented_behavior": "Amounts round half to even.",
            }
        ]
    },
    "_Recommendations": {"recommendations": []},
    "_Mismatches": {"mismatches": []},
}


def _git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


def _repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "money.py").write_text("def fmt(x):\n    return str(x)\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "money.py").write_text("def fmt(x):\n    return f'{round(x, 2)}'\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head")
    return repo, base, _git(repo, "rev-parse", "HEAD")


def _review(tmp_path):
    repo, base, head = _repo(tmp_path)
    return run_review(
        task_text=_TASK,
        change_set=extract_change_set(repo, base, head),
        repo=repo,
        client=client_dispatching(_JUDGMENTS),
        reviewed_revision=head,
    )


def test_the_verdict_is_derived_with_each_requirements_disposition_in_hand(tmp_path):
    """Acceptance: by the same path a review run takes.

    `derive_verdict` took three arguments and none of them carried the
    requirement map, so mandate coverage could not reach it. Passing the map is
    the fix; this asserts the pipeline does it, not merely that it can be done.
    """
    review = _review(tmp_path)

    coverage = review.completion.mandate_coverage
    assert coverage is not None, "the pipeline derived the verdict without the requirement map"
    assert coverage.total_requirements == 3
    # The `task` paragraph was declined with a reason, and is taken at face
    # value rather than counted against coverage.
    assert coverage.declined_requirements == ["task-01"]


def test_two_runs_over_identical_task_text_produce_byte_identical_review_state(tmp_path):
    """Two runs, byte-identical review state — over the real pipeline.

    The determinism this change could plausibly break is its own: a derived
    obligation is minted during the run rather than parsed from the task, so an
    id from a counter or a uuid, or an obligation order taken from the `set` the
    pipeline uses to hold derived ids out of coverage classification, would each
    diverge between runs while every other test here still passed.

    Compared as canonical JSON, which is what "byte-identical review state"
    means — `tests/test_determinism.py` covers the separate claim that
    determinism survives a *drifting provider* via transcript reuse.
    """
    repo, base, head = _repo(tmp_path)
    change_set = extract_change_set(repo, base, head)

    def once():
        return run_review(
            task_text=_TASK,
            change_set=change_set,
            repo=repo,
            client=client_dispatching(_JUDGMENTS),
            reviewed_revision=head,
        ).to_canonical_json()

    assert once() == once()


def test_a_resolved_questions_obligation_reaches_the_obligation_map(tmp_path):
    """The derived obligation must be a first-class member of the review, not a
    thing `derive_obligations` can produce in isolation. If the pipeline drops
    it, an implementation choice that settled an ambiguity is once again
    invisible to every downstream stage."""
    review = _review(tmp_path)

    derived = next(
        (o for o in review.obligation_map if o.id == derived_obligation_id("q-rounding")),
        None,
    )
    assert derived is not None, "the pipeline never derived the resolved question's obligation"
    assert derived.description == "Amounts round half to even."
    # Addressed by construction, citing what resolved it -- never a coverage gap.
    # The cited label is resolved to a real hunk, as every other code ref is, so
    # the citation points at the change rather than at a prompt-local index.
    assert derived.coverage_status == "addressed"
    assert derived.coverage_refs == ["money.py#@@ -1,2 +1,2 @@"]
    # And the requirement that raised the question now counts as judged.
    assert review.completion.mandate_coverage.unjudged_requirements == []
