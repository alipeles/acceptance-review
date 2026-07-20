from acceptance.benchmark.case import (
    BenchmarkCase,
    BenchmarkCaseInputs,
    BenchmarkCaseSource,
    GroundTruthGap,
    GroundTruthLabels,
)
from acceptance.benchmark.runner import run_case
from acceptance.config import RunConfig
from acceptance.review_store import ReviewStore


def test_running_the_empty_skeleton_over_an_archetype_case_yields_an_all_miss_score(
    git_repo_elsewhere, tmp_path
):
    """M-B0.2 acceptance: running the empty skeleton over an archetype case
    yields a scored (all-miss) result without error."""
    case = BenchmarkCase(
        case_id="archetype-01-missed-obligation",
        source=BenchmarkCaseSource(kind="archetype", identifier="missed-obligation"),
        inputs=BenchmarkCaseInputs(
            repo=str(git_repo_elsewhere["path"]),
            task_text="## Deliverable\nAdd CSV export with active filters.\n",
            base_revision=git_repo_elsewhere["base"],
            head_revision=git_repo_elsewhere["head"],
        ),
        ground_truth=GroundTruthLabels(
            gaps=[GroundTruthGap(description="Active filters not applied", obligation_ref="filters")]
        ),
    )

    result = run_case(
        case,
        config=RunConfig(),
        review_store=ReviewStore(tmp_path / "reviews"),
    )

    assert result.reviewer_output is not None
    assert result.reviewer_output.reviewed_revision == git_repo_elsewhere["head"]
    assert result.score is not None
    assert result.score.gap_recall == 0.0  # all-miss: the skeleton found nothing
    assert result.score.gap_precision is None  # nothing reported to be right/wrong about


def test_run_case_does_not_mutate_the_input_case(git_repo_elsewhere, tmp_path):
    case = BenchmarkCase(
        case_id="archetype-01",
        source=BenchmarkCaseSource(kind="archetype", identifier="missed-obligation"),
        inputs=BenchmarkCaseInputs(
            repo=str(git_repo_elsewhere["path"]),
            task_text="## Deliverable\n...\n",
            base_revision=git_repo_elsewhere["base"],
            head_revision=git_repo_elsewhere["head"],
        ),
        ground_truth=GroundTruthLabels(gaps=[GroundTruthGap(description="x")]),
    )

    run_case(case, config=RunConfig(), review_store=ReviewStore(tmp_path / "reviews"))

    assert case.reviewer_output is None
    assert case.score is None
