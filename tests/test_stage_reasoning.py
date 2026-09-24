"""A stage may run with a reasoning effort, and nothing else moves when it does (#366)."""

import json
from types import SimpleNamespace

import pytest
from pydantic import BaseModel, ValidationError

from acceptance.config import RunConfig, provenance_for
from acceptance.llm import (
    ControlNotHonouredError,
    Mode,
    ModelClient,
    TranscriptStore,
    _extract_usage,
    request_key,
)
from acceptance.review_state import StageControls
from acceptance.usage import render, summarize


class Verdict(BaseModel):
    supported: bool
    rationale: str


MESSAGES = [{"role": "user", "content": "Does the test discriminate?"}]
DESCRIPTOR = "mutation descriptor"
DEFECT_MATCH = "mutation verification: defect match"
ANSWER = '{"supported": true, "rationale": "ok"}'


def _response(content: str = ANSWER, reasoning_tokens: int | None = None):
    usage = SimpleNamespace(prompt_tokens=11, completion_tokens=7, total_tokens=18)
    if reasoning_tokens is not None:
        usage.completion_tokens_details = SimpleNamespace(reasoning_tokens=reasoning_tokens)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=usage,
    )


def _provider(drops: tuple[str, ...] = (), reasoning_tokens: int | None = None):
    """A completion function with a provider's habit of discarding controls.

    `effective_controls` stands in for LiteLLM's offline answer, the way
    `_default_completion_fn` carries it. `drops` names what this provider
    discards; everything else is honoured as asked.
    """
    calls = []

    def completion_fn(**kwargs):
        calls.append(kwargs)
        return _response(reasoning_tokens=reasoning_tokens)

    def effective_controls(model, **requested):
        return {name: (None if name in drops else value) for name, value in requested.items()}

    completion_fn.calls = calls
    completion_fn.effective_controls = effective_controls
    return completion_fn


def _client(store, completion_fn=None, **kwargs) -> ModelClient:
    return ModelClient(
        model="openai/gpt-5.4-mini",
        mode=Mode.RECORD,
        store=store,
        seed=7,
        completion_fn=completion_fn or _provider(),
        **kwargs,
    )


@pytest.fixture
def store(tmp_path):
    return TranscriptStore(tmp_path / "transcripts")


# --- request keys -----------------------------------------------------------

# Computed from `45c2958`, the commit before this setting existed, by building
# exactly these requests. Every recording on disk was keyed by that code, so a
# key that moves here is a corpus that stops replaying.
KEYS_RECORDED_BEFORE_THE_SETTING = {
    DESCRIPTOR: "db0d75f3c691b2fe0d704a1ad0ace0a85519ca8db1a4ab6fd4854ef07468fe18",
    DEFECT_MATCH: "bafde8d752f4dbea9aea54cb897cc56eac6b8c8411cdf253052a16ddc2210b4b",
}
PARTITIONED_KEY_RECORDED_BEFORE_THE_SETTING = (
    "c764628650d115f4a38dce1430b6e05b368b2b62c7dc2a79ab6a18e56256e0f8"
)


def _keys(client: ModelClient) -> dict[str, str]:
    return {
        stage: request_key(client.build_request(MESSAGES, Verdict, stage=stage))
        for stage in (DESCRIPTOR, DEFECT_MATCH)
    }


def _pinned_client(**kwargs) -> ModelClient:
    return ModelClient(
        model="openai/gpt-5.4-mini",
        seed=7,
        stage_models={DEFECT_MATCH: "openai/gpt-5.4"},
        **kwargs,
    )


def test_with_no_stage_configured_every_key_is_the_one_recorded_before_the_setting():
    client = _pinned_client()

    assert _keys(client) == KEYS_RECORDED_BEFORE_THE_SETTING
    partitioned = client.build_request(
        MESSAGES,
        Verdict,
        partition={"index": 0, "size": 4},
        stage_controls={"distance_threshold": 0.1},
        stage="obligation linking",
    )
    assert request_key(partitioned) == PARTITIONED_KEY_RECORDED_BEFORE_THE_SETTING


def test_the_default_run_configuration_configures_no_stage():
    assert RunConfig().stage_reasoning == {}
    assert RunConfig().build_client().reasoning_for(DESCRIPTOR) is None


def test_configuring_one_stage_moves_its_key_and_no_other_stage_key():
    keys = _keys(_pinned_client(stage_reasoning={DESCRIPTOR: "low"}))

    assert keys[DESCRIPTOR] != KEYS_RECORDED_BEFORE_THE_SETTING[DESCRIPTOR]
    assert keys[DEFECT_MATCH] == KEYS_RECORDED_BEFORE_THE_SETTING[DEFECT_MATCH]


def test_the_effort_is_in_the_request_only_when_its_stage_sets_one():
    client = _pinned_client(stage_reasoning={DESCRIPTOR: "high"})

    assert client.build_request(MESSAGES, Verdict, stage=DESCRIPTOR)["reasoning_effort"] == "high"
    assert "reasoning_effort" not in client.build_request(MESSAGES, Verdict, stage=DEFECT_MATCH)


def test_two_efforts_on_one_stage_are_two_different_requests():
    low = _keys(_pinned_client(stage_reasoning={DESCRIPTOR: "low"}))[DESCRIPTOR]
    high = _keys(_pinned_client(stage_reasoning={DESCRIPTOR: "high"}))[DESCRIPTOR]

    assert low != high


def test_run_config_reaches_the_client():
    client = RunConfig(stage_reasoning={DESCRIPTOR: "medium"}).build_client()

    assert client.reasoning_for(DESCRIPTOR) == "medium"
    assert client.reasoning_for(DEFECT_MATCH) is None


def test_run_config_refuses_an_effort_that_is_not_one():
    with pytest.raises(ValidationError):
        RunConfig(stage_reasoning={DESCRIPTOR: "hgih"})


# --- the effort reaches the provider, or the run stops ----------------------


def test_the_effort_is_sent_to_the_provider(store):
    provider = _provider()
    client = _client(store, provider, stage_reasoning={DESCRIPTOR: "low"})

    client.complete(MESSAGES, Verdict, stage=DESCRIPTOR)
    client.complete(MESSAGES, Verdict, stage=DEFECT_MATCH)

    assert provider.calls[0]["reasoning_effort"] == "low"
    assert "reasoning_effort" not in provider.calls[1]


def test_a_dropped_effort_stops_the_run_before_the_call(store):
    provider = _provider(drops=("reasoning_effort",))
    client = _client(store, provider, stage_reasoning={DESCRIPTOR: "low"})

    with pytest.raises(ControlNotHonouredError) as raised:
        client.complete(MESSAGES, Verdict, stage=DESCRIPTOR)

    assert DESCRIPTOR in str(raised.value)
    assert "openai/gpt-5.4-mini" in str(raised.value)
    assert provider.calls == []
    assert not store.root.exists() or not any(store.root.iterdir())


def test_a_dropped_effort_on_another_stage_does_not_stop_a_stage_without_one(store):
    provider = _provider(drops=("reasoning_effort",))
    client = _client(store, provider, stage_reasoning={DESCRIPTOR: "low"})

    client.complete(MESSAGES, Verdict, stage=DEFECT_MATCH)

    assert len(provider.calls) == 1


def test_litellm_itself_is_what_stops_a_model_that_takes_no_effort(store):
    """The real offline answer, not a stand-in: `gpt-4o` takes no reasoning
    effort, and LiteLLM's `drop_params` would discard it without a word.

    The completion function is a tripwire carrying LiteLLM's real reporter,
    rather than the default one, so that if the check ever stops working this
    test fails instead of making a live, billed call."""
    from acceptance.llm import _litellm_effective_controls

    def tripwire(**kwargs):
        raise AssertionError("the call was made; the effort check did not stop it")

    tripwire.effective_controls = _litellm_effective_controls
    client = ModelClient(
        model="openai/gpt-4o",
        mode=Mode.RECORD,
        store=store,
        seed=7,
        completion_fn=tripwire,
        stage_reasoning={DESCRIPTOR: "low"},
    )

    with pytest.raises(ControlNotHonouredError, match="openai/gpt-4o"):
        client.complete(MESSAGES, Verdict, stage=DESCRIPTOR)


def test_litellm_keeps_the_effort_and_drops_the_temperature_on_gpt_5_4():
    """What the provenance tests below assume about OpenAI, checked against
    LiteLLM rather than asserted. Offline; no call is made."""
    from acceptance.llm import _litellm_effective_controls

    applied = _litellm_effective_controls(
        "openai/gpt-5.4", temperature=0.0, seed=7, reasoning_effort="low"
    )

    assert applied == {"temperature": None, "seed": 7, "reasoning_effort": "low"}


# --- provenance says what reached the provider, per stage -------------------


def test_provenance_records_each_stage_controls_as_honoured(store):
    """OpenAI takes no temperature on a reasoning call. The reasoning stage must
    not be recorded at temperature 0, and the stage beside it must not lose its
    0 because of it."""
    provider = _provider()

    # OpenAI's habit, as LiteLLM reports it: temperature is dropped only
    # from a call that reasons.
    def effective_controls(model, **requested):
        dropped = "reasoning_effort" in requested
        return {
            name: (None if dropped and name == "temperature" else value)
            for name, value in requested.items()
        }

    provider.effective_controls = effective_controls
    client = _client(store, provider, stage_reasoning={DESCRIPTOR: "low"})

    client.complete(MESSAGES, Verdict, stage=DESCRIPTOR)
    client.complete(MESSAGES, Verdict, stage=DEFECT_MATCH)
    provenance = provenance_for(client)

    assert provenance.stage_controls == {
        DESCRIPTOR: StageControls(temperature=None, seed=7, reasoning_effort="low"),
        DEFECT_MATCH: StageControls(temperature=0.0, seed=7, reasoning_effort=None),
    }
    # The run as a whole is no longer pinned at temperature 0, and says so.
    assert provenance.controls_in_force.temperature is None
    assert provenance.determinism() == "unpinned"


def test_a_replayed_stage_reports_the_controls_its_recording_ran_under(store):
    recorded = _client(store, stage_reasoning={DESCRIPTOR: "low"})
    recorded.complete(MESSAGES, Verdict, stage=DESCRIPTOR)

    def no_call(**kwargs):
        raise AssertionError("a live call was issued during replay")

    replayed = ModelClient(
        model="openai/gpt-5.4-mini",
        mode=Mode.REPLAY,
        store=store,
        seed=7,
        completion_fn=no_call,
        stage_reasoning={DESCRIPTOR: "low"},
    )
    replayed.complete(MESSAGES, Verdict, stage=DESCRIPTOR)

    assert replayed.stage_controls_in_force == {
        DESCRIPTOR: {"temperature": 0.0, "seed": 7, "reasoning_effort": "low"}
    }


def test_a_recording_with_no_controls_known_claims_none(store):
    client = _client(store)
    request = client.build_request(MESSAGES, Verdict, stage=DEFECT_MATCH)
    # A transcript from before controls were recorded.
    store.write(request_key(request), {"request": request, "response": ANSWER, "usage": {}})

    client.complete(MESSAGES, Verdict, stage=DEFECT_MATCH)

    assert client.stage_controls_in_force == {
        DEFECT_MATCH: {"temperature": None, "seed": None, "reasoning_effort": None}
    }


def test_an_embedding_is_not_a_stage_that_dropped_its_controls(store):
    def embedding_fn(**kwargs):
        return {"data": [{"embedding": [0.1, 0.2]} for _ in kwargs["input"]]}

    client = _client(store, embedding_model="voyage/voyage-3.5-lite", embedding_fn=embedding_fn)

    client.embed(["one", "two"], stage="obligation linking")

    assert client.stage_controls_in_force == {}


# --- reasoning tokens --------------------------------------------------------


def test_a_call_records_its_reasoning_tokens(store):
    client = _client(store, _provider(reasoning_tokens=5), stage_reasoning={DESCRIPTOR: "low"})

    client.complete(MESSAGES, Verdict, stage=DESCRIPTOR)
    request = client.build_request(MESSAGES, Verdict, stage=DESCRIPTOR)
    record = json.loads(store.path_for(request_key(request)).read_text())

    assert record["usage"]["reasoning_tokens"] == 5


def test_an_unreported_reasoning_count_is_omitted_not_zero():
    assert "reasoning_tokens" not in _extract_usage(_response())


def test_the_footer_shows_reasoning_tokens_only_when_a_stage_reasoned():
    reasoned = [
        {"stage": DESCRIPTOR, "served_from": "provider", "usage": {"reasoning_tokens": 1234}},
        {"stage": DEFECT_MATCH, "served_from": "provider", "usage": {"completion_tokens": 9}},
    ]
    plain = [{"stage": DEFECT_MATCH, "served_from": "provider", "usage": {"completion_tokens": 9}}]

    shown = render(summarize(reasoned))
    assert "reasoning" in shown.splitlines()[1]
    assert "1,234" in shown
    assert "reasoning" not in render(summarize(plain))


def test_the_cost_of_a_reasoning_call_includes_its_reasoning_tokens():
    """Reasoning tokens are billed as output. Priced by LiteLLM, offline: a call
    whose output was mostly reasoning must cost what all of its output costs,
    not what its visible answer costs."""
    import litellm  # noqa: F401 — `_extract_usage` prices only when it is loaded
    from litellm import ModelResponse

    def priced(completion_tokens: int, reasoning_tokens: int | None) -> float:
        usage = {
            "prompt_tokens": 100,
            "completion_tokens": completion_tokens,
            "total_tokens": 100 + completion_tokens,
        }
        if reasoning_tokens is not None:
            usage["completion_tokens_details"] = {"reasoning_tokens": reasoning_tokens}
        response = ModelResponse(
            model="gpt-5.4",
            choices=[{"message": {"role": "assistant", "content": ANSWER}}],
            usage=usage,
        )
        return _extract_usage(response)["cost_usd"]

    with_reasoning = priced(completion_tokens=1000, reasoning_tokens=900)

    assert with_reasoning == pytest.approx(priced(completion_tokens=1000, reasoning_tokens=None))
    assert with_reasoning > priced(completion_tokens=100, reasoning_tokens=None)
