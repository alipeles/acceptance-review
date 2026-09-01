"""#275: a criterion the recommendation stage returns nothing for costs one
prescription, not the whole review.

The stage-level contract lives beside the stage
(`tests/coverage/test_recommendations.py`). These are the wiring tests. The
defect they pin was not in `recommend_tests`' judgement but in what the pipeline
did with it: `SchemaValidationError` from one stage, with no handler anywhere on
the path, threw away a completed decomposition, mapping, discrimination and
coverage classification — twelve honoured prescriptions among them — to report
that a thirteenth was missing.

So every assertion here runs through `run_review`, and the ones about the
evidence axis check the obligation the verdict actually reads, not the log entry
the stage wrote.
"""

import subprocess

import pytest

from acceptance.change.diff import extract_change_set
from acceptance.pipeline import run_review
from acceptance.recommendation import lookup, render_json, render_text
from acceptance.report import render_report
from acceptance.review_state import Review, UnobtainedRecommendation
from tests.support import client_dispatching

_TASK = (
    "# Task\nThe build is clean.\n\n"
    "## Constraints\n"
    "- The checkout action is not on a Node 20 major version\n"
    "- Alpha behaves\n"
    "- Beta behaves\n"
    "- Gamma behaves\n"
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


def _defect_id(obligation_id: str) -> str:
    """The one enumerated defect each criterion gets below.

    Composed the way `enumeration.py` composes it — `<obligation id>/<slug>` —
    so a test can name the prescription it expects without reading it back off
    the review.
    """
    return f"{obligation_id}/returns-a-constant"


def _prescription(obligation_id: str) -> dict:
    return {
        "defect_id": _defect_id(obligation_id),
        "required_inputs": "an input where a correct and a defective implementation differ",
        "boundary_conditions": "the empty case and the maximum",
        "expected_output": "the discriminating result",
        "required_assertions": ["assert beta() == 1"],
        "repo_conventions": "test_alpha.py",
    }


def _judgments(recommendations: list[dict]) -> dict:
    """A full pipeline response set over three obligations.

    `checkout-action` requires code alone (#266), so no test is owed for it and
    it never reaches the recommendation stage at all. `alpha` and `beta` both
    require tests and neither is mapped to one, so both are weak and both are
    supplied to the stage — which lets one response answer for one of them and
    stay silent about the other, the shape the whole issue is about.
    """
    return {
        "_Decomposition": {
            "obligations": [
                _obligation(
                    "checkout-action",
                    "the workflow pins actions/checkout at v5",
                    "code_only",
                    _PIN_REASON,
                ),
                _obligation("alpha", "alpha() returns 1", "code_and_tests", ""),
                _obligation("beta", "beta() returns 1", "code_and_tests", ""),
                _obligation("gamma", "gamma() returns 1", "code_and_tests", ""),
            ],
            "open_questions": [],
            "requirement_dispositions": [],
        },
        # One enumerated way to fail per criterion, and no pair verdict killing
        # it, so every criterion that requires tests carries one uncovered
        # defect — which is what reaches the recommendation stage since #316.
        # `obligation_id` is filled per call by the double, because the
        # enumerator answers for one criterion at a time.
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
                for obligation_id in ("checkout-action", "alpha", "beta", "gamma")
            ]
        },
        "_Detections": {"unrequested_changes": []},
        "_Judgments": {"resolutions": []},
        "_Recommendations": {"recommendations": recommendations},
        "_Mismatches": {"mismatches": []},
    }


def _build_repo(tmp_path):
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
    (tmp_path / "alpha.py").write_text("def alpha():\n    return 1\n")
    git("add", "-A")
    git("commit", "-qm", "head")
    return base, git("rev-parse", "HEAD")


def _review(tmp_path, recommendations: list[dict]) -> Review:
    base, head = _build_repo(tmp_path)
    return run_review(
        task_text=_TASK,
        change_set=extract_change_set(tmp_path, base, head),
        repo=tmp_path,
        client=client_dispatching(_judgments(recommendations)),
        reviewed_revision=head,
    )


@pytest.fixture
def partial_review(tmp_path) -> Review:
    """The real shape from `dogfood-logs/258-gate2-run2/`, at four obligations
    instead of thirteen: the stage answers for two weak criteria and says
    nothing about a third.

    Two answered rather than one, deliberately. With a single answer, "the
    prescriptions that came back survive" and "one prescription survives" are
    the same assertion, and the failure that started this — twelve answers
    discarded to report a missing thirteenth — is about the plural."""
    return _review(tmp_path, [_prescription("beta"), _prescription("gamma")])


def test_an_omitted_criterion_still_produces_a_review(partial_review):
    """The defect, stated at its coarsest. `run_review` used to raise
    `SchemaValidationError` from inside the recommendation stage, so there was
    no review at all — no verdict, no findings, and no report to read them in."""
    assert partial_review.completion is not None


def test_the_answered_criterion_keeps_its_prescription(partial_review):
    """What aborting cost. On the run this issue was filed from, twelve
    prescriptions were discarded to report that a thirteenth was missing."""
    assert sorted(r.obligation_id for r in partial_review.recommendations) == ["beta", "gamma"]
    # Whole prescriptions, not just their ids: an entry that survived with its
    # §9.5 fields emptied would satisfy the id check and be useless to an agent.
    for prescription in partial_review.recommendations:
        assert prescription.required_assertions
        assert prescription.plausible_defect
        assert prescription.required_inputs


def test_the_omitted_criterion_is_recorded_as_not_obtained(partial_review):
    """Present as a positive record, not as an absence — the "always" half of
    #271's invariant, which the abort was the wrong price for."""
    assert [u.obligation_id for u in partial_review.unobtained_recommendations] == ["alpha"]
    unobtained = partial_review.unobtained_recommendations[0]
    assert unobtained.criterion == "alpha() returns 1"
    assert "no prescription was produced" in unobtained.reason


def test_a_criterion_owed_no_test_is_not_recorded_as_not_obtained(partial_review):
    """The distinction the record exists to carry. `checkout-action` requires
    code evidence alone (#266), so no prescription is owed and none is missing;
    recording it here would turn a settled answer into an open one."""
    assert "checkout-action" not in {
        u.obligation_id for u in partial_review.unobtained_recommendations
    }


def test_the_omitted_criterion_is_left_indeterminate_on_the_evidence_axis(partial_review):
    """Not `unsupported`, which is a substantive claim about its tests, and not
    the rating the strength classifier assigned before the stage ran."""
    alpha = next(o for o in partial_review.obligation_map if o.id == "alpha")

    assert alpha.evidence_class == "indeterminate"


def test_a_review_missing_a_prescription_does_not_come_back_clean(partial_review):
    """The gate stays red, and says which criterion it is uncertain about.

    Without the second `_apply_indeterminate` pass in the pipeline, this is the
    assertion that fails: the mark is made after the first pass has already run,
    so the verdict would read the strength classifier's rating and could return
    a clean result over a prescription nobody obtained."""
    assert partial_review.completion is not None
    assert partial_review.completion.verdict.value != "no_material_gaps"
    assert "alpha" in partial_review.completion.escalation_candidates


def test_the_report_says_the_prescription_was_not_obtained(partial_review):
    report = render_report(partial_review)

    assert "NOT OBTAINED" in report
    assert "no prescription was produced" in report


def test_the_report_renders_that_differently_from_a_criterion_owed_no_test(partial_review):
    """Two lines that must never read alike: "we decided you need no test here",
    with the reason #266 recorded, and "a test is owed and we did not find out
    which"."""
    report = render_report(partial_review)
    blocks = {
        line.strip()
        for line in report.splitlines()
        if "NOT OBTAINED" in line or "not required" in line
    }

    not_obtained = [line for line in blocks if "NOT OBTAINED" in line]
    not_required = [line for line in blocks if "not required" in line]
    assert not_obtained and not_required
    assert not_obtained != not_required
    # And the no-test-owed line still carries the reason that justifies it.
    assert _PIN_REASON in report


def test_the_not_obtained_record_survives_persistence(partial_review):
    """Review state is the interchange format between runs (§12); a record that
    exists only in memory is one a re-run silently loses."""
    restored = Review.from_dict(partial_review.to_dict())

    assert [u.to_dict() for u in restored.unobtained_recommendations] == [
        u.to_dict() for u in partial_review.unobtained_recommendations
    ]


def test_two_runs_over_the_same_inputs_render_the_same_report(tmp_path, tmp_path_factory):
    """M0.5: two recorded runs over one input are byte-identical, and the new
    path must not be where that stops being true."""
    # Two prescriptions alongside the omission, not one: with a single entry
    # every ordering is the same ordering, so nothing about the report's
    # stability is being asserted.
    first = _review(tmp_path, [_prescription("gamma"), _prescription("beta")])
    second = _review(
        tmp_path_factory.mktemp("second"), [_prescription("gamma"), _prescription("beta")]
    )

    def _without_revisions(report: str) -> str:
        return "\n".join(line for line in report.splitlines() if "revision" not in line.lower())

    assert _without_revisions(render_report(first)) == _without_revisions(render_report(second))


# --- on-demand retrieval (`acceptance recommendation --criterion`) ---


def _unobtained() -> UnobtainedRecommendation:
    return UnobtainedRecommendation(
        obligation_id="alpha",
        defect_id=_defect_id("alpha"),
        criterion="alpha() returns 1",
        reason="the recommendation stage was given 2 uncovered defect(s) and returned 1",
    )


def test_retrieval_returns_the_not_obtained_record_rather_than_nothing():
    """The retrieval path has the same three-way distinction to keep as the
    report. Returning None here would tell an agent that came for the
    prescription that none is owed."""
    review = Review(
        mode="local", reviewed_revision="abc123", unobtained_recommendations=[_unobtained()]
    )

    assert lookup(review, "alpha") == _unobtained()
    # A criterion nobody asked about is still an ordinary None.
    assert lookup(review, "gamma") is None


def test_retrieval_renders_not_obtained_distinctly_in_both_formats():
    rendered_text = render_text(_unobtained())
    rendered_json = render_json(_unobtained())

    assert "NOT OBTAINED" in rendered_text
    assert rendered_text != render_text(None)
    # Not an empty prescription: a consumer filling §9.5's fields with blanks
    # would write a test against no inputs and believe it had followed one.
    assert '"status":"not_obtained"' in rendered_json.replace(" ", "")
    assert "required_assertions" not in rendered_json
