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
