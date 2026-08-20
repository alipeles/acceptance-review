"""Per-stage token, cost and cache accounting (#264).

The claim under test is narrow and easy to get wrong: a replayed call cost this
run nothing, and the transcript it replays holds what it cost when it was
*recorded*. Reporting either as the other is a confidently false number, which
is the failure this project exists to prevent — so most of what is asserted here
is that the two stay apart.
"""

from __future__ import annotations

import json
import tempfile
from types import SimpleNamespace

from acceptance.config import DEFAULT_MODEL
from acceptance.llm import (
    SERVED_FROM_PROVIDER,
    SERVED_FROM_RECORDING,
    Mode,
    ModelClient,
    StrictResponseModel,
    TranscriptStore,
    _extract_usage,
)
from acceptance.usage import render, summarize


def _call(stage, served_from, **usage):
    return {"stage": stage, "key": "k", "served_from": served_from, "usage": usage}


# --- what the provider reported ------------------------------------------------


def _response(usage):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))],
        usage=usage,
    )


def test_cache_counts_are_recorded_when_the_provider_reports_them():
    usage = _extract_usage(
        _response(
            SimpleNamespace(
                prompt_tokens=100,
                completion_tokens=10,
                total_tokens=110,
                prompt_tokens_details=SimpleNamespace(
                    cached_tokens=80, cache_creation_tokens=5, cache_write_tokens=3
                ),
            )
        )
    )

    assert usage["cached_tokens"] == 80
    assert usage["cache_creation_tokens"] == 5
    assert usage["cache_write_tokens"] == 3


def test_a_cache_count_the_provider_omits_is_absent_rather_than_zero():
    """Acceptance: absence and zero are different claims.

    Recording 0 for a provider that says nothing about caching would report a
    measured 0% hit rate — a number nobody measured.
    """
    usage = _extract_usage(
        _response(SimpleNamespace(prompt_tokens=100, completion_tokens=10, total_tokens=110))
    )

    assert "cached_tokens" not in usage
    assert "cache_creation_tokens" not in usage
    assert "cache_write_tokens" not in usage


def test_a_provider_reporting_zero_cached_tokens_records_the_zero():
    """The other half of the same distinction: a measured zero is kept."""
    usage = _extract_usage(
        _response(
            SimpleNamespace(
                prompt_tokens=100,
                completion_tokens=10,
                total_tokens=110,
                prompt_tokens_details=SimpleNamespace(cached_tokens=0),
            )
        )
    )

    assert usage["cached_tokens"] == 0


def test_usage_details_are_read_from_a_mapping_too():
    """An injected completion_fn may hand back plain dicts; both shapes reach here."""
    usage = _extract_usage(
        _response({"prompt_tokens": 20, "prompt_tokens_details": {"cached_tokens": 7}})
    )

    assert usage["prompt_tokens"] == 20
    assert usage["cached_tokens"] == 7


# --- the aggregate -------------------------------------------------------------


def test_a_replayed_call_costs_this_run_nothing_but_still_cost_something_to_record():
    """Acceptance: the two money figures are not the same number."""
    usage = summarize(
        [
            _call("decompose", SERVED_FROM_RECORDING, cost_usd=0.20, prompt_tokens=100),
            _call("decompose", SERVED_FROM_PROVIDER, cost_usd=0.05, prompt_tokens=50),
        ]
    )

    assert usage.run_spend_usd == 0.05
    assert usage.evidence_cost_usd == 0.25
    assert usage.provider_calls == 1
    assert usage.replayed_calls == 1


def test_a_fully_replayed_run_spends_nothing_and_says_so():
    usage = summarize([_call("mapping", SERVED_FROM_RECORDING, cost_usd=0.75)])

    assert usage.run_spend_usd == 0.0
    assert usage.evidence_cost_usd == 0.75
    assert "this run spent $0.0000" in render(usage)


def test_each_stage_is_accounted_for_separately_and_in_a_stable_order():
    usage = summarize(
        [
            _call("mapping", SERVED_FROM_PROVIDER, cost_usd=0.02, prompt_tokens=10),
            _call("decompose", SERVED_FROM_PROVIDER, cost_usd=0.03, prompt_tokens=20),
            _call("mapping", SERVED_FROM_PROVIDER, cost_usd=0.04, prompt_tokens=30),
        ]
    )

    assert [stage.stage for stage in usage.stages] == ["decompose", "mapping"]
    mapping = usage.stages[1]
    assert mapping.calls == 2
    assert mapping.prompt_tokens == 40
    assert round(mapping.run_spend_usd, 4) == 0.06


def test_the_cached_share_is_measured_only_over_calls_that_reported_one():
    """A call that said nothing about caching must not dilute the share.

    Counting its prompt tokens in the denominator would report a cache hit rate
    lower than anything observed — an unmeasured call scored as a miss.
    """
    usage = summarize(
        [
            _call("decompose", SERVED_FROM_PROVIDER, prompt_tokens=100, cached_tokens=90),
            _call("decompose", SERVED_FROM_PROVIDER, prompt_tokens=900),
        ]
    )

    assert usage.stages[0].cached_prompt_share == 0.9


def test_a_stage_no_call_reported_caching_for_has_an_unmeasured_share():
    usage = summarize([_call("decompose", SERVED_FROM_PROVIDER, prompt_tokens=100)])

    assert usage.stages[0].cached_prompt_share is None
    # And the footer says so with a dash rather than 0.0%.
    assert "—" in render(usage)


def test_a_run_that_made_no_call_says_that_rather_than_printing_an_empty_table():
    assert render(summarize([])) == "Model usage: no model call was made."


def test_a_transcript_missing_its_usage_fields_is_counted_but_not_priced():
    """Transcripts outlive the fields they carry.

    One recorded before cost was tracked simply lacks it. That must cost the run
    a figure, never a review.
    """
    usage = summarize([_call("decompose", SERVED_FROM_RECORDING)])

    assert usage.stages[0].calls == 1
    assert usage.evidence_cost_usd == 0.0


# --- the determinism controls this must not touch ------------------------------


class _Answer(StrictResponseModel):
    value: str


def _client(usage, store):
    def completion_fn(**kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({"value": "x"})))],
            usage=usage,
        )

    return ModelClient(
        model=DEFAULT_MODEL,
        mode=Mode.RECORD,
        store=store,
        completion_fn=completion_fn,
    )


_MESSAGES = [{"role": "user", "content": "hello"}]


def test_naming_the_stage_does_not_change_the_request_key():
    """Acceptance: `stage` is provenance, not a determinism control.

    If it entered the hash, every existing transcript would orphan the moment a
    call site was labelled — and this change labels seven of them.
    """
    store = TranscriptStore(tempfile.mkdtemp())
    client = _client(SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2), store)

    client.complete(_MESSAGES, _Answer, stage="decompose")
    client.complete(_MESSAGES, _Answer, stage="a completely different stage")
    client.complete(_MESSAGES, _Answer)

    keys = {call["key"] for call in client.observed_calls}
    assert len(keys) == 1, f"stage changed the request key: {keys}"
    # And only the first call reached the provider; the rest replayed.
    assert [call["served_from"] for call in client.observed_calls] == [
        SERVED_FROM_PROVIDER,
        SERVED_FROM_RECORDING,
        SERVED_FROM_RECORDING,
    ]


def test_recording_usage_fields_does_not_change_the_request_key():
    """Acceptance: `usage` is a sibling of `request` in the record, not an input.

    Two clients issuing the same request, whose providers report different usage
    — one with cache detail, one without — must land on the same key.
    """
    plain = _client(
        SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        TranscriptStore(tempfile.mkdtemp()),
    )
    detailed = _client(
        SimpleNamespace(
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
            prompt_tokens_details=SimpleNamespace(cached_tokens=1, cache_creation_tokens=4),
        ),
        TranscriptStore(tempfile.mkdtemp()),
    )

    plain.complete(_MESSAGES, _Answer, stage="decompose")
    detailed.complete(_MESSAGES, _Answer, stage="decompose")

    assert plain.observed_calls[0]["key"] == detailed.observed_calls[0]["key"]
    # The usage really did differ — otherwise this asserts nothing.
    assert "cached_tokens" not in plain.observed_calls[0]["usage"]
    assert detailed.observed_calls[0]["usage"]["cached_tokens"] == 1
