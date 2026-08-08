"""RunConfig controls, incl. the M3.5.2 scope-expansion policy (DR-081)."""

import pytest
from pydantic import ValidationError

from acceptance.config import (
    DEFAULT_MAPPING_BATCH_SIZE,
    RunConfig,
    ScopeExpansionPolicy,
    provenance_for,
)


def test_scope_expansion_policy_defaults_to_strict():
    # DR-081's recall-forward stance: surface more, let the user dismiss.
    assert RunConfig().scope_expansion_policy is ScopeExpansionPolicy.STRICT


def test_scope_expansion_policy_is_configurable():
    config = RunConfig(scope_expansion_policy=ScopeExpansionPolicy.LOOSE)
    assert config.scope_expansion_policy is ScopeExpansionPolicy.LOOSE


def test_scope_expansion_policy_round_trips():
    config = RunConfig(scope_expansion_policy=ScopeExpansionPolicy.LOOSE)
    restored = RunConfig.model_validate(config.model_dump())
    assert restored.scope_expansion_policy is ScopeExpansionPolicy.LOOSE


def test_scope_expansion_policy_is_not_a_determinism_control():
    # It tunes review interpretation (M3.5.3), not how the model is called, so
    # it must not leak into provenance (which feeds byte-identical replay and
    # M-B0.4 variance) — two configs differing only in policy are provenance-equal.
    strict = RunConfig(scope_expansion_policy=ScopeExpansionPolicy.STRICT)
    loose = RunConfig(scope_expansion_policy=ScopeExpansionPolicy.LOOSE)
    assert provenance_for(strict.build_client()) == provenance_for(loose.build_client())
    assert "scope_expansion" not in provenance_for(strict.build_client()).model_dump()


# --- determinism: the seed half of "fixed seed/temperature" (#154) ---


def test_a_seed_is_fixed_by_default():
    """`config.py` documents the Stage-1 determinism strategy as "fixed
    seed/temperature + cached transcripts", but `seed` defaulted to None, so
    half of it was never in force. A run must carry a seed unless one is
    deliberately cleared."""
    from acceptance.config import DEFAULT_SEED, RunConfig

    assert DEFAULT_SEED is not None
    assert RunConfig().seed == DEFAULT_SEED


def test_the_default_seed_reaches_both_the_model_call_and_the_provenance():
    """A seed that is configured but not sent changes nothing, and a seed that
    is sent but not recorded leaves a reader unable to tell what determinism
    controls produced a review (§13.6)."""
    from acceptance.config import DEFAULT_SEED, RunConfig

    config = RunConfig()

    assert config.build_client().seed == DEFAULT_SEED
    assert provenance_for(config.build_client()).controls_requested.seed == DEFAULT_SEED


def test_the_seed_is_part_of_the_request_so_changing_it_invalidates_transcripts():
    """The seed must be in the hashed request, so changing a determinism
    control forces re-verification rather than silently replaying responses
    produced under different settings."""
    from acceptance.config import RunConfig
    from acceptance.llm import request_key
    from acceptance.requirement.obligations import _Decomposition

    messages = [{"role": "system", "content": "x"}, {"role": "user", "content": "y"}]
    seeded = RunConfig(seed=1).build_client().build_request(messages, _Decomposition)
    other = RunConfig(seed=2).build_client().build_request(messages, _Decomposition)

    assert seeded["seed"] == 1
    assert request_key(seeded) != request_key(other)


def test_the_default_model_is_pinned_so_changing_it_is_deliberate():
    """The committed corpus is recorded against whatever model the tool runs
    (tests/prompts), and the benchmark's accuracy numbers are only comparable
    across runs of the same model. So the default is a pinned fact, not an
    incidental one — swapping it has to be a visible edit here, not a silent
    drift that quietly invalidates every recorded judgment.
    """
    assert RunConfig().model == "openai/gpt-5.4-mini"
    assert RunConfig().build_client().model == "openai/gpt-5.4-mini"


# --- provenance: what held, not what was asked for (#160) -------------------


def _dropping_client(model: str = "anthropic/claude-sonnet-5"):
    """A client whose provider discards every determinism control, as Anthropic
    does: it rejects `seed` outright and takes only `temperature=1`."""
    from tests.support import client_finding_nothing

    client = client_finding_nothing(model=model, temperature=0.0, seed=0)
    client._completion_fn.effective_controls = lambda model, **requested: {
        name: None for name in requested
    }
    return client


def test_provenance_reports_the_controls_the_provider_honoured():
    """A review that ran against a provider which threw our seed away must not
    report that seed as in force — that overstates its reproducibility (§13.6),
    and M-B0.4's variance disclosure reads exactly this field."""
    from acceptance.requirement.obligations import _Decomposition

    client = _dropping_client()
    client.complete([{"role": "user", "content": "decompose"}], _Decomposition)

    provenance = provenance_for(client)

    assert provenance.controls_requested.seed == 0
    assert provenance.controls_in_force.seed is None
    assert provenance.controls_in_force.temperature is None
    assert provenance.determinism() == "unpinned"


def test_provenance_of_a_run_that_made_no_model_call_is_indeterminate():
    """Not "the configured controls held". With no call there is no evidence
    either way, and an indeterminate answer is a valid result (§9.3)."""
    provenance = provenance_for(RunConfig().build_client())

    assert provenance.controls_in_force is None
    assert provenance.determinism() == "indeterminate"


def test_the_mapping_batch_size_is_a_run_control_with_a_fixed_default():
    assert RunConfig().mapping_batch_size == DEFAULT_MAPPING_BATCH_SIZE

    with pytest.raises(ValidationError):
        RunConfig(mapping_batch_size=0)  # a batch must hold something


def test_provenance_reports_the_partition_size_the_run_actually_used():
    """Read off the calls, not off configuration — the same rule as the other
    controls (#160). A review that reported a configured partition size while
    its calls ran unpartitioned would describe a run that did not happen."""
    from acceptance.requirement.obligations import _Decomposition

    from tests.support import client_finding_nothing

    client = client_finding_nothing()
    client.complete(
        [{"role": "user", "content": "batch 1"}],
        _Decomposition,
        {"size": 7},
        stage="decompose",
    )

    assert provenance_for(client).request_partition_sizes == {"decompose": 7}


def test_provenance_of_an_unpartitioned_run_reports_no_partition_size():
    """An EMPTY mapping means "no partitioned call was made", which is a
    different claim from a partition of size one — the same distinction
    controls_in_force draws between "ignored" and "nothing observed"."""
    from acceptance.requirement.obligations import _Decomposition

    from tests.support import client_finding_nothing

    client = client_finding_nothing()
    client.complete([{"role": "user", "content": "unpartitioned"}], _Decomposition)

    assert provenance_for(client).request_partition_sizes == {}


def test_one_builder_serves_both_the_cli_pipeline_and_the_benchmark():
    """The CLI and the benchmark each had their own provenance builder, so the
    benchmark could disagree with the tool it measures about how a review was
    produced. There is now one, and no config-sourced builder to drift back to."""
    from acceptance.benchmark import decomposition

    assert decomposition.provenance_for is provenance_for
    assert not hasattr(RunConfig, "provenance")


def test_the_benchmark_hooks_also_report_honoured_controls():
    """The behavioural half of the above: a benchmark hook's review carries the
    dropped controls, not the requested ones."""
    from acceptance.benchmark.case import (
        BenchmarkCase,
        BenchmarkCaseInputs,
        BenchmarkCaseSource,
        GroundTruthLabels,
        GroundTruthObligation,
    )
    from acceptance.benchmark.decomposition import decompose_case

    case = BenchmarkCase(
        case_id="provenance-probe",
        source=BenchmarkCaseSource(kind="archetype", identifier="provenance-probe"),
        inputs=BenchmarkCaseInputs(
            repo=".", base_revision="HEAD", head_revision="HEAD", task_text="# Task\nDo a thing.\n"
        ),
        ground_truth=GroundTruthLabels(
            obligations=[
                GroundTruthObligation(
                    id="do-a-thing",
                    description="Do a thing",
                    explicit=True,
                    evidence_class="unsupported",
                    evidence_rationale="Nothing exercises it.",
                    candidate_tests=[],
                )
            ]
        ),
    )

    scored = decompose_case(case, _dropping_client())

    assert scored.reviewer_output.provenance.determinism() == "unpinned"
    assert scored.reviewer_output.provenance.controls_in_force.seed is None
