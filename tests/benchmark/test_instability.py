"""Tests for the judgement-instability harness (#189).

Every test runs in replay/injected mode. The harness itself issues live calls by
design — that is what measuring a judge requires — so nothing here may.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from acceptance.benchmark.fixtures import build_benchmark_case  # noqa: E402
from acceptance.benchmark.instability import (  # noqa: E402
    DEFAULT_MODELS,
    DEFAULT_RUNS_PER_MODEL,
    ClassDistribution,
    DifferenceClass,
    DifferenceKind,
    InstabilityReport,
    ModelInstability,
    ObservingClient,
    PerturbationResult,
    Perturbation,
    RunKey,
    RunSnapshot,
    add_unrelated_test,
    classify_unmatched,
    compare_runs,
    cross_model_agreement,
    measure_instability,
    run_once,
    seeds_for,
    summarize_model,
)
from support import client_dispatching, client_finding_nothing  # noqa: E402

ARCHETYPES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "archetypes"


def _snapshot(index, obligations, evidence=None, questions=(), defects=(), model="m"):
    return RunSnapshot(
        run=RunKey(model=model, seed=1000 + index, index=index),
        obligations=obligations,
        evidence_classes=evidence or {oid: "strongly_supported" for oid in obligations},
        open_questions=list(questions),
        defect_verdicts=list(defects),
    )


def _coverage_client(covered_by_subject: dict[str, bool], alignment_matches=()):
    """A client answering both calls `compare_runs` makes: alignment, then
    coverage of whatever the alignment left unmatched."""
    return client_dispatching(
        {
            "_Alignment": {"matches": list(alignment_matches)},
            "_CoverageJudgement": {
                "items": [
                    {"subject": subject, "covered": covered, "reason": "test double"}
                    for subject, covered in covered_by_subject.items()
                ]
            },
        }
    )


# --------------------------------------------------------------------------
# content vs shape — the distinction the whole harness turns on
# --------------------------------------------------------------------------


def test_an_unmatched_statement_covered_by_the_other_set_is_a_shape_difference():
    client = _coverage_client({"run the pipeline across models": True})

    classified = classify_unmatched(
        ["run the pipeline across models"],
        ["run the pipeline repeatedly across a chosen set of models"],
        client,
    )

    assert classified == {"run the pipeline across models": DifferenceClass.SHAPE}


def test_an_unmatched_statement_covered_by_nothing_is_a_content_difference():
    client = _coverage_client({"never write into the reviewed repo": False})

    classified = classify_unmatched(
        ["never write into the reviewed repo"], ["something else entirely"], client
    )

    assert classified == {"never write into the reviewed repo": DifferenceClass.CONTENT}


def test_an_unanswered_subject_counts_as_content_not_shape():
    """Silence is not evidence that nothing was lost. Defaulting an unanswered
    subject to `covered` would understate the class that matters."""
    client = _coverage_client({})  # the double answers about nothing

    classified = classify_unmatched(["a dropped requirement"], ["unrelated"], client)

    assert classified == {"a dropped requirement": DifferenceClass.CONTENT}


def test_with_no_counterpart_set_at_all_everything_is_content():
    """No model call is needed, and none should be made: if the other run
    produced nothing, everything in this one is missing from it."""
    classified = classify_unmatched(["anything"], [], client_finding_nothing())

    assert classified == {"anything": DifferenceClass.CONTENT}


def test_a_lost_obligation_is_reported_as_a_content_difference():
    left = _snapshot(0, {"a": "keep a provenance record", "b": "write nothing to the repo"})
    right = _snapshot(1, {"a": "keep a provenance record"})
    client = _coverage_client(
        {"write nothing to the repo": False},
        alignment_matches=[{"ground_truth": "g0", "reviewer": "r0"}],
    )

    differences = compare_runs(left, right, client)

    lost = [d for d in differences if d.kind is DifferenceKind.OBLIGATION]
    assert len(lost) == 1
    assert lost[0].classification is DifferenceClass.CONTENT
    assert lost[0].subject == "write nothing to the repo"
    assert lost[0].absent_from == right.run.label()


def test_a_repartitioned_obligation_is_reported_as_a_shape_difference():
    """The run 3 -> 4 case from the Gate 1 corpus: one sentence stated as one
    obligation in one run and split in the next. Nothing was lost."""
    left = _snapshot(0, {"a": "run the pipeline repeatedly across a set of models"})
    right = _snapshot(1, {"a": "run the pipeline repeatedly", "b": "run across a set of models"})
    # Both directions are asked: the combined statement is covered by the two
    # split ones, and each split one is covered by the combined one. Answering
    # only one side would leave the other unanswered, which counts as content.
    client = _coverage_client(
        {
            "run the pipeline repeatedly across a set of models": True,
            "run the pipeline repeatedly": True,
            "run across a set of models": True,
        },
        alignment_matches=[],
    )

    differences = compare_runs(left, right, client)

    obligation_differences = [d for d in differences if d.kind is DifferenceKind.OBLIGATION]
    assert obligation_differences
    assert all(d.classification is DifferenceClass.SHAPE for d in obligation_differences)


def test_an_oscillating_open_question_is_a_content_difference():
    """The corpus's headline finding: a question present in one run and absent
    in the next, on task text that never changed."""
    left = _snapshot(0, {"a": "x"}, questions=["What output format should the report use?"])
    right = _snapshot(1, {"a": "x"}, questions=[])
    client = _coverage_client(
        {"What output format should the report use?": False},
        alignment_matches=[{"ground_truth": "g0", "reviewer": "r0"}],
    )

    differences = compare_runs(left, right, client)

    questions = [d for d in differences if d.kind is DifferenceKind.OPEN_QUESTION]
    assert len(questions) == 1
    assert questions[0].classification is DifferenceClass.CONTENT


def test_a_flipped_evidence_class_is_content_and_never_shape():
    """A rating that moves is a judgement present in one run and absent from the
    other. There is no partitioning involved, so it cannot be shape."""
    left = _snapshot(0, {"a": "x"}, evidence={"a": "strongly_supported"})
    right = _snapshot(1, {"a": "x"}, evidence={"a": "partially_supported"})
    client = _coverage_client({}, alignment_matches=[{"ground_truth": "g0", "reviewer": "r0"}])

    differences = compare_runs(left, right, client)

    flips = [d for d in differences if d.kind is DifferenceKind.EVIDENCE_CLASS]
    assert len(flips) == 1
    assert flips[0].classification is DifferenceClass.CONTENT
    assert flips[0].detail == "strongly_supported -> partially_supported"


def test_a_flipped_defect_verdict_is_reported_per_defect():
    """DR-180's localized instance: identical mapped tests, same defect, opposite
    `would_be_caught`. The obligation's final class can hide this, so the
    per-defect verdict is measured in its own right."""
    from acceptance.benchmark.instability import DefectVerdict

    defect = "the writer still emits the file"
    left = _snapshot(0, {"a": "x"}, defects=[DefectVerdict(obligation_id="a", defect=defect, would_be_caught=True)])
    right = _snapshot(1, {"a": "x"}, defects=[DefectVerdict(obligation_id="a", defect=defect, would_be_caught=False)])
    client = _coverage_client({}, alignment_matches=[{"ground_truth": "g0", "reviewer": "r0"}])

    differences = compare_runs(left, right, client)

    verdicts = [d for d in differences if d.kind is DifferenceKind.DEFECT_VERDICT]
    assert len(verdicts) == 1
    assert verdicts[0].classification is DifferenceClass.CONTENT
    assert "would_be_caught True -> False" in verdicts[0].detail


# --------------------------------------------------------------------------
# aggregation
# --------------------------------------------------------------------------


def test_content_and_shape_are_reported_as_separate_figures():
    """The requirement that governs the report: the two classes have different
    fixes, so no field may carry their sum."""
    left = _snapshot(0, {"a": "x", "b": "dropped requirement"}, evidence={"a": "strongly_supported", "b": None})
    right = _snapshot(1, {"a": "x"}, evidence={"a": "partially_supported"})
    client = _coverage_client(
        {"dropped requirement": False},
        alignment_matches=[{"ground_truth": "g0", "reviewer": "r0"}],
    )

    summary = summarize_model("m", [left, right], client)

    assert summary.content_differences
    assert summary.content_difference_count.mean is not None
    assert summary.shape_difference_count.mean is not None
    combined = {"total_differences", "difference_count", "variance"}
    assert combined.isdisjoint(ModelInstability.model_fields)


def test_presence_rows_show_an_obligation_missing_from_some_runs():
    left = _snapshot(0, {"a": "kept", "b": "sometimes lost"})
    right = _snapshot(1, {"a": "kept"})
    client = _coverage_client(
        {"sometimes lost": False}, alignment_matches=[{"ground_truth": "g0", "reviewer": "r0"}]
    )

    summary = summarize_model("m", [left, right], client)
    rows = {row.subject: row for row in summary.obligation_presence}

    assert rows["kept"].runs_present == 2 and rows["kept"].stable()
    assert rows["sometimes lost"].runs_present == 1
    assert not rows["sometimes lost"].stable()


def test_evidence_class_distribution_counts_every_draw():
    snapshots = [
        _snapshot(0, {"a": "x"}, evidence={"a": "strongly_supported"}),
        _snapshot(1, {"a": "x"}, evidence={"a": "partially_supported"}),
        _snapshot(2, {"a": "x"}, evidence={"a": "strongly_supported"}),
    ]
    client = _coverage_client({}, alignment_matches=[{"ground_truth": "g0", "reviewer": "r0"}])

    summary = summarize_model("m", snapshots, client)
    distribution = {d.subject: d for d in summary.evidence_class_distribution}["x"]

    assert distribution.counts == {"strongly_supported": 2, "partially_supported": 1}
    assert not distribution.unanimous()
    assert distribution.modal() == "strongly_supported"


def test_the_harness_uses_the_benchmark_variance_path_and_not_a_second_one():
    """Constraint from the task: statistics come from `disclose_variance`'s
    machinery. Asserting the shared symbol keeps a copy from creeping back."""
    from acceptance.benchmark import instability, scoring

    assert instability.metric_stats is scoring.metric_stats
    assert instability.MetricStats is scoring.MetricStats


def test_cross_model_agreement_is_reported_alongside_within_model_variance():
    a = ModelInstability(
        model="model-a",
        evidence_class_distribution=[ClassDistribution(subject="x", counts={"strongly_supported": 3})],
    )
    b = ModelInstability(
        model="model-b",
        evidence_class_distribution=[ClassDistribution(subject="x", counts={"unsupported": 3})],
    )

    rows = cross_model_agreement([a, b])

    assert len(rows) == 1
    assert rows[0].agreement() == 0.0
    assert rows[0].modal_class_by_model == {
        "model-a": "strongly_supported",
        "model-b": "unsupported",
    }


def test_cross_model_agreement_is_none_with_a_single_model():
    """One model yields no pairs. Reporting 1.0 would claim agreement that was
    never tested."""
    only = ModelInstability(
        model="model-a",
        evidence_class_distribution=[ClassDistribution(subject="x", counts={"unsupported": 1})],
    )

    assert cross_model_agreement([only])[0].agreement() is None


# --------------------------------------------------------------------------
# perturbation
# --------------------------------------------------------------------------


def test_perturbation_sensitivity_is_a_proportion_of_watched_judgements():
    result = PerturbationResult(
        name="add-unrelated-test", watched_judgements=8, changed_judgements=2
    )

    assert result.sensitivity() == 0.25


def test_perturbation_sensitivity_is_none_when_nothing_was_watched():
    result = PerturbationResult(name="x", watched_judgements=0, changed_judgements=0)

    assert result.sensitivity() is None


def test_the_perturbation_never_writes_into_the_repository_under_review(tmp_path):
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")
    repo = Path(case.inputs.repo)
    before = sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*") if p.is_file())

    perturbed = add_unrelated_test(case)

    after = sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*") if p.is_file())
    assert after == before
    assert Path(perturbed.inputs.repo) != repo
    assert perturbed.inputs.head_revision != case.inputs.head_revision


def test_the_perturbation_adds_a_test_that_asserts_nothing_about_the_change(tmp_path):
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")

    perturbed = add_unrelated_test(case)

    added = "\n".join(
        p.read_text() for p in Path(perturbed.inputs.repo).rglob("test_*.py")
    )
    assert "test_unrelated_addition_for_perturbation_measurement" in added


# --------------------------------------------------------------------------
# defaults, guards and provenance
# --------------------------------------------------------------------------


def test_the_default_run_is_one_model_and_three_runs():
    """Measuring more than one model must be something the caller opts into,
    not the cost of a default run."""
    assert len(DEFAULT_MODELS) == 1
    assert DEFAULT_RUNS_PER_MODEL == 3


def test_seeds_are_derived_so_a_measurement_is_repeatable_from_its_provenance():
    assert seeds_for(3) == seeds_for(3)
    assert len(set(seeds_for(3))) == 3, "draws must differ, or nothing is resampled"


def test_measuring_variance_requires_at_least_two_runs(tmp_path):
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")

    with pytest.raises(ValueError, match="at least two runs"):
        measure_instability(case, runs_per_model=1)


# --------------------------------------------------------------------------
# wiring — the pipeline is actually driven, not just the helpers
# --------------------------------------------------------------------------


def _observing_factory(calls):
    def factory(config):
        def completion_fn(**kwargs):
            name = kwargs["response_format"]["json_schema"]["name"]
            calls.append((config.seed, name))
            empty = {
                "_Decomposition": {"obligations": [], "open_questions": []},
                "_Mappings": {"mappings": []},
                "_Discrimination": {"discriminations": []},
                "_Coverage": {"classifications": []},
                "_Detections": {"unrequested_changes": []},
                "_Judgments": {"resolutions": []},
                "_Recommendations": {"recommendations": []},
                "_Mismatches": {"mismatches": []},
            }[name]
            from types import SimpleNamespace

            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(empty)))],
                usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            )

        import tempfile

        from acceptance.llm import TranscriptStore

        return ObservingClient(
            model=config.model,
            mode=config.mode,
            store=TranscriptStore(tempfile.mkdtemp()),
            temperature=config.temperature,
            seed=config.seed,
            completion_fn=completion_fn,
        )

    return factory


def test_run_once_drives_the_real_pipeline_and_snapshots_its_output(tmp_path):
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")
    calls: list = []

    snapshot = run_once(case, RunKey(model="m", seed=7, index=0), client_factory=_observing_factory(calls))

    assert isinstance(snapshot, RunSnapshot)
    assert "_Decomposition" in {name for _, name in calls}, "decompose must be inside the measured surface"
    assert all(seed == 7 for seed, _ in calls), "the run's seed must reach the client"


def test_measure_instability_varies_the_seed_across_runs(tmp_path):
    """Independent draws are the whole point: repeated runs on one fixed seed
    would replay a recording and measure nothing."""
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")
    calls: list = []

    measure_instability(
        case,
        runs_per_model=2,
        perturbation=None,
        comparison_client=client_finding_nothing(),
        client_factory=_observing_factory(calls),
    )

    assert len(set(seed for seed, _ in calls)) == 2


def test_measure_instability_records_the_conditions_that_produced_it(tmp_path):
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")

    report = measure_instability(
        case,
        models=["model-a"],
        runs_per_model=2,
        perturbation=None,
        comparison_client=client_finding_nothing(),
        client_factory=_observing_factory([]),
    )

    assert isinstance(report, InstabilityReport)
    provenance = report.provenance
    assert provenance.models == ["model-a"]
    assert provenance.runs_per_model == 2
    assert provenance.seeds == seeds_for(2)
    assert provenance.case_id == case.case_id
    assert provenance.task_digest


def test_a_perturbation_run_is_included_when_one_is_supplied(tmp_path):
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")
    applied: list = []

    def apply(c):
        applied.append(c)
        return c

    report = measure_instability(
        case,
        runs_per_model=2,
        perturbation=Perturbation(name="noop", apply=apply),
        comparison_client=client_finding_nothing(),
        client_factory=_observing_factory([]),
    )

    assert applied, "the perturbation must actually be applied"
    assert report.perturbation is not None
    assert report.perturbation.name == "noop"
    assert report.provenance.perturbation == "noop"
