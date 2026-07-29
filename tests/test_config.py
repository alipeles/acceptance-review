"""RunConfig controls, incl. the M3.5.2 scope-expansion policy (DR-081)."""

from acceptance.config import RunConfig, ScopeExpansionPolicy


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
    assert strict.provenance() == loose.provenance()
    assert "scope_expansion" not in strict.provenance().model_dump()


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
    assert config.provenance().seed == DEFAULT_SEED


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
