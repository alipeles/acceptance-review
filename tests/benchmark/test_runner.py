from acceptance.benchmark.case import (
    BenchmarkCase,
    BenchmarkCaseInputs,
    BenchmarkCaseSource,
    GroundTruthGap,
    GroundTruthLabels,
    GroundTruthObligation,
)
from acceptance.benchmark.runner import run_case
from acceptance.config import RunConfig
from acceptance.review_store import ReviewStore
from tests.support import client_finding_nothing


def _labels() -> GroundTruthLabels:
    return GroundTruthLabels(
        obligations=[
            GroundTruthObligation(
                id="filters",
                description="Active filters are applied to the export",
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
        ground_truth=_labels(),
    )

    result = run_case(
        case,
        config=RunConfig(),
        review_store=ReviewStore(tmp_path / "reviews"),
        client=client_finding_nothing(),
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
        ground_truth=_labels(),
    )

    run_case(
        case,
        config=RunConfig(),
        review_store=ReviewStore(tmp_path / "reviews"),
        client=client_finding_nothing(),
    )

    assert case.reviewer_output is None
    assert case.score is None
