import pytest

from acceptance.benchmark.case import (
    BenchmarkCase,
    BenchmarkCaseInputs,
    BenchmarkCaseSource,
    EmptyRequirementRegistryError,
    GroundTruthGap,
    GroundTruthLabels,
    GroundTruthObligation,
)
from acceptance.benchmark.runner import run_case
from acceptance.config import RunConfig
from acceptance.review_store import ReviewStore
from tests.support import client_dispatching, client_finding_nothing

# A mandate `parse_task_file` reads: `# Task` is a heading it recognises, so the
# paragraph under it becomes a requirement. `## Deliverable` is not one, and a
# case headed that way scores all-miss whatever the checker does (#243).
_TASK_TEXT = (
    "# Task\nAdd CSV export.\n\n## Constraints\n- Apply the active filters to the export.\n"
)

_FILTERS = "Active filters are applied to the export"


def _labels() -> GroundTruthLabels:
    return GroundTruthLabels(
        obligations=[
            GroundTruthObligation(
                id="filters",
                description=_FILTERS,
                explicit=True,
                evidence_class="unsupported",
                evidence_rationale="No test exercises filtering.",
            )
        ],
        gaps=[
            GroundTruthGap(
                id="gap-filters",
                description="Active filters not applied",
                obligation_id="filters",
            )
        ],
    )


def _case(repo: dict, task_text: str = _TASK_TEXT) -> BenchmarkCase:
    return BenchmarkCase(
        case_id="archetype-01-missed-obligation",
        source=BenchmarkCaseSource(kind="archetype", identifier="missed-obligation"),
        inputs=BenchmarkCaseInputs(
            repo=str(repo["path"]),
            task_text=task_text,
            base_revision=repo["base"],
            head_revision=repo["head"],
        ),
        ground_truth=_labels(),
    )


def _client_finding_the_labelled_gap():
    """A checker that derives the labelled obligation and finds no code for it —
    the gap the ground truth labels, reported."""
    return client_dispatching(
        {
            "_Decomposition": {
                "obligations": [
                    {
                        "id": "filters",
                        "description": _FILTERS,
                        "type": "functional",
                        "importance": "critical",
                        "explicit": True,
                        "observable_behavior": "the export holds only filtered rows",
                        "source_quote": "Apply the active filters to the export",
                    }
                ],
                "open_questions": [],
                "requirement_dispositions": [],
            },
            "_Coverage": {
                "classifications": [
                    {
                        "obligation_id": "filters",
                        "status": "not_addressed",
                        "rationale": "no code applies the filters",
                        "diff_refs": [],
                    }
                ]
            },
        }
    )


def test_running_the_empty_skeleton_over_an_archetype_case_yields_an_all_miss_score(
    git_repo_elsewhere, tmp_path
):
    """M-B0.2 acceptance: running the empty skeleton over an archetype case
    yields a scored (all-miss) result without error."""
    result = run_case(
        _case(git_repo_elsewhere),
        config=RunConfig(),
        review_store=ReviewStore(tmp_path / "reviews"),
        client=client_finding_nothing(),
    )

    assert result.reviewer_output is not None
    assert result.reviewer_output.reviewed_revision == git_repo_elsewhere["head"]
    assert result.score is not None
    assert result.score.gap_recall == 0.0  # all-miss: the skeleton found nothing
    assert result.score.gap_precision is None  # nothing reported to be right/wrong about


def test_the_all_miss_score_depends_on_the_checker_not_the_input(git_repo_elsewhere, tmp_path):
    """The companion to the acceptance test: the same case, run through a
    checker that reports the labelled gap, scores it found. Without this the
    all-miss assertion above could hold because of the input alone (#243)."""
    result = run_case(
        _case(git_repo_elsewhere),
        config=RunConfig(),
        review_store=ReviewStore(tmp_path / "reviews"),
        client=_client_finding_the_labelled_gap(),
    )

    assert result.score is not None
    assert result.score.gap_recall == 1.0


def test_run_case_refuses_a_task_file_that_yields_no_requirements(git_repo_elsewhere, tmp_path):
    """`## Deliverable` is not a heading `parse_task_file` recognises, so the
    case has nothing to decompose. That is the absence of a run, not a score of
    zero, and the runner refuses it as the corpus case builders do (#228)."""
    case = _case(
        git_repo_elsewhere,
        task_text="## Deliverable\nAdd CSV export with active filters.\n",
    )
    store = ReviewStore(tmp_path / "reviews")

    with pytest.raises(EmptyRequirementRegistryError, match="archetype-01-missed-obligation"):
        run_case(case, config=RunConfig(), review_store=store, client=client_finding_nothing())

    assert not (tmp_path / "reviews").exists() or not any((tmp_path / "reviews").iterdir())


def test_run_case_does_not_mutate_the_input_case(git_repo_elsewhere, tmp_path):
    case = _case(git_repo_elsewhere)

    run_case(
        case,
        config=RunConfig(),
        review_store=ReviewStore(tmp_path / "reviews"),
        client=client_finding_nothing(),
    )

    assert case.reviewer_output is None
    assert case.score is None
