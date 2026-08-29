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

from support import _completed, client_dispatching, client_finding_nothing

from acceptance.benchmark.fixtures import build_benchmark_case
from acceptance.benchmark.instability import (
    DEFAULT_MODELS,
    DEFAULT_RUNS_PER_MODEL,
    ClassDistribution,
    DifferenceClass,
    DifferenceKind,
    InstabilityReport,
    ModelInstability,
    ObservingClient,
    Perturbation,
    PerturbationResult,
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
from acceptance.config import Mode, RunConfig

_EMPTY_BY_SCHEMA = {
    "_Decomposition": {"obligations": [], "open_questions": [], "requirement_dispositions": []},
    # The summary pass (#317) — filled in from the request by `_completed`,
    # because a span has to be a substring of the summary the call was shown.
    "_SummarySpans": {},
    "_Mappings": {"mappings": []},
    "_Discrimination": {"discriminations": []},
    "_Coverage": {"classifications": []},
    "_Detections": {"unrequested_changes": []},
    "_Judgments": {"resolutions": []},
    "_Recommendations": {"recommendations": []},
    "_Mismatches": {"mismatches": []},
}


def _recording_factory(calls: list):
    """An ObservingClient factory that records (model, seed, schema) per call,
    so a test can assert which models and seeds actually reached the pipeline."""

    def factory(config):
        def completion_fn(**kwargs):
            from types import SimpleNamespace

            name = kwargs["response_format"]["json_schema"]["name"]
            calls.append((config.model, config.seed, name))
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=json.dumps(_completed(_EMPTY_BY_SCHEMA[name], **kwargs))
                        )
                    )
                ],
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
    left = _snapshot(
        0,
        {"a": "x"},
        defects=[DefectVerdict(obligation_id="a", defect=defect, would_be_caught=True)],
    )
    right = _snapshot(
        1,
        {"a": "x"},
        defects=[DefectVerdict(obligation_id="a", defect=defect, would_be_caught=False)],
    )
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
    left = _snapshot(
        0, {"a": "x", "b": "dropped requirement"}, evidence={"a": "strongly_supported", "b": None}
    )
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
        evidence_class_distribution=[
            ClassDistribution(subject="x", counts={"strongly_supported": 3})
        ],
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

    added = "\n".join(p.read_text() for p in Path(perturbed.inputs.repo).rglob("test_*.py"))
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
                "_Decomposition": {
                    "obligations": [],
                    "open_questions": [],
                    "requirement_dispositions": [],
                },
                "_SummarySpans": {},
                "_Mappings": {"mappings": []},
                "_Discrimination": {"discriminations": []},
                "_Coverage": {"classifications": []},
                "_Detections": {"unrequested_changes": []},
                "_Judgments": {"resolutions": []},
                "_Recommendations": {"recommendations": []},
                "_Mismatches": {"mismatches": []},
            }[name]
            empty = _completed(empty, **kwargs)
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

    snapshot = run_once(
        case, RunKey(model="m", seed=7, index=0), client_factory=_observing_factory(calls)
    )

    assert isinstance(snapshot, RunSnapshot)
    assert "_Decomposition" in {name for _, name in calls}, (
        "decompose must be inside the measured surface"
    )
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

    assert len({seed for seed, _ in calls}) == 2


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


# --------------------------------------------------------------------------
# Gate 2 gaps: behaviour through `measure_instability`, not just its helpers
# --------------------------------------------------------------------------


def test_observations_do_not_leak_between_clients():
    """A mutable class-level default would make every run share one list, so all
    runs would look identical — stability faked by the measuring instrument."""
    import tempfile

    from acceptance.llm import TranscriptStore

    def build():
        return ObservingClient(
            model="m", mode=Mode.RECORD, store=TranscriptStore(tempfile.mkdtemp())
        )

    first, second = build(), build()
    first.observed.append("only mine")

    assert second.observed == []


def test_a_caller_supplied_model_set_is_actually_measured(tmp_path):
    """Not just accepted — every named model must reach a run. The cross-model
    figure is meaningless if only the first model is ever executed."""
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")
    calls: list = []

    report = measure_instability(
        case,
        models=["model-a", "model-b"],
        runs_per_model=2,
        perturbation=None,
        comparison_client=client_finding_nothing(),
        client_factory=_recording_factory(calls),
    )

    assert {model for model, _, _ in calls} == {"model-a", "model-b"}
    assert [m.model for m in report.per_model] == ["model-a", "model-b"]


def test_the_default_run_count_produces_three_runs_per_model(tmp_path):
    """Asserting the constant is 3 would pass against an implementation that
    ignores it. Count the runs actually executed."""
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")
    calls: list = []

    report = measure_instability(
        case,
        perturbation=None,
        comparison_client=client_finding_nothing(),
        client_factory=_recording_factory(calls),
    )

    assert len({seed for _, seed, _ in calls}) == DEFAULT_RUNS_PER_MODEL == 3
    assert len(report.per_model[0].runs) == 3


def test_runs_are_recorded_live_and_never_replayed(tmp_path):
    """Replay returns a recording. Measuring the judge over replayed draws would
    measure the transcript, so every run must be in RECORD mode."""
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")
    modes: list = []

    def factory(config):
        modes.append(config.mode)
        return _recording_factory([])(config)

    measure_instability(
        case,
        runs_per_model=2,
        perturbation=None,
        comparison_client=client_finding_nothing(),
        client_factory=factory,
    )

    assert modes and all(mode is Mode.RECORD for mode in modes)


def test_obligations_align_by_content_even_when_their_ids_differ():
    """decompose assigns ids afresh each run, so identifier equality would
    report every obligation as both lost and gained."""
    left = _snapshot(0, {"run1-slug": "record the seeds that produced the report"})
    right = _snapshot(1, {"totally-different-slug": "record the seeds that produced the report"})
    client = _coverage_client({}, alignment_matches=[{"ground_truth": "g0", "reviewer": "r0"}])

    differences = compare_runs(left, right, client)

    assert not [d for d in differences if d.kind is DifferenceKind.OBLIGATION]


def test_matching_ids_with_different_text_are_not_treated_as_the_same_obligation():
    """The converse: a shared id must not paper over different content."""
    left = _snapshot(0, {"same-id": "write nothing into the reviewed repo"})
    right = _snapshot(1, {"same-id": "something else entirely"})
    client = _coverage_client(
        {
            "write nothing into the reviewed repo": False,
            "something else entirely": False,
        },
        alignment_matches=[],
    )

    differences = compare_runs(left, right, client)

    assert [d for d in differences if d.kind is DifferenceKind.OBLIGATION]


def test_content_and_shape_counts_diverge_when_both_kinds_occur():
    """A summed metric would be wrong here, so the counts must differ."""
    left = _snapshot(0, {"a": "kept requirement", "b": "lost requirement"})
    right = _snapshot(1, {"a": "kept requirement", "c": "kept requirement, restated"})
    client = _coverage_client(
        {"lost requirement": False, "kept requirement, restated": True},
        alignment_matches=[{"ground_truth": "g0", "reviewer": "r0"}],
    )

    summary = summarize_model("m", [left, right], client)

    assert len(summary.content_differences) == 1
    assert len(summary.shape_differences) == 1
    assert summary.content_difference_count.mean == 1.0
    assert summary.shape_difference_count.mean == 1.0
    # The point of the case: a summed metric would report 2 for both and lose
    # the distinction the whole report turns on.
    assert summary.content_differences[0].subject == "lost requirement"
    assert summary.shape_differences[0].subject == "kept requirement, restated"


def test_the_report_carries_no_pass_fail_or_threshold_field():
    """The harness reports; deciding whether a figure is acceptable belongs to
    the task that changes the judge."""
    forbidden = {"verdict", "passed", "threshold", "acceptable", "rating", "status"}

    for model in (InstabilityReport, ModelInstability, PerturbationResult):
        assert forbidden.isdisjoint(model.model_fields), model.__name__


def test_no_ci_workflow_invokes_the_instability_harness():
    """It issues live model calls, so it must be run deliberately. This is the
    one obligation whose evidence is a config file rather than Python."""
    workflows = Path(__file__).resolve().parents[2] / ".github" / "workflows"
    text = "\n".join(p.read_text() for p in workflows.glob("*.yml"))

    assert "instability" not in text
    assert "measure_instability" not in text


def test_the_observing_client_does_not_change_what_the_pipeline_produces(tmp_path):
    """The harness measures; it must not perturb the thing it measures. Same
    case, same responses — an ObservingClient and a plain one must agree."""
    from acceptance.benchmark.coverage import classify_case

    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")

    plain = classify_case(case, client_finding_nothing(seed=5))
    observed = classify_case(
        case, _recording_factory([])(RunConfig(model="m", mode=Mode.RECORD, seed=5))
    )

    assert plain.reviewer_output is not None and observed.reviewer_output is not None
    assert [o.description for o in plain.reviewer_output.obligation_map] == [
        o.description for o in observed.reviewer_output.obligation_map
    ]
    assert plain.reviewer_output.completion is not None


# --------------------------------------------------------------------------
# Gate 2 run 2: the last four obligations
# --------------------------------------------------------------------------


def test_cross_model_agreement_covers_every_judgement_axis():
    """Evidence classes alone would be blind to open-question presence, which is
    the axis where the decompose-stability corpus found the worst instability."""
    from acceptance.benchmark.instability import AgreementAxis, PresenceRow

    a = ModelInstability(
        model="model-a",
        evidence_class_distribution=[
            ClassDistribution(subject="ob", counts={"strongly_supported": 3})
        ],
        defect_verdict_distribution=[ClassDistribution(subject="ob :: d", counts={"true": 3})],
        obligation_presence=[PresenceRow(subject="ob", runs_present=3, runs_total=3)],
        open_question_presence=[PresenceRow(subject="what format?", runs_present=3, runs_total=3)],
    )
    b = ModelInstability(
        model="model-b",
        evidence_class_distribution=[
            ClassDistribution(subject="ob", counts={"strongly_supported": 3})
        ],
        defect_verdict_distribution=[ClassDistribution(subject="ob :: d", counts={"false": 3})],
        obligation_presence=[PresenceRow(subject="ob", runs_present=3, runs_total=3)],
        open_question_presence=[PresenceRow(subject="what format?", runs_present=0, runs_total=3)],
    )

    rows = cross_model_agreement([a, b])
    by_axis = {(row.axis, row.subject): row for row in rows}

    assert set(AgreementAxis) == {axis for axis, _ in by_axis}
    assert by_axis[(AgreementAxis.EVIDENCE_CLASS, "ob")].agreement() == 1.0
    assert by_axis[(AgreementAxis.DEFECT_VERDICT, "ob :: d")].agreement() == 0.0
    # The finding this harness exists for: one model raises the question every
    # run, the other never does.
    assert by_axis[(AgreementAxis.OPEN_QUESTION_PRESENCE, "what format?")].agreement() == 0.0


def test_a_model_that_cannot_make_up_its_mind_does_not_count_as_agreeing():
    """A three-valued presence label. Collapsing 'sometimes' into present or
    absent would let an unstable model agree with a consistent one."""
    from acceptance.benchmark.instability import AgreementAxis, PresenceRow

    steady = ModelInstability(
        model="steady",
        open_question_presence=[PresenceRow(subject="q", runs_present=3, runs_total=3)],
    )
    wobbly = ModelInstability(
        model="wobbly",
        open_question_presence=[PresenceRow(subject="q", runs_present=2, runs_total=3)],
    )

    rows = {(r.axis, r.subject): r for r in cross_model_agreement([steady, wobbly])}
    row = rows[(AgreementAxis.OPEN_QUESTION_PRESENCE, "q")]

    assert row.agreement() == 0.0
    assert row.modal_class_by_model == {"steady": "present", "wobbly": "unstable (2/3)"}


def test_the_three_movement_sources_are_reported_as_distinct_figures(tmp_path):
    """One report where all three sources are simultaneously non-empty and land
    in different fields. A blended figure could not keep them apart."""
    from acceptance.benchmark.instability import AgreementAxis

    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")

    report = measure_instability(
        case,
        models=["model-a", "model-b"],
        runs_per_model=2,
        perturbation=Perturbation(name="noop", apply=lambda c: c),
        comparison_client=client_finding_nothing(),
        client_factory=_recording_factory([]),
    )

    # 1. resample — per model, from repeated runs
    assert [m.model for m in report.per_model] == ["model-a", "model-b"]
    assert all(m.content_difference_count is not None for m in report.per_model)
    # 2. perturbation — its own field, with its own figure
    assert report.perturbation is not None
    assert (
        report.perturbation.sensitivity() is not None or report.perturbation.watched_judgements == 0
    )
    # 3. model — its own field, keyed by axis
    assert {row.axis for row in report.cross_model_agreement} <= set(AgreementAxis)
    # and no field carries their sum
    assert not hasattr(report, "total_movement")


def test_decomposition_variation_is_surfaced_and_not_only_evidence_variation():
    """The whole-pipeline surface has to reach the report. An obligation that
    appears in one run and not another is decompose moving, and it must show up
    distinctly from an evidence-class flip."""
    left = _snapshot(0, {"a": "kept", "b": "obligation only this run produced"})
    right = _snapshot(1, {"a": "kept"})
    client = _coverage_client(
        {"obligation only this run produced": False},
        alignment_matches=[{"ground_truth": "g0", "reviewer": "r0"}],
    )

    summary = summarize_model("m", [left, right], client)

    presence = {row.subject: row for row in summary.obligation_presence}
    assert presence["obligation only this run produced"].runs_present == 1
    assert not presence["obligation only this run produced"].stable()
    decompose_differences = [
        d for d in summary.content_differences if d.kind is DifferenceKind.OBLIGATION
    ]
    assert decompose_differences, "decompose movement must reach the report on its own axis"
    assert all(d.kind is not DifferenceKind.EVIDENCE_CLASS for d in decompose_differences)


def test_omitted_parameters_fall_back_to_the_declared_defaults(tmp_path):
    """Defaults must be used when the caller omits them, not merely declared."""
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")
    calls: list = []

    report = measure_instability(
        case,
        comparison_client=client_finding_nothing(),
        client_factory=_recording_factory(calls),
    )

    assert report.provenance.models == list(DEFAULT_MODELS)
    assert report.provenance.runs_per_model == DEFAULT_RUNS_PER_MODEL
    assert report.provenance.seeds == seeds_for(DEFAULT_RUNS_PER_MODEL)
    assert report.provenance.perturbation == "add-unrelated-test"
    assert {model for model, _, _ in calls} == set(DEFAULT_MODELS)


def test_the_harness_reports_variance_without_reducing_it():
    """No smoothing, damping or discarding of outliers: every draw survives into
    the distribution. Stability bought by blunting the measurement would hide the
    defect this exists to find."""
    snapshots = [
        _snapshot(0, {"a": "x"}, evidence={"a": "strongly_supported"}),
        _snapshot(1, {"a": "x"}, evidence={"a": "unsupported"}),
        _snapshot(2, {"a": "x"}, evidence={"a": "strongly_supported"}),
    ]
    client = _coverage_client({}, alignment_matches=[{"ground_truth": "g0", "reviewer": "r0"}])

    summary = summarize_model("m", snapshots, client)
    distribution = {d.subject: d for d in summary.evidence_class_distribution}["x"]

    # The lone outlier is still there; a mitigating harness would have dropped it.
    assert distribution.counts == {"strongly_supported": 2, "unsupported": 1}
    assert sum(distribution.counts.values()) == len(snapshots)
    # Every pairwise difference is retained, not averaged away.
    assert len(summary.content_differences) == 2
