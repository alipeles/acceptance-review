"""The native Anthropic adapter and the provider paths it sits beside (#432).

A Claude model goes through Anthropic's own SDK; every other provider goes
through LiteLLM. These tests pin what the native path sends, what it records,
and that what a call does — mark a reusable opening, join a batch — is read from
the adapter's declared capabilities rather than from the model's name.

Nothing here reaches the network: the SDK is answered by
`tests.support.FakeAnthropic`, and the LiteLLM call by LiteLLM's own
`mock_response`.
"""

from __future__ import annotations

import json

import anthropic
import httpx2
import pytest

from acceptance import llm, llm_batch, providers
from acceptance.config import DEFAULT_MODEL, RunConfig, provenance_for
from acceptance.llm import (
    ControlNotHonouredError,
    LLMError,
    Mode,
    ModelClient,
    SchemaValidationError,
    StrictResponseModel,
    TranscriptStore,
    request_key,
)
from acceptance.providers import ANTHROPIC_CAPABILITIES, LITELLM_CAPABILITIES, Capabilities
from acceptance.request_blocks import Block, BlockKind, assemble
from acceptance.usage import summarize
from tests.support import FakeAnthropic, use_fake_anthropic


class Verdict(StrictResponseModel):
    supported: bool
    rationale: str


MESSAGES = [
    {"role": "system", "content": "You are a careful reviewer."},
    {"role": "user", "content": "The obligation: bonds accrue daily."},
    {"role": "user", "content": "Is it supported?"},
]

_LONG = "sentence about the diff. " * 800


@pytest.fixture
def fake(monkeypatch) -> FakeAnthropic:
    monkeypatch.setattr(llm, "_FIRST_BACKOFF_SECONDS", 0.0)
    monkeypatch.setattr(llm_batch, "GATHER_SECONDS", 0.05)
    monkeypatch.setattr(llm_batch, "POLL_SECONDS", 0.01)
    return use_fake_anthropic(monkeypatch)


def _client(tmp_path, **kwargs) -> ModelClient:
    return RunConfig(mode=Mode.RECORD, transcript_root=tmp_path, **kwargs).build_client()


def _record(client: ModelClient, messages=MESSAGES, stage: str | None = None) -> dict:
    key = request_key(client.build_request(messages, Verdict, stage=stage))
    return json.loads(client.store.path_for(key).read_text())


def _long_request() -> list[dict]:
    return assemble(
        [
            Block(BlockKind.DIFF, _LONG),
            Block(BlockKind.INSTRUCTIONS, "judge it"),
            Block(BlockKind.SUBJECT, "this batch"),
        ]
    )


def _request() -> httpx2.Request:
    return httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


# --- which path a call takes ---------------------------------------------


def test_a_claude_run_goes_through_the_native_adapter(tmp_path, fake, monkeypatch):
    """The default configuration, on the default Claude model, never reaches
    LiteLLM: its one call is a Messages API request to the SDK."""

    def litellm_must_not_be_called(**kwargs):
        raise AssertionError("a Claude call went through LiteLLM")

    monkeypatch.setattr(llm, "_default_completion_fn", litellm_must_not_be_called)
    client = RunConfig(mode=Mode.RECORD, transcript_root=tmp_path).build_client()

    client.complete(MESSAGES, Verdict)

    assert len(fake.direct) == 1
    assert fake.direct[0]["model"] == "claude-sonnet-5-5"


def test_a_provider_with_no_native_adapter_completes_through_litellm(tmp_path, fake, monkeypatch):
    """The general path: an OpenAI model is answered through LiteLLM's own
    completion code (with its offline `mock_response`), and the Anthropic SDK
    is never touched."""
    real = llm._default_completion_fn
    reply = '{"supported": true, "rationale": "through litellm"}'
    monkeypatch.setattr(
        llm, "_default_completion_fn", lambda **kwargs: real(mock_response=reply, **kwargs)
    )
    client = ModelClient(
        model="openai/gpt-5.4-mini",
        mode=Mode.RECORD,
        store=TranscriptStore(tmp_path),
        key_check=lambda model: [],
    )

    verdict = client.complete(MESSAGES, Verdict)

    assert verdict.rationale == "through litellm"
    assert fake.direct == [] and fake.counted == [] and fake.retrieved == []


def test_an_injected_completion_function_answers_a_claude_model_itself(tmp_path, fake):
    """Every capability test injects one, so it must win over the native path."""
    from tests.support import _fake_response

    client = ModelClient(
        model=DEFAULT_MODEL,
        mode=Mode.RECORD,
        store=TranscriptStore(tmp_path),
        completion_fn=lambda **kwargs: _fake_response(
            '{"supported": false, "rationale": "injected"}'
        ),
    )

    assert client.complete(MESSAGES, Verdict).rationale == "injected"
    assert fake.direct == []


# --- what the native path sends --------------------------------------------


def test_the_request_is_the_messages_api_shape(tmp_path, fake):
    """System messages become system text; two user messages in a row become
    one turn of two blocks; the schema goes in `output_config.format`."""
    _client(tmp_path).complete(MESSAGES, Verdict)

    sent = fake.direct[0]
    assert sent["system"] == [{"type": "text", "text": "You are a careful reviewer."}]
    assert sent["messages"] == [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "The obligation: bonds accrue daily."},
                {"type": "text", "text": "Is it supported?"},
            ],
        }
    ]
    schema = sent["output_config"]["format"]
    assert schema["type"] == "json_schema"
    assert schema["schema"] == anthropic.transform_schema(
        llm.inline_schema_refs(Verdict.model_json_schema())
    )


def test_the_output_ceiling_is_the_models_own_and_asked_once(tmp_path, fake):
    fake.max_output = 64_000
    client = _client(tmp_path)

    client.complete(MESSAGES, Verdict)
    client.complete([{"role": "user", "content": "A second question."}], Verdict)

    assert [sent["max_tokens"] for sent in fake.direct] == [64_000, 64_000]
    assert fake.retrieved == ["claude-sonnet-5-5"]


def test_a_direct_call_carries_an_explicit_timeout(tmp_path, fake):
    """Left unset, the SDK refuses a non-streaming call whose output ceiling
    could outlast its default timeout."""
    _client(tmp_path).complete(MESSAGES, Verdict)

    assert fake.timeouts == [providers._REQUEST_TIMEOUT_SECONDS]


def test_no_temperature_or_seed_is_sent_and_the_recording_says_neither_applied(tmp_path, fake):
    """Claude refuses a temperature and has no seed. The run still asks for
    both — they are in the hashed request — and the record says neither was
    applied, which is what provenance then reports."""
    client = _client(tmp_path)
    client.complete(MESSAGES, Verdict)

    sent = fake.direct[0]
    assert "temperature" not in sent and "seed" not in sent
    record = _record(client)
    assert record["request"]["temperature"] == 0.0 and record["request"]["seed"] == 0
    assert record["controls_applied"] == {"temperature": None, "seed": None}
    in_force = provenance_for(client).controls_in_force
    assert in_force is not None and in_force.temperature is None and in_force.seed is None


def test_an_accepted_effort_is_sent_in_output_config(tmp_path, fake):
    client = _client(tmp_path, stage_reasoning={"judge": "high"})

    client.complete(MESSAGES, Verdict, stage="judge")

    assert fake.direct[0]["output_config"]["effort"] == "high"
    assert _record(client, stage="judge")["controls_applied"]["reasoning_effort"] == "high"


def test_an_effort_the_adapter_does_not_accept_stops_the_run_before_the_call(tmp_path, fake):
    client = _client(tmp_path, stage_reasoning={"judge": "minimal"})

    with pytest.raises(ControlNotHonouredError, match="minimal"):
        client.complete(MESSAGES, Verdict, stage="judge")

    assert fake.direct == [] and fake.retrieved == []


# --- what the native path records ------------------------------------------


def test_usage_comes_from_anthropics_response_under_the_usual_names(tmp_path, fake):
    """`prompt_tokens` is the sum of Anthropic's three input counts, as it was
    when LiteLLM recorded it, so the spend summary reads both the same way."""
    fake.usage = {
        "input_tokens": 100,
        "output_tokens": 50,
        "cache_read_input_tokens": 4000,
        "cache_creation_input_tokens": 600,
    }
    client = _client(tmp_path)
    client.complete(MESSAGES, Verdict)

    usage = _record(client)["usage"]
    assert usage["prompt_tokens"] == 4700
    assert usage["completion_tokens"] == 50
    assert usage["total_tokens"] == 4750
    assert usage["cached_tokens"] == 4000
    assert usage["cache_creation_tokens"] == 600


def test_the_cost_is_priced_from_anthropics_token_counts(tmp_path, fake):
    """Sonnet 5.5: $2 input, $10 output, $0.20 cache read, $2.50 cache write,
    per million tokens."""
    fake.usage = {
        "input_tokens": 1_000_000,
        "output_tokens": 100_000,
        "cache_read_input_tokens": 2_000_000,
        "cache_creation_input_tokens": 400_000,
    }
    client = _client(tmp_path)
    client.complete(MESSAGES, Verdict)

    expected = 2.00 + 1.00 + 0.40 + 1.00
    assert _record(client)["usage"]["cost_usd"] == pytest.approx(expected)
    assert summarize(client.observed_calls).anthropic_run_spend_usd == pytest.approx(expected)


def test_a_batched_call_is_priced_at_the_batch_rate_when_it_is_priced(tmp_path, fake):
    """No correction afterwards: the adapter prices the call at the rate it was
    billed at."""
    assert providers.anthropic_usage(
        {"input_tokens": 1_000_000, "output_tokens": 0}, DEFAULT_MODEL, batched=True
    )["cost_usd"] == pytest.approx(1.00)


def test_a_model_without_a_price_records_tokens_and_no_cost():
    usage = providers.anthropic_usage(
        {"input_tokens": 10, "output_tokens": 5}, "anthropic/claude-unpriced-9", batched=False
    )

    assert usage["prompt_tokens"] == 10 and "cost_usd" not in usage


def test_a_count_anthropic_did_not_report_is_omitted_not_zeroed():
    usage = providers.anthropic_usage(
        {"input_tokens": 10, "output_tokens": 5}, DEFAULT_MODEL, batched=False
    )

    assert "cached_tokens" not in usage and "cache_creation_tokens" not in usage


def test_the_stop_reason_is_anthropics_own(tmp_path, fake):
    client = _client(tmp_path)
    client.complete(MESSAGES, Verdict)

    assert _record(client)["stop_reason"] == "end_turn"


def test_thinking_blocks_are_not_part_of_the_answer():
    reply = providers.AnthropicAdapter.reply(
        {
            "content": [
                {"type": "thinking", "thinking": "", "signature": "x"},
                {"type": "text", "text": '{"supported": true, '},
                {"type": "text", "text": '"rationale": "ok"}'},
            ],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 1, "output_tokens": 1},
        },
        DEFAULT_MODEL,
        batched=False,
    )

    assert json.loads(reply.content) == {"supported": True, "rationale": "ok"}


def test_a_reply_that_does_not_match_the_schema_is_rejected_with_the_usual_error(tmp_path, fake):
    """The same typed error as any other provider's, and nothing is recorded."""
    fake.responder = lambda params: '{"supported": "maybe"}'
    client = _client(tmp_path)

    with pytest.raises(SchemaValidationError, match="Verdict"):
        client.complete(MESSAGES, Verdict)

    assert list(tmp_path.glob("*.json")) == []


def test_a_refusal_with_no_text_is_rejected_with_the_usual_error(tmp_path, fake):
    def refuse(params):
        return ""

    fake.responder = refuse
    with pytest.raises(SchemaValidationError):
        _client(tmp_path).complete(MESSAGES, Verdict)


def test_a_recorded_claude_call_replays_with_no_sdk_at_all(tmp_path, fake, monkeypatch):
    recorded = _client(tmp_path).complete(MESSAGES, Verdict)
    calls = fake.calls

    def refuse():
        raise AssertionError("replay reached the SDK")

    monkeypatch.setattr(providers, "_default_sdk_client", refuse)
    replayed = RunConfig(mode=Mode.REPLAY, transcript_root=tmp_path).build_client()

    assert replayed.complete(MESSAGES, Verdict) == recorded
    assert fake.calls == calls


# --- failures ---------------------------------------------------------------


def test_a_connection_failure_is_asked_again(tmp_path, fake):
    fake.failures = [anthropic.APIConnectionError(request=_request())]
    client = _client(tmp_path)

    assert client.complete(MESSAGES, Verdict).supported
    assert len(fake.direct) == 2


def test_an_overloaded_provider_is_asked_again(tmp_path, fake):
    overloaded = httpx2.Response(529, request=_request())
    fake.failures = [anthropic.InternalServerError("overloaded", response=overloaded, body=None)]

    assert _client(tmp_path).complete(MESSAGES, Verdict).supported
    assert len(fake.direct) == 2


def test_a_bad_request_is_not_asked_again(tmp_path, fake):
    bad = httpx2.Response(400, request=_request())
    fake.failures = [anthropic.BadRequestError("bad schema", response=bad, body=None)]

    with pytest.raises(LLMError, match="status 400 and was not retried"):
        _client(tmp_path).complete(MESSAGES, Verdict)

    assert len(fake.direct) == 1


def test_the_sdk_does_not_retry_on_its_own(monkeypatch):
    """The client already retries; both together would multiply every outage.

    The suite replaces `_default_sdk_client` with a guard, so the real one is
    loaded from a fresh copy of the module. Building the SDK client makes no
    call."""
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("_fresh_providers", providers.__file__)
    fresh = importlib.util.module_from_spec(spec)
    # Dataclasses look their module up while being defined.
    monkeypatch.setitem(sys.modules, "_fresh_providers", fresh)
    spec.loader.exec_module(fresh)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-never-sent")

    assert fresh._default_sdk_client().max_retries == 0


# --- capabilities, not names -----------------------------------------------


def test_a_long_opening_is_marked_with_anthropics_exact_count(tmp_path, fake):
    client = _client(tmp_path)

    client.complete(_long_request(), Verdict)

    turn = fake.direct[0]["messages"][0]["content"]
    assert turn[0]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in turn[-1]
    assert len(fake.counted) == 1


def test_an_opening_is_counted_once_however_many_calls_share_it(tmp_path, fake):
    client = _client(tmp_path)
    first = _long_request()
    second = [*first[:2], {"role": "user", "content": "another batch"}]

    client.complete(first, Verdict)
    client.complete(second, Verdict)

    assert len(fake.direct) == 2 and len(fake.counted) == 1


def test_an_opening_under_the_models_minimum_is_not_marked(tmp_path, fake):
    fake.tokens_per_count = 511
    _client(tmp_path).complete(_long_request(), Verdict)

    assert "cache_control" not in json.dumps(fake.direct[0])


def test_the_breakpoint_follows_the_declared_capability(tmp_path, fake, monkeypatch):
    """Same model, same request: an adapter that declares no breakpoints sends
    none. The model's name does not decide it."""
    monkeypatch.setattr(
        providers.AnthropicAdapter,
        "capabilities",
        Capabilities(**{**ANTHROPIC_CAPABILITIES.__dict__, "cache_breakpoints": False}),
    )

    _client(tmp_path).complete(_long_request(), Verdict)

    assert "cache_control" not in json.dumps(fake.direct[0])
    assert fake.counted == []


def test_batching_follows_the_declared_capability(tmp_path, fake, monkeypatch):
    monkeypatch.setattr(
        providers.AnthropicAdapter,
        "capabilities",
        Capabilities(**{**ANTHROPIC_CAPABILITIES.__dict__, "batching": False}),
    )
    client = _client(tmp_path, batch=True)

    client.complete(MESSAGES, Verdict)

    assert fake.batches == [] and len(fake.direct) == 1
    assert "sent_via" not in _record(client)


def test_the_litellm_path_declares_neither_breakpoints_nor_batching():
    assert not LITELLM_CAPABILITIES.cache_breakpoints
    assert not LITELLM_CAPABILITIES.batching
    assert ANTHROPIC_CAPABILITIES.cache_breakpoints and ANTHROPIC_CAPABILITIES.batching


# --- keys -------------------------------------------------------------------


def test_a_missing_anthropic_key_is_named_before_any_call(tmp_path, fake, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    client = _client(tmp_path)

    assert client.missing_keys_by_model().get(DEFAULT_MODEL) == ["ANTHROPIC_API_KEY"]
    with pytest.raises(llm.MissingKeyError, match="ANTHROPIC_API_KEY"):
        client.complete(MESSAGES, Verdict)
    assert fake.direct == []
