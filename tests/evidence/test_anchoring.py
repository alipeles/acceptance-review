"""#292 acceptance: a re-judgement that alters a rating names the change it rests on.

The defect these guard against is #269's Gate 2, where one commit that added nine
tests and changed no source collapsed `strongly supported` from 37 obligations to
4. Nothing about those criteria had got worse; the judge was asked again and
answered differently. So a criterion whose inputs changed is re-judged with its
recorded rating and the specific changes that could justify moving it, and a
judgement that moves the rating without resting on one of them is rejected.

Every rejection here is provoked by a response that ignores the instruction it
was given, because that is the whole point: the prompt asks, and the code that
reads the answer is what enforces. A test whose double cooperated would pass
against an implementation that had no enforcement at all.
"""

from acceptance.evidence.anchoring import DependencyChange, RatingAnchor, build_anchors
from acceptance.evidence.discrimination import judge_discrimination
from acceptance.evidence.strength import classify_strength, hold_rejected_ratings
from acceptance.review_state import (
    ChangeSet,
    DiffHunk,
    FileChange,
    Obligation,
    ObligationType,
    Review,
    TestEvidence,
)
from acceptance.supplied_ids import UnusableAnswerLog
from tests.support import client_dispatching


def _obligation(obligation_id: str, description: str = "Prorate a partial month", **kwargs):
    return Obligation(
        id=obligation_id,
        description=description,
        type=ObligationType.FUNCTIONAL,
        importance="critical",
        explicit=True,
        observable_behavior="...",
        **kwargs,
    )


def _evidence(identifier: str, obligation_ids: list[str]) -> TestEvidence:
    return TestEvidence(
        identifier=identifier,
        location=identifier.split("::", 1)[0],
        assertions=["assert prorate(...) == 1"],
        mapped_obligations=obligation_ids,
    )


def _change_set(*paths: str) -> ChangeSet:
    hunk = DiffHunk(
        header="@@ -1 +1 @@",
        old_start=1,
        old_lines=1,
        new_start=1,
        new_lines=1,
        content="+def prorate(...): ...",
    )
    return ChangeSet(
        base_revision="b",
        head_revision="h",
        files=[
            FileChange(
                path=path,
                status="modified",
                category="test" if path.startswith("test") else "source",
                hunks=[hunk],
            )
            for path in paths
        ],
    )


def _prior(**obligation_kwargs) -> Review:
    return Review(
        mode="local",
        reviewed_revision="b",
        obligation_map=[_obligation("prorate", **obligation_kwargs)],
    )


def _anchor(*change_ids: str, stored_class: str = "strongly_supported") -> RatingAnchor:
    return RatingAnchor(
        obligation_id="prorate",
        stored_class=stored_class,
        changes=[DependencyChange(id=cid, description=f"{cid} changed") for cid in change_ids],
    )


def _judgement(*, caught: bool, rests_on: list[str]) -> dict:
    return {
        "_AnchoredDiscrimination": {
            "obligations": [
                {
                    "obligation_id": "prorate",
                    "defects": [
                        {
                            "description": "off-by-one on the final day",
                            "would_be_caught": caught,
                            "reason": "...",
                        }
                    ],
                    "rests_on": rests_on,
                }
            ]
        }
    }


def _judge(judgements, anchors, capture=None):
    """Run the stage over one criterion with one mapped test."""
    log = UnusableAnswerLog()
    obligations = [_obligation("prorate")]
    evidence = [_evidence("test_billing.py::test_prorates", ["prorate"])]
    discriminations = judge_discrimination(
        obligations,
        evidence,
        _change_set("test_billing.py"),
        client_dispatching(judgements, capture=capture),
        log,
        anchors,
    )
    return discriminations, log, obligations, evidence


# --- what the judgement is given -------------------------------------------


def _anchored_prompt() -> str:
    """The request text a judgement about one anchored criterion is sent."""
    capture: list = []
    _judge(
        _judgement(caught=True, rests_on=[]),
        {"prorate": _anchor("mapped-test-file:test_billing.py")},
        capture=capture,
    )
    anchored = [call for call in capture if call["schema"] == "_AnchoredDiscrimination"]
    assert len(anchored) == 1, "the anchored schema was not the one requested"
    return anchored[0]["prompt"]


def test_a_changed_criterion_is_given_the_rating_stored_for_it():
    """Acceptance: the stored rating reaches the judge — in the prompt, where the
    model reads it, not merely in the caller's variables."""
    assert "rating recorded by the earlier review: strongly_supported" in _anchored_prompt()


def test_a_changed_criterion_is_given_the_changes_to_its_dependencies():
    """Acceptance: and so do the changes it is allowed to rest on, each with the
    id it must cite to use it."""
    prompt = _anchored_prompt()

    assert "changes to this criterion's inputs since that rating:" in prompt
    assert "id=mapped-test-file:test_billing.py" in prompt


def test_a_review_with_no_stored_state_puts_no_stored_rating_in_the_request():
    """Acceptance: a first review is unanchored, and byte-for-byte unchanged.

    This is what keeps every existing recorded transcript replayable — the
    schema name is hashed into the request key, so an anchored schema on an
    unanchored call would orphan them all.
    """
    capture: list = []
    _judge(
        {
            "_Discrimination": {
                "obligations": [
                    {
                        "obligation_id": "prorate",
                        "defects": [
                            {"description": "d", "would_be_caught": True, "reason": "r"},
                        ],
                    }
                ]
            }
        },
        {},
        capture=capture,
    )

    assert [call["schema"] for call in capture] == ["_Discrimination"]
    prompt = capture[0]["prompt"]
    assert "rating recorded by the earlier review" not in prompt
    assert "rests_on" not in prompt


# --- accepting and rejecting a move ----------------------------------------


def test_a_move_that_names_a_supplied_change_is_accepted():
    """Acceptance: naming a change it was given, the judgement stands."""
    discriminations, log, obligations, evidence = _judge(
        # strongly_supported -> nominally_supported: the defect is now uncaught.
        _judgement(caught=False, rests_on=["mapped-test-file:test_billing.py"]),
        {"prorate": _anchor("mapped-test-file:test_billing.py")},
    )

    assert log.held_ratings == {}, "an accepted judgement must not hold the old rating"
    strengths = hold_rejected_ratings(
        classify_strength(obligations, evidence, discriminations), log.held_ratings
    )
    assert strengths[0].evidence_class == "nominally_supported"


def test_a_move_that_names_no_change_is_rejected_and_the_stored_rating_stands():
    """Acceptance: the rejection, and the rating that survives it.

    The response moves the rating and leaves `rests_on` empty — exactly what the
    prompt told it not to do. Nothing in the prompt can prevent that, which is
    why the check is in the reader.
    """
    discriminations, log, obligations, evidence = _judge(
        _judgement(caught=False, rests_on=[]),
        {"prorate": _anchor("mapped-test-file:test_billing.py")},
    )

    assert log.held_ratings == {"prorate": "strongly_supported"}
    strengths = hold_rejected_ratings(
        classify_strength(obligations, evidence, discriminations), log.held_ratings
    )
    assert strengths[0].evidence_class == "strongly_supported"


def test_a_move_resting_on_another_criterions_change_is_rejected():
    """The enum is the union of every change id supplied to the call, so a
    criterion can name a change belonging to a DIFFERENT criterion and still
    satisfy the schema. `constrain` cannot express "this criterion's ids only",
    so only the per-criterion check in the reader catches this.

    Both criteria are really in the batch, each with its own mapped test and its
    own change — otherwise the foreign id would never have been supplied at all
    and `scan` would reject it before the reader ever looked.
    """
    log = UnusableAnswerLog()
    obligations = [_obligation("prorate"), _obligation("tax", description="Apply local tax")]
    evidence = [
        _evidence("test_billing.py::test_prorates", ["prorate"]),
        _evidence("test_tax.py::test_taxes", ["tax"]),
    ]
    judgements = {
        "_AnchoredDiscrimination": {
            "obligations": [
                {
                    "obligation_id": "prorate",
                    # Moves the rating, resting on the change supplied for `tax`.
                    "defects": [{"description": "d", "would_be_caught": False, "reason": "r"}],
                    "rests_on": ["mapped-test-file:test_tax.py"],
                },
                {
                    "obligation_id": "tax",
                    "defects": [{"description": "d", "would_be_caught": True, "reason": "r"}],
                    "rests_on": [],
                },
            ]
        }
    }
    judge_discrimination(
        obligations,
        evidence,
        _change_set("test_billing.py", "test_tax.py"),
        client_dispatching(judgements),
        log,
        {
            "prorate": _anchor("mapped-test-file:test_billing.py"),
            "tax": RatingAnchor(
                obligation_id="tax",
                stored_class="strongly_supported",
                changes=[DependencyChange(id="mapped-test-file:test_tax.py", description="x")],
            ),
        },
    )

    # The id was supplied to the call, so it is not an unsupplied-id violation...
    assert [answer.returned_id for answer in log.answers] == ["prorate"]
    # ...it is a rating move resting on something that is not this criterion's.
    assert "a different criterion" in log.answers[0].reason
    assert log.held_ratings == {"prorate": "strongly_supported"}


def test_a_judgement_that_holds_the_rating_needs_no_justification():
    """An unchanged rating is not a move, so an empty `rests_on` is correct and
    must not be reported as a rejection."""
    _, log, _, _ = _judge(
        _judgement(caught=True, rests_on=[]),
        {"prorate": _anchor("mapped-test-file:test_billing.py")},
    )

    assert log.held_ratings == {}
    assert log.answers == []


def test_a_rejected_judgement_is_reported():
    """Acceptance: the rejection reaches the log the report renders from, and
    says enough to act on — which rating moved where, and what it could have
    rested on."""
    _, log, _, _ = _judge(
        _judgement(caught=False, rests_on=[]),
        {"prorate": _anchor("mapped-test-file:test_billing.py")},
    )

    assert len(log.answers) == 1
    answer = log.answers[0]
    assert answer.field == "rests_on"
    assert answer.returned_id == "prorate"
    assert "strongly_supported to nominally_supported" in answer.reason
    assert "mapped-test-file:test_billing.py" in answer.reason


# --- which criteria get anchored -------------------------------------------


def test_an_anchor_names_the_changed_files_this_criterion_depends_on():
    anchors = build_anchors(
        _prior(
            evidence_class="strongly_supported",
            test_evidence=["test_billing.py::test_prorates"],
            coverage_refs=["billing.py#@@ -1 +1 @@"],
        ),
        [_obligation("prorate")],
        _change_set("test_billing.py", "billing.py"),
    )

    assert [change.id for change in anchors["prorate"].changes] == [
        "mapped-test-file:test_billing.py",
        "implementation-file:billing.py",
    ]
    assert anchors["prorate"].stored_class == "strongly_supported"


def test_a_reworded_requirement_is_itself_a_nameable_change():
    anchors = build_anchors(
        _prior(description="Prorate a partial month", evidence_class="strongly_supported"),
        [_obligation("prorate", description="Prorate any partial billing period")],
        _change_set("unrelated.py"),
    )

    assert [change.id for change in anchors["prorate"].changes] == ["requirement-text"]


def test_a_criterion_with_no_nameable_change_is_not_anchored():
    """Anchoring it would freeze its rating: with no change to rest on, every
    move is rejected and no evidence could ever raise it again. Until #293 can
    compare test CONTENTS, a sub-file change is invisible here, so the criterion
    is left unanchored rather than held at a rating we cannot defend."""
    anchors = build_anchors(
        _prior(
            evidence_class="strongly_supported",
            test_evidence=["test_billing.py::test_prorates"],
        ),
        [_obligation("prorate")],
        _change_set("something_else.py"),
    )

    assert anchors == {}


def test_a_criterion_the_prior_review_never_rated_is_not_anchored():
    anchors = build_anchors(
        _prior(test_evidence=["test_billing.py::test_prorates"]),
        [_obligation("prorate")],
        _change_set("test_billing.py"),
    )

    assert anchors == {}


# --- the wiring ------------------------------------------------------------


_WIRING_TASK = "# Task\nProrate a partial month.\n\n## Constraints\n- Prorate a partial month\n"

_WIRING_JUDGEMENTS = {
    "_Decomposition": {
        "obligations": [
            {
                "id": "prorate",
                "description": "Prorate a partial month",
                "type": "functional",
                "importance": "critical",
                "explicit": True,
                "observable_behavior": "prorate(...) == 1",
                "source_quote": "Prorate a partial month",
            }
        ],
        "open_questions": [],
        "requirement_dispositions": [
            {
                "requirement_id": "task-01",
                "disposition": "no_obligation",
                "reason": "Restates the constraint below; imposes nothing of its own.",
            },
            {
                "requirement_id": "constraint-01",
                "disposition": "yielded",
                "obligation_id": "prorate",
                "more_obligation_ids": [],
            },
        ],
    },
    "_Mappings": {
        "mappings": [
            {
                "test_id": "test_billing.py::test_prorates",
                "obligation_ids": ["prorate"],
                "rationale": "Asserts the prorated amount.",
            }
        ]
    },
    # Moves the rating down and rests on nothing — the response the reader must
    # refuse, delivered through the real pipeline rather than a direct call.
    "_AnchoredDiscrimination": {
        "obligations": [
            {
                "obligation_id": "prorate",
                "defects": [{"description": "off by one", "would_be_caught": False, "reason": "r"}],
                "rests_on": [],
            }
        ]
    },
    "_Coverage": {
        "classifications": [
            {
                "obligation_id": "prorate",
                "status": "addressed",
                "rationale": "billing.py implements it.",
                "diff_refs": [],
            }
        ]
    },
}


def _wiring_repo(tmp_path):
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir(parents=True)

    def git(*args):
        subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)

    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    (repo / "billing.py").write_text("def prorate(days):\n    return days\n")
    (repo / "test_billing.py").write_text(
        "from billing import prorate\n\n\ndef test_prorates():\n    assert prorate(1) == 1\n"
    )
    git("add", "-A")
    git("commit", "-qm", "base")
    (repo / "test_billing.py").write_text(
        "from billing import prorate\n\n\ndef test_prorates():\n    assert prorate(2) == 2\n"
    )
    git("add", "-A")
    git("commit", "-qm", "head")
    return repo


def _wiring_review(tmp_path, client):
    from acceptance.change.diff import extract_change_set
    from acceptance.pipeline import run_review
    from acceptance.rerun import task_source_for

    repo = _wiring_repo(tmp_path)
    prior = Review(
        mode="local",
        reviewed_revision="HEAD~1",
        task_source=task_source_for(_WIRING_TASK, "task.md"),
        obligation_map=[
            _obligation(
                "prorate",
                evidence_class="strongly_supported",
                test_evidence=["test_billing.py::test_prorates"],
            )
        ],
    )
    return run_review(
        task_text=_WIRING_TASK,
        change_set=extract_change_set(repo, "HEAD~1", "HEAD"),
        repo=repo,
        client=client,
        reviewed_revision="HEAD",
        prior=prior,
    )


def test_the_pipeline_anchors_the_judgement_and_holds_the_rejected_rating(tmp_path):
    """Acceptance, as wiring: a helper the pipeline never calls is the hole this
    repo keeps finding, so the enforcement is driven end to end.

    The prior review rated `prorate` strongly supported; the head edits the file
    holding its mapped test, so it is anchored; the judge moves the rating and
    rests on nothing. The rating must survive, and the refusal must be reported.
    """
    capture: list = []
    review = _wiring_review(tmp_path, client_dispatching(_WIRING_JUDGEMENTS, capture=capture))

    assert any(call["schema"] == "_AnchoredDiscrimination" for call in capture), (
        "the pipeline did not build anchors, so nothing was enforced"
    )
    prorate = next(o for o in review.obligation_map if o.id == "prorate")
    assert prorate.evidence_class == "strongly_supported"
    assert any("rests_on" in (finding.description or "") for finding in review.findings), (
        "the rejection did not reach the report"
    )


def test_two_anchored_runs_over_the_same_input_are_byte_identical(tmp_path):
    """Acceptance: the anchored path keeps M0.5. The enum is built from a set, so
    an unsorted one would make the request — and the review — differ between two
    runs over identical inputs."""
    first = _wiring_review(tmp_path / "a", client_dispatching(_WIRING_JUDGEMENTS))
    second = _wiring_review(tmp_path / "b", client_dispatching(_WIRING_JUDGEMENTS))

    assert first.to_canonical_json() == second.to_canonical_json()


def test_anchoring_without_a_log_is_refused():
    """A rejection that cannot be reported is a suppressed one, so the stage
    refuses the combination rather than enforcing silently."""
    import pytest

    with pytest.raises(ValueError, match="cannot be reported"):
        judge_discrimination(
            [_obligation("prorate")],
            [_evidence("test_billing.py::test_prorates", ["prorate"])],
            _change_set("test_billing.py"),
            client_dispatching(_judgement(caught=False, rests_on=[])),
            None,
            {"prorate": _anchor("mapped-test-file:test_billing.py")},
        )
