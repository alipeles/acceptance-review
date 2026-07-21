"""M-B5a.2 acceptance: each archetype has a valid labeled BenchmarkCase whose
ground truth is an obligation tree — each obligation carrying its candidate
tests, evidence strength, and the reason for that strength — plus the expected
gap(s).

The label *correctness* is a human-review gate (`[human]` on the issue); these
tests establish that every case is present, well-formed, internally consistent
(every reference resolves, every obligation has an evidence class and a
rationale), that the candidate_tests ids name real tests in the fixture, and
that the full fixture -> labeled case -> run -> score loop works against the
(no-op) checker.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from acceptance.benchmark.case import BenchmarkCase, GroundTruthLabels
from acceptance.benchmark.fixtures import build_benchmark_case, load_labels, materialize_archetype
from acceptance.benchmark.runner import run_case
from acceptance.benchmark.scoring import score_case_set
from acceptance.config import RunConfig
from acceptance.review_store import ReviewStore

ARCHETYPES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "archetypes"
FIXTURE_DIRS = sorted(p for p in ARCHETYPES_DIR.iterdir() if p.is_dir())


@pytest.fixture(params=FIXTURE_DIRS, ids=lambda p: p.name)
def fixture_dir(request):
    return request.param


def _collected_test_ids(repo: Path) -> set[str]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    # Lines look like "test_receipt.py::test_positive_line"; a trailing summary
    # line ("2 tests collected in ...") is filtered out by the "::" check.
    return {line.strip() for line in result.stdout.splitlines() if "::" in line}


def test_every_fixture_has_labels(fixture_dir):
    assert (fixture_dir / "labels.json").is_file()
    labels = load_labels(fixture_dir)
    assert isinstance(labels, GroundTruthLabels)
    assert labels.obligations, "each fixture must label its obligation decomposition"


def test_every_obligation_has_an_evidence_class_and_rationale(fixture_dir):
    # Structural in the schema (both are required), asserted here as the
    # completeness guarantee the labels must meet: no result without a reason.
    labels = load_labels(fixture_dir)
    for obligation in labels.obligations:
        assert obligation.evidence_class
        assert obligation.evidence_rationale.strip()


def test_non_strong_obligations_are_each_flagged_by_a_gap(fixture_dir):
    """Anything short of strongly_supported is a deficiency that weighs against
    acceptance — a partial/nominal/unsupported obligation can only be accepted
    with a caveat, so each must be raised as a gap. Only strongly_supported
    obligations may go unflagged."""
    labels = load_labels(fixture_dir)
    flagged = {g.obligation_id for g in labels.gaps if g.obligation_id is not None}
    for obligation in labels.obligations:
        if obligation.evidence_class != "strongly_supported":
            assert obligation.id in flagged, (
                f"{fixture_dir.name}: obligation {obligation.id!r} is "
                f"{obligation.evidence_class} but no gap references it"
            )


def test_build_benchmark_case_validates(fixture_dir, tmp_path):
    case = build_benchmark_case(fixture_dir, tmp_path / "repo")

    assert isinstance(case, BenchmarkCase)
    assert case.case_id == fixture_dir.name
    assert case.source.kind == "archetype"
    assert case.inputs.base_revision != case.inputs.head_revision
    assert case.inputs.task_text.strip()
    assert case.ground_truth.obligations


def test_candidate_test_ids_name_real_tests(fixture_dir, tmp_path):
    """Every test id a label maps to an obligation must be a real pytest node
    in the fixture's head — no dangling test references."""
    fixture = materialize_archetype(fixture_dir, tmp_path / "repo")
    real_test_ids = _collected_test_ids(fixture.repo_path)
    labels = load_labels(fixture_dir)

    labeled = {t for o in labels.obligations for t in o.candidate_tests}
    unknown = labeled - real_test_ids
    assert not unknown, f"labels reference tests that do not exist: {sorted(unknown)}"


def test_declaration_mismatch_case_carries_the_declaration(tmp_path):
    fixture_dir = ARCHETYPES_DIR / "07-declaration-mismatch"
    case = build_benchmark_case(fixture_dir, tmp_path / "repo")
    assert case.inputs.declaration_text is not None
    assert "KeyError" in case.inputs.declaration_text
    # The gap here is a declaration-vs-code discrepancy, not a task obligation.
    assert case.ground_truth.gaps[0].obligation_id is None


def test_revision_cycle_is_a_true_negative(tmp_path):
    """#9 head closes the earlier gap, so its ground truth has no gap — a
    precision (false-alarm) check for the checker, not a recall check."""
    fixture_dir = ARCHETYPES_DIR / "09-revision-cycle"
    case = build_benchmark_case(fixture_dir, tmp_path / "repo")
    assert case.ground_truth.gaps == []
    ties = next(o for o in case.ground_truth.obligations if o.id == "ties-to-even")
    assert ties.evidence_class == "strongly_supported"


def test_full_loop_scores_the_noop_checker_as_all_miss(tmp_path):
    """fixture -> labeled case -> run the (no-op) checker -> score. The empty
    skeleton finds nothing, so every recall metric over the labels is 0.0."""
    cases = []
    for i, fixture_dir in enumerate(FIXTURE_DIRS):
        case = build_benchmark_case(fixture_dir, tmp_path / f"repo-{i}")
        cases.append(
            run_case(
                case,
                config=RunConfig(),
                review_store=ReviewStore(tmp_path / f"reviews-{i}"),
            )
        )

    report = score_case_set(cases)

    assert report.case_count == len(FIXTURE_DIRS)
    assert report.gap_recall == 0.0  # eight fixtures label a gap; none found
    assert report.decomposition_accuracy == 0.0  # obligations labeled everywhere; none found
    assert report.mapping_accuracy == 0.0  # coverage edges labeled; none found
    assert report.evidence_agreement == 0.0
    assert report.determinism_mode == "replay"
