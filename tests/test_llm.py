import json
import sys
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from acceptance.llm import (
    Mode,
    ModelClient,
    SchemaValidationError,
    TranscriptNotFoundError,
    TranscriptStore,
    request_key,
)


class Verdict(BaseModel):
    """Stand-in for a real judgment schema (obligations land in M1)."""

    supported: bool
    rationale: str


MESSAGES = [{"role": "user", "content": "Does the test discriminate?"}]


def _fake_response(content: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=11, completion_tokens=7, total_tokens=18),
    )


def _recorder(content: str):
    """A completion_fn that returns `content` and counts its calls."""
    calls = []

    def completion_fn(**kwargs):
        calls.append(kwargs)
        return _fake_response(content)

    completion_fn.calls = calls
    return completion_fn


def _exploding_completion_fn(**kwargs):
    raise AssertionError("a live model call was issued during replay")


@pytest.fixture
def store(tmp_path):
    return TranscriptStore(tmp_path / "transcripts")


def test_record_mode_validates_and_persists_a_transcript(store):
    completion_fn = _recorder('{"supported": true, "rationale": "boundary case asserted"}')
    client = ModelClient(
        model="anthropic/claude-sonnet-5",
        mode=Mode.RECORD,
        store=store,
        completion_fn=completion_fn,
    )

    verdict = client.complete(MESSAGES, Verdict)

    assert verdict == Verdict(supported=True, rationale="boundary case asserted")
    assert len(completion_fn.calls) == 1
    key = request_key(client.build_request(MESSAGES, Verdict))
    assert store.path_for(key).is_file()


def test_recorded_transcript_replays_with_zero_live_calls(store):
    recorded = ModelClient(
        model="anthropic/claude-sonnet-5",
        mode=Mode.RECORD,
        store=store,
        completion_fn=_recorder('{"supported": false, "rationale": "no assertion on the result"}'),
    )
    original = recorded.complete(MESSAGES, Verdict)

    replayed = ModelClient(
        model="anthropic/claude-sonnet-5",
        mode=Mode.REPLAY,
        store=store,
        completion_fn=_exploding_completion_fn,
    )

    assert replayed.complete(MESSAGES, Verdict) == original


def test_record_mode_serves_an_existing_transcript_without_re_billing(store):
    """RECORD is record-if-missing: an already-recorded request is not re-called."""
    completion_fn = _recorder('{"supported": true, "rationale": "ok"}')
    client = ModelClient(
        model="anthropic/claude-sonnet-5",
        mode=Mode.RECORD,
        store=store,
        completion_fn=completion_fn,
    )

    first = client.complete(MESSAGES, Verdict)
    second = client.complete(MESSAGES, Verdict)

    assert first == second
    assert len(completion_fn.calls) == 1


def test_replay_without_a_transcript_raises_rather_than_calling_live(store):
    client = ModelClient(
        model="anthropic/claude-sonnet-5",
        mode=Mode.REPLAY,
        store=store,
        completion_fn=_exploding_completion_fn,
    )

    with pytest.raises(TranscriptNotFoundError):
        client.complete(MESSAGES, Verdict)


def test_malformed_json_is_rejected_with_a_typed_error(store):
    client = ModelClient(
        model="anthropic/claude-sonnet-5",
        mode=Mode.RECORD,
        store=store,
        completion_fn=_recorder("I think the test looks fine, honestly."),
    )

    with pytest.raises(SchemaValidationError):
        client.complete(MESSAGES, Verdict)


def test_schema_violating_response_is_rejected_with_a_typed_error(store):
    client = ModelClient(
        model="anthropic/claude-sonnet-5",
        mode=Mode.RECORD,
        store=store,
        completion_fn=_recorder('{"supported": "yes-ish"}'),
    )

    with pytest.raises(SchemaValidationError):
        client.complete(MESSAGES, Verdict)


def test_non_text_content_is_rejected_with_a_typed_error(store):
    def completion_fn(**kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=None))],
            usage=None,
        )

    client = ModelClient(
        model="anthropic/claude-sonnet-5",
        mode=Mode.RECORD,
        store=store,
        completion_fn=completion_fn,
    )

    with pytest.raises(SchemaValidationError):
        client.complete(MESSAGES, Verdict)


def test_request_key_is_stable_across_clients(store):
    def build():
        client = ModelClient(model="anthropic/claude-sonnet-5", store=store)
        return client.build_request(MESSAGES, Verdict)

    assert request_key(build()) == request_key(build())


@pytest.mark.parametrize(
    "kwargs",
    [
        {"model": "openai/gpt-5"},
        {"temperature": 0.7},
        {"seed": 42},
    ],
)
def test_request_key_distinguishes_call_parameters(store, kwargs):
    base = ModelClient(model="anthropic/claude-sonnet-5", store=store)
    varied = ModelClient(**{"model": "anthropic/claude-sonnet-5", "store": store, **kwargs})

    assert request_key(base.build_request(MESSAGES, Verdict)) != request_key(
        varied.build_request(MESSAGES, Verdict)
    )


def test_request_key_distinguishes_prompt_and_schema(store):
    client = ModelClient(model="anthropic/claude-sonnet-5", store=store)

    class OtherVerdict(BaseModel):
        supported: bool

    assert request_key(client.build_request(MESSAGES, Verdict)) != request_key(
        client.build_request([{"role": "user", "content": "different"}], Verdict)
    )
    assert request_key(client.build_request(MESSAGES, Verdict)) != request_key(
        client.build_request(MESSAGES, OtherVerdict)
    )


def test_transcripts_record_no_wall_clock_state(store):
    """Determinism guard: re-running the same input must reproduce byte-identical
    state, so transcripts carry no timestamps or run ids (M0.5)."""
    client = ModelClient(
        model="anthropic/claude-sonnet-5",
        mode=Mode.RECORD,
        store=store,
        completion_fn=_recorder('{"supported": true, "rationale": "ok"}'),
    )
    client.complete(MESSAGES, Verdict)

    key = request_key(client.build_request(MESSAGES, Verdict))
    record = json.loads(store.path_for(key).read_text())

    assert set(record) == {"request", "response", "usage"}
    assert set(record["usage"]) <= {
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "cost_usd",
    }


def test_harness_does_not_import_the_provider_stack(store):
    """Capability tests run off transcripts with no live calls (CLAUDE.md M0.4/M0.5),
    so an injected completion_fn must never drag LiteLLM in."""
    already_imported = "litellm" in sys.modules
    client = ModelClient(
        model="anthropic/claude-sonnet-5",
        mode=Mode.RECORD,
        store=store,
        completion_fn=_recorder('{"supported": true, "rationale": "ok"}'),
    )

    client.complete(MESSAGES, Verdict)

    assert ("litellm" in sys.modules) == already_imported


def test_recorded_transcripts_are_byte_identical_for_the_same_call(tmp_path):
    """Two recordings of the same request/response produce identical bytes."""
    content = '{"supported": true, "rationale": "ok"}'
    written = []
    for name in ("first", "second"):
        store = TranscriptStore(tmp_path / name)
        client = ModelClient(
            model="anthropic/claude-sonnet-5",
            mode=Mode.RECORD,
            store=store,
            completion_fn=_recorder(content),
        )
        client.complete(MESSAGES, Verdict)
        key = request_key(client.build_request(MESSAGES, Verdict))
        written.append(store.path_for(key).read_bytes())

    assert written[0] == written[1]
