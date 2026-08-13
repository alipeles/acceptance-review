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
    inline_schema_refs,
    request_key,
)
from acceptance.review_state import UnrequestedChangeDisposition as UnrequestedDisposition


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

    # `stop_reason` (#266) is a property of the response, not of when it was
    # made, so it belongs in a transcript this guard is happy with — the guard is
    # about wall-clock state, and an exhaustive key set is how it stays able to
    # catch a field that is.
    assert set(record) == {"request", "response", "usage", "stop_reason", "controls_applied"}
    assert set(record["usage"]) <= {
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "cost_usd",
    }


@pytest.mark.parametrize("finish_reason", ["stop", "length"])
def test_a_transcript_records_why_the_model_stopped_generating(store, finish_reason):
    """#266: the transcript must say whether the answer was finished or cut off.

    `length` is the case that motivated it. Diagnosing #266 meant separating a
    truncated response from a short-but-complete one, and with no stop reason
    recorded that had to be reconstructed from token counts and whether the JSON
    happened to parse — for a stage whose whole symptom was returning fewer
    judgments than it was asked for.

    Both values are exercised because recording only the interesting one would
    be indistinguishable from recording a constant."""
    response = _fake_response('{"supported": true, "rationale": "ok"}')
    response.choices[0].finish_reason = finish_reason

    client = ModelClient(
        model="anthropic/claude-sonnet-5",
        mode=Mode.RECORD,
        store=store,
        completion_fn=lambda **kwargs: response,
    )
    client.complete(MESSAGES, Verdict)

    key = request_key(client.build_request(MESSAGES, Verdict))
    record = json.loads(store.path_for(key).read_text())

    assert record["stop_reason"] == finish_reason


def test_a_provider_reporting_no_stop_reason_records_none(store):
    """`None` is a real answer, not a gap to fill. Inventing `stop` for a
    provider that said nothing would assert the response was complete on no
    evidence — the precise claim #266 needed to be able to distrust."""
    client = ModelClient(
        model="anthropic/claude-sonnet-5",
        mode=Mode.RECORD,
        store=store,
        completion_fn=_recorder('{"supported": true, "rationale": "ok"}'),
    )
    client.complete(MESSAGES, Verdict)

    key = request_key(client.build_request(MESSAGES, Verdict))
    record = json.loads(store.path_for(key).read_text())

    assert record["stop_reason"] is None


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


# --- provider-agnosticism (M0.4) -------------------------------------------
# The harness routes through LiteLLM so the model can be swapped to compare
# quality and cost. That only holds if provider differences are absorbed here
# rather than surfacing as crashes, and if the controls a provider silently
# discards are recorded instead of assumed.


class Disposition(BaseModel):
    # Shaped like the real response models: an enum field, which pydantic
    # factors into a definitions block and refers to indirectly. Kept as a
    # comment, not a docstring — a docstring becomes the schema's `description`,
    # so words like the one being asserted on would leak into the payload.
    disposition: UnrequestedDisposition
    rationale: str


def test_the_schema_sent_to_the_provider_has_no_ref_indirection(store):
    """`$defs`/`$ref` is not a cosmetic difference. Anthropic returns the reply
    nested under `parameters`, and both providers judge worse — the enum's
    allowed values have to be visible at the field (#158)."""
    completion_fn = _recorder('{"disposition": "risky", "rationale": "ok"}')
    client = ModelClient(
        model="anthropic/claude-sonnet-5",
        mode=Mode.RECORD,
        store=store,
        completion_fn=completion_fn,
    )
    assert "$defs" in Disposition.model_json_schema()  # the trap being avoided

    client.complete(MESSAGES, Disposition)

    sent = completion_fn.calls[0]["response_format"]["json_schema"]
    assert sent["name"] == "Disposition"
    rendered = json.dumps(sent["schema"])
    assert "$ref" not in rendered and "$defs" not in rendered
    # Inlined, not merely stripped: the allowed values must survive.
    assert sent["schema"]["properties"]["disposition"]["enum"] == [
        "in_service",
        "separable",
        "risky",
    ]


def test_the_hashed_request_carries_the_inlined_schema(store):
    """The schema that changes the answer must be the one inside the hash, or a
    change to how schemas are rendered would silently replay stale judgments."""
    client = ModelClient(model="anthropic/claude-sonnet-5", store=store)

    request = client.build_request(MESSAGES, Disposition)

    assert "$ref" not in json.dumps(request["response_schema"]["schema"])


def test_inlining_preserves_nested_and_listed_refs():
    """A `$ref` can appear nested in a list item or a property of a property."""

    class Inner(BaseModel):
        kind: UnrequestedDisposition

    class Outer(BaseModel):
        items: list[Inner]

    inlined = inline_schema_refs(Outer.model_json_schema())

    assert "$ref" not in json.dumps(inlined) and "$defs" not in inlined
    assert inlined["properties"]["items"]["items"]["properties"]["kind"]["enum"] == [
        "in_service",
        "separable",
        "risky",
    ]


def test_the_live_call_lets_litellm_discard_controls_a_provider_rejects():
    """Anthropic refuses `seed` and accepts only `temperature=1`. Without
    `drop_params` the call raises and the tool is OpenAI-only in practice."""
    litellm = pytest.importorskip("litellm")
    sent = {}
    original = litellm.completion
    litellm.completion = lambda **kwargs: sent.update(kwargs) or _fake_response("{}")
    try:
        from acceptance.llm import _default_completion_fn

        _default_completion_fn(model="anthropic/claude-sonnet-5", messages=MESSAGES)
    finally:
        litellm.completion = original

    assert sent["drop_params"] is True


def test_controls_a_provider_discards_are_recorded_as_absent_not_as_requested():
    """`drop_params` discards silently, so a transcript could otherwise claim a
    seed the provider never received. A dropped control must read as `None` —
    the run was not pinned, and the record has to say so rather than overclaim."""
    pytest.importorskip("litellm")
    from acceptance.llm import _litellm_effective_controls

    openai = _litellm_effective_controls("openai/gpt-5.4-mini", temperature=0.0, seed=0)
    anthropic = _litellm_effective_controls("anthropic/claude-sonnet-5", temperature=0.0, seed=0)

    assert openai == {"temperature": 0.0, "seed": 0}
    # Not merely absent from the dict — explicitly reported as not in force.
    assert anthropic == {"temperature": None, "seed": None}


def test_a_transcript_records_which_determinism_controls_actually_applied(store):
    """The recorded corpus is the evidence base for prompt quality, so it has to
    carry the conditions it was produced under, not the ones we asked for."""
    client = ModelClient(
        model="openai/gpt-5.4-mini",
        mode=Mode.RECORD,
        store=store,
        temperature=0.0,
        seed=0,
        completion_fn=_recorder('{"supported": true, "rationale": "ok"}'),
    )

    client.complete(MESSAGES, Verdict)

    key = request_key(client.build_request(MESSAGES, Verdict))
    record = json.loads(store.path_for(key).read_text())
    assert record["controls_applied"] == {"temperature": 0.0, "seed": 0}


def _dropping_completion_fn(content: str):
    """A completion_fn standing in for a provider that discards our controls.

    Anthropic is the real case: it rejects `seed` outright and `claude-sonnet-5`
    accepts only `temperature=1`, so LiteLLM's `drop_params` sends neither.
    """
    fn = _recorder(content)
    fn.effective_controls = lambda model, **requested: {name: None for name in requested}
    return fn


def test_a_client_reports_the_controls_the_provider_honoured(store):
    """Provenance is only worth reading if it describes the run that happened.
    A client asked for a seed the provider throws away must report the run as
    unseeded rather than echoing the request back (#160)."""
    client = ModelClient(
        model="anthropic/claude-sonnet-5",
        mode=Mode.RECORD,
        store=store,
        temperature=0.0,
        seed=0,
        completion_fn=_dropping_completion_fn('{"supported": true, "rationale": "ok"}'),
    )

    client.complete(MESSAGES, Verdict)

    assert client.controls_in_force == {"temperature": None, "seed": None}


def test_a_client_that_made_no_call_reports_nothing_in_force(store):
    """Indeterminate, not "the configured controls held". A review can make no
    model call at all, and such a run has no evidence either way (§9.3)."""
    client = ModelClient(
        model="openai/gpt-5.4-mini", mode=Mode.RECORD, store=store, temperature=0.0, seed=0
    )

    assert client.controls_in_force is None


def test_a_replayed_run_reports_the_controls_its_transcript_recorded(store):
    """A replay is exactly as reproducible as the recording it replays. Replaying
    a transcript recorded against a provider that discarded a control must not
    report that control as in force."""
    recorder = ModelClient(
        model="anthropic/claude-sonnet-5",
        mode=Mode.RECORD,
        store=store,
        temperature=0.0,
        seed=0,
        completion_fn=_dropping_completion_fn('{"supported": true, "rationale": "ok"}'),
    )
    recorder.complete(MESSAGES, Verdict)

    replayer = ModelClient(
        model="anthropic/claude-sonnet-5",
        mode=Mode.REPLAY,
        store=store,
        temperature=0.0,
        seed=0,
        completion_fn=_exploding_completion_fn,
    )
    replayer.complete(MESSAGES, Verdict)

    assert replayer.controls_in_force == {"temperature": None, "seed": None}


def test_a_run_is_only_as_pinned_as_its_least_pinned_call(store):
    """A review makes many calls. If one ran unpinned the run is unpinned, so
    disagreement collapses to "not in force" — overstating in the negative
    direction never claims reproducibility the run lacks (§3.7)."""
    completion_fn = _recorder('{"supported": true, "rationale": "ok"}')
    # Honoured on the first call, dropped on the second.
    honoured = [True, False]
    completion_fn.effective_controls = lambda model, **requested: (
        dict(requested) if honoured.pop(0) else {name: None for name in requested}
    )
    client = ModelClient(
        model="openai/gpt-5.4-mini",
        mode=Mode.RECORD,
        store=store,
        temperature=0.0,
        seed=0,
        completion_fn=completion_fn,
    )

    client.complete(MESSAGES, Verdict)
    assert client.controls_in_force == {"temperature": 0.0, "seed": 0}

    client.complete([{"role": "user", "content": "another question"}], Verdict)

    assert client.controls_in_force == {"temperature": None, "seed": None}


def test_a_response_that_fails_validation_is_not_left_in_the_store(store):
    """Structured output is best-effort on some providers — Anthropic omitted a
    required field in 2 of 4 probes of a real schema. Persisting before
    validating let such a reply into the corpus, where replay would serve it
    forever. A response the harness rejects is not evidence (#160)."""
    client = ModelClient(
        model="anthropic/claude-sonnet-5",
        mode=Mode.RECORD,
        store=store,
        # `rationale` is required and missing — exactly the observed failure.
        completion_fn=_recorder('{"supported": true}'),
    )

    with pytest.raises(SchemaValidationError):
        client.complete(MESSAGES, Verdict)

    key = request_key(client.build_request(MESSAGES, Verdict))
    assert not store.path_for(key).exists()
    # And it contributes no observation: a call that failed is not a data point.
    assert client.controls_in_force is None
