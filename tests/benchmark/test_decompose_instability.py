"""The decompose-only instability instrument (#193).

Replay-first: every test here builds its snapshots directly or injects a
completion function, so the suite issues no live model call. The one test that
exercises `decompose_once` end to end asserts that property explicitly rather
than relying on it.
"""

from __future__ import annotations

import json

import pytest

from acceptance.benchmark.decompose_instability import (
    DecomposeSnapshot,
    _moved_requirements,
    append_unrelated_exclusion,
    decompose_once,
    measure_decompose_instability,
    snapshot_decomposition,
    summarize_decompose,
    symbols_in,
)
from acceptance.benchmark.instability import RunKey
from acceptance.requirement.obligations import Decomposition
from acceptance.requirement.registry import build_registry
from acceptance.requirement.task_file import parse_task_file
from acceptance.review_state import (
    Disposition,
    Obligation,
    ObligationType,
    RequirementDisposition,
    RequirementMap,
    RequirementRef,
    RequirementSection,
)
from acceptance.source_ref import TextSpan
from tests.support import _completed, _fake_response, model_client_with

TASK = """# Task
Report the variance the harness measures.

## Constraints
- The statistics come from `benchmark/scoring.py::disclose_variance` rather \
than a second path.
- Alignment uses the existing `align_obligations` function.

## Scope exclusions
- Interpreting the figures it produces.

## Completion expectations
- A test asserts the statistics are sourced from the existing path.
"""


def _run(index: int, seed: int = 1000) -> RunKey:
    return RunKey(model="test-model", seed=seed, index=index)


def _span(text: str = "x") -> TextSpan:
    return TextSpan(text=text, start=0, end=len(text))


def _obligation(oid: str, description: str, type_: str = "functional") -> Obligation:
    return Obligation(
        id=oid,
        description=description,
        type=ObligationType(type_),
        importance="normal",
        explicit=True,
        observable_behavior="observable",
    )


def _decomposition(
    requirement_text: str,
    obligations: list[Obligation],
    requirement_id: str = "constraint-01",
) -> Decomposition:
    """One requirement and what it yielded, as `decompose` would return it."""
    return Decomposition(
        obligations=obligations,
        open_questions=[],
        requirement_map=RequirementMap(
            requirements=[
                RequirementRef(
                    id=requirement_id,
                    section=RequirementSection.CONSTRAINT,
                    ordinal=1,
                    span=_span(requirement_text),
                )
            ],
            dispositions=[
                RequirementDisposition(
                    requirement_id=requirement_id,
                    disposition=Disposition.YIELDED,
                    obligation_ids=[o.id for o in obligations],
                )
            ],
        ),
    )


# --------------------------------------------------------------------------
# Symbols
# --------------------------------------------------------------------------


def test_symbols_are_taken_from_backticks_and_qualified_references():
    text = "Use `benchmark/scoring.py::disclose_variance` and `align_obligations`."
    assert symbols_in(text) == [
        "benchmark/scoring.py::disclose_variance",
        "align_obligations",
    ]


def test_backticked_prose_is_not_a_symbol():
    """The whitespace rule, which is what keeps this from reporting every
    emphasised phrase as a lost identifier."""
    assert symbols_in("the `existing variance path` is used") == []


def test_an_unbackticked_qualified_reference_is_still_a_symbol():
    assert symbols_in("see benchmark/scoring.py::score_case for it") == [
        "benchmark/scoring.py::score_case"
    ]


def test_a_symbol_repeated_in_one_requirement_is_one_symbol():
    assert symbols_in("`f` and `f` again") == ["f"]


# --------------------------------------------------------------------------
# The snapshot, keyed on the requirement id
# --------------------------------------------------------------------------


def test_a_surviving_symbol_is_recorded_against_its_requirement():
    text = "Source them from `benchmark/scoring.py::disclose_variance`."
    result = _decomposition(
        text,
        [
            _obligation(
                "src-stats", "Source statistics from `benchmark/scoring.py::disclose_variance`."
            )
        ],
    )
    snapshot = snapshot_decomposition(result, _run(0))

    key = "constraint-01 :: benchmark/scoring.py::disclose_variance"
    assert snapshot.required_symbols == [key]
    assert snapshot.surviving_symbols == [key]


def test_a_dropped_symbol_is_required_but_does_not_survive():
    """#193 §3 exactly: the obligation states the same requirement and has
    discarded the only identifier in its source."""
    text = "Source them from `benchmark/scoring.py::disclose_variance`."
    result = _decomposition(
        text,
        [_obligation("src-stats", "The statistics come from the existing variance path.")],
    )
    snapshot = snapshot_decomposition(result, _run(0))

    key = "constraint-01 :: benchmark/scoring.py::disclose_variance"
    assert snapshot.required_symbols == [key]
    assert snapshot.surviving_symbols == []


def test_the_snapshot_keys_every_axis_on_the_requirement_id():
    text = "Do the thing with `widget`."
    result = _decomposition(
        text,
        [
            _obligation("a", "Do the thing with `widget`."),
            _obligation("b", "Report it.", type_="explanation_observability"),
        ],
    )
    snapshot = snapshot_decomposition(result, _run(0))

    assert snapshot.dispositions == {"constraint-01": "yielded"}
    assert snapshot.obligation_ids_by_requirement == {"constraint-01": ["a", "b"]}
    assert snapshot.types_by_requirement == {
        "constraint-01": ["functional", "explanation_observability"]
    }
    assert snapshot.descriptions_by_requirement["constraint-01"] == [
        "Do the thing with `widget`.",
        "Report it.",
    ]


# --------------------------------------------------------------------------
# Aggregation
# --------------------------------------------------------------------------


def _snapshot(index: int, descriptions: list[str], ids: list[str], types: list[str]):
    return DecomposeSnapshot(
        run=_run(index, seed=1000 + index),
        obligations=dict(zip(ids, descriptions)),
        dispositions={"constraint-01": "yielded"},
        obligation_ids_by_requirement={"constraint-01": ids},
        types_by_requirement={"constraint-01": types},
        descriptions_by_requirement={"constraint-01": descriptions},
        surviving_symbols=[],
        required_symbols=[],
    )


def test_identical_runs_are_unanimous_on_every_free_axis():
    snapshots = [_snapshot(i, ["Do X."], ["do-x"], ["functional"]) for i in range(3)]
    report = summarize_decompose("test-model", snapshots)

    assert report.unstable_requirements("description_distribution") == []
    assert report.unstable_requirements("obligation_id_distribution") == []
    assert report.unstable_requirements("type_distribution") == []


def test_a_reworded_description_is_reported_as_unstable():
    """The axis the whole design turns on: same requirement, different words."""
    snapshots = [
        _snapshot(0, ["Do X."], ["do-x"], ["functional"]),
        _snapshot(1, ["Perform X."], ["do-x"], ["functional"]),
        _snapshot(2, ["Do X."], ["do-x"], ["functional"]),
    ]
    report = summarize_decompose("test-model", snapshots)

    assert report.unstable_requirements("description_distribution") == ["constraint-01"]
    # The id held while the wording moved, so the id axis must stay clean —
    # otherwise the two findings could never be told apart.
    assert report.unstable_requirements("obligation_id_distribution") == []


def test_a_reminted_id_is_reported_even_when_the_wording_holds():
    snapshots = [
        _snapshot(0, ["Do X."], ["do-x"], ["functional"]),
        _snapshot(1, ["Do X."], ["perform-x"], ["functional"]),
    ]
    report = summarize_decompose("test-model", snapshots)

    assert report.unstable_requirements("obligation_id_distribution") == ["constraint-01"]
    assert report.unstable_requirements("description_distribution") == []


def test_an_unstable_type_is_reported():
    snapshots = [
        _snapshot(0, ["Do X."], ["do-x"], ["functional"]),
        _snapshot(1, ["Do X."], ["do-x"], ["human_review"]),
    ]
    report = summarize_decompose("test-model", snapshots)
    assert report.unstable_requirements("type_distribution") == ["constraint-01"]


def test_reordered_obligations_are_not_counted_as_agreement():
    """Order decides which obligation `linking.py` keeps as the survivor, so two
    runs that derived the same pair in a different order have not agreed."""
    snapshots = [
        _snapshot(0, ["A.", "B."], ["a", "b"], ["functional", "functional"]),
        _snapshot(1, ["B.", "A."], ["b", "a"], ["functional", "functional"]),
    ]
    report = summarize_decompose("test-model", snapshots)
    assert report.unstable_requirements("description_distribution") == ["constraint-01"]


def test_an_intermittently_surviving_symbol_is_separated_from_one_never_kept():
    kept = "constraint-01 :: kept"
    never = "constraint-01 :: never"
    snapshots = []
    for index, surviving in enumerate(([kept], [], [kept])):
        snapshot = _snapshot(index, ["Do X."], ["do-x"], ["functional"])
        snapshot.surviving_symbols = surviving
        snapshot.required_symbols = [kept, never]
        snapshots.append(snapshot)

    report = summarize_decompose("test-model", snapshots)
    lost = {row.subject: (row.runs_present, row.runs_total) for row in report.symbols_lost()}

    # Survived twice of three -- the #193 §3 instability.
    assert lost[kept] == (2, 3)
    # Never survived at all: a systematic loss, and a different finding. It has
    # no presence row of its own, so the report must not claim it was stable.
    assert never not in {row.subject for row in report.symbol_survival}


def test_a_skipped_comparison_reads_as_absent_rather_than_as_stability():
    """`None`, never `[]`. An empty difference list is indistinguishable from a
    measurement that found nothing, which is the one reading a measurement that
    never ran must never produce."""
    snapshots = [_snapshot(i, ["Do X."], ["do-x"], ["functional"]) for i in range(2)]
    report = summarize_decompose("test-model", snapshots, client=None)

    assert report.content_differences is None
    assert report.shape_differences is None
    assert report.content_difference_count is None


# --------------------------------------------------------------------------
# Perturbation
# --------------------------------------------------------------------------


def test_the_perturbation_leaves_every_existing_requirement_id_untouched():
    """If appending renumbered anything, every later requirement would look
    changed for a reason having nothing to do with the judge."""
    before = {r.id for r in build_registry(parse_task_file(TASK))}
    after = {r.id for r in build_registry(parse_task_file(append_unrelated_exclusion(TASK)))}

    # Set comparison, not positional: `build_registry` emits sections in a fixed
    # order, so a new exclusion lands ahead of the completion items in the list
    # while renaming nothing. Identity is the id, and every prior id survives.
    assert before < after
    assert after - before == {"exclusion-02"}


def test_the_perturbation_adds_its_bullet_to_scope_exclusions():
    perturbed = parse_task_file(append_unrelated_exclusion(TASK))
    assert len(perturbed.scope_exclusions) == 2
    assert "changelog" in perturbed.scope_exclusions[-1].text


def test_a_task_file_with_no_scope_exclusions_cannot_be_perturbed_silently():
    with pytest.raises(ValueError, match="Scope exclusions"):
        append_unrelated_exclusion("# Task\nDo it.\n")


def test_the_added_requirement_is_in_neither_the_numerator_nor_the_denominator():
    baseline = _snapshot(0, ["Do X."], ["do-x"], ["functional"])
    perturbed = _snapshot(0, ["Do X."], ["do-x"], ["functional"])
    perturbed.dispositions = {**perturbed.dispositions, "exclusion-02": "yielded"}
    perturbed.descriptions_by_requirement = {
        **perturbed.descriptions_by_requirement,
        "exclusion-02": ["The change does not alter the changelog format."],
    }

    assert _moved_requirements(baseline, perturbed) == []


def test_a_requirement_that_moved_under_the_perturbation_is_named():
    baseline = _snapshot(0, ["Do X."], ["do-x"], ["functional"])
    perturbed = _snapshot(0, ["Do X differently."], ["do-x"], ["functional"])

    assert _moved_requirements(baseline, perturbed) == ["constraint-01"]


# --------------------------------------------------------------------------
# Wiring — the instrument actually drives `decompose`
# --------------------------------------------------------------------------


def _yielding_client(calls: list[dict]):
    """Answers every batch by yielding one obligation per requirement."""

    def completion_fn(**kwargs):
        name = kwargs["response_format"]["json_schema"]["name"]
        if name != "_Decomposition":
            return _fake_response(json.dumps(_completed({}, **kwargs)))
        calls.append(kwargs)
        payload = _completed({"open_questions": [], "requirement_dispositions": []}, **kwargs)
        return _fake_response(json.dumps(payload))

    return model_client_with(completion_fn)


def test_decompose_once_drives_the_real_decompose_stage(monkeypatch):
    """And reaches no provider on the way.

    `decompose_once` builds its client in RECORD mode, which is the live path —
    so "no live call" holds only while every client the instrument builds
    carries its own `completion_fn`, and nothing but this would notice one that
    stopped. `_default_completion_fn` is the single door to litellm (`llm.py`),
    so breaking it is sufficient.
    """
    from acceptance import llm

    def forbidden(**kwargs):
        raise AssertionError("the instrument reached the live provider path")

    monkeypatch.setattr(llm, "_default_completion_fn", forbidden)

    calls: list[dict] = []
    snapshot = decompose_once(
        TASK,
        _run(0),
        client_factory=lambda config: _yielding_client(calls),
    )

    assert calls, "decompose_once did not reach the decompose stage"
    assert snapshot.run.index == 0
    # Every registry requirement is accounted for in the snapshot, whatever the
    # model said — the axis is keyed on the parse, not on the response.
    assert set(snapshot.dispositions) == {r.id for r in build_registry(parse_task_file(TASK))}


def test_each_draw_uses_its_own_seed():
    seeds: list[int | None] = []

    def factory(config):
        seeds.append(config.seed)
        return _yielding_client([])

    measure_decompose_instability(
        TASK,
        models=("test-model",),
        runs=3,
        perturb=False,
        client_factory=factory,
    )

    assert seeds == [1000, 1001, 1002]


def test_the_perturbed_draw_shares_the_first_baseline_seed():
    """Otherwise the perturbation measurement would confound an added bullet
    with a different draw."""
    seeds: list[int | None] = []

    def factory(config):
        seeds.append(config.seed)
        return _yielding_client([])

    measure_decompose_instability(
        TASK,
        models=("test-model",),
        runs=2,
        perturb=True,
        client_factory=factory,
    )

    assert seeds == [1000, 1001, 1000]


def test_the_report_records_the_task_digest_it_measured():
    report = measure_decompose_instability(
        TASK,
        models=("test-model",),
        runs=1,
        perturb=False,
        client_factory=lambda config: _yielding_client([]),
    )

    from acceptance.rerun import task_digest

    assert report.provenance.task_digest == task_digest(TASK)
    assert report.provenance.determinism_mode == "record"
