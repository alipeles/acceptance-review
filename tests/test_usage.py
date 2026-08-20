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
from acceptance.usage import _PIPELINE_ORDER, render, summarize


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
            _call("test-to-obligation mapping", SERVED_FROM_PROVIDER, prompt_tokens=10),
            _call("decompose", SERVED_FROM_PROVIDER, prompt_tokens=20),
            _call("test-to-obligation mapping", SERVED_FROM_PROVIDER, prompt_tokens=30),
        ]
    )

    assert [stage.stage for stage in usage.stages] == [
        "decompose",
        "test-to-obligation mapping",
    ]
    mapping = usage.stages[1]
    assert mapping.calls == 2
    assert mapping.prompt_tokens == 40


def test_stages_are_reported_in_the_order_the_pipeline_runs_them():
    """Not alphabetically: the table is read as the review proceeds.

    Alphabetical put `coverage classification` above `decompose` and split the
    three `evidence/` stages apart, so a reader had to reassemble the sequence
    themselves. The calls are fed in deliberately jumbled order here, because an
    incremental re-run issues its live calls in a different sequence from the run
    that recorded them and the table must not depend on that.
    """
    usage = summarize(
        [
            _call("declaration comparison", SERVED_FROM_PROVIDER),
            _call("coverage classification", SERVED_FROM_PROVIDER),
            _call("decompose", SERVED_FROM_PROVIDER),
            _call("test recommendation", SERVED_FROM_PROVIDER),
            _call("test-to-obligation mapping", SERVED_FROM_PROVIDER),
            _call("obligation linking", SERVED_FROM_PROVIDER),
            _call("discrimination judgment", SERVED_FROM_PROVIDER),
        ]
    )

    assert [stage.stage for stage in usage.stages] == [
        "decompose",
        "obligation linking",
        "test-to-obligation mapping",
        "discrimination judgment",
        "coverage classification",
        "test recommendation",
        "declaration comparison",
    ]


def test_a_stage_the_order_does_not_name_is_reported_last_rather_than_dropped():
    """The order is presentation, not a whitelist.

    A stage added without touching `_PIPELINE_ORDER` must still show its spend —
    losing a row would understate the run's cost, which is worse than showing it
    in the wrong place. `test_every_pipeline_stage_appears_in_the_reported_order`
    is what makes that a temporary state rather than a silent one.
    """
    usage = summarize(
        [
            _call("a brand new stage", SERVED_FROM_PROVIDER, prompt_tokens=5),
            _call("decompose", SERVED_FROM_PROVIDER, prompt_tokens=7),
        ]
    )

    assert [stage.stage for stage in usage.stages] == ["decompose", "a brand new stage"]
    assert usage.stages[1].prompt_tokens == 5


def test_every_pipeline_stage_appears_in_the_reported_order():
    """Guards the order against drift as stages are added or renamed.

    Read off the modules' own `_STAGE` constants rather than restated, so a
    rename that leaves the footer ordering behind fails here instead of quietly
    dropping that stage to the bottom of the table.
    """
    from acceptance.coverage.classify import _STAGE as CLASSIFY
    from acceptance.coverage.declaration_comparison import _STAGE as DECLARATION
    from acceptance.coverage.disposition import _STAGE as DISPOSITION
    from acceptance.coverage.open_questions import _STAGE as OPEN_QUESTIONS
    from acceptance.coverage.recommendations import _STAGE as RECOMMENDATIONS
    from acceptance.coverage.unrequested import _STAGE as UNREQUESTED
    from acceptance.evidence.discrimination import _STAGE as DISCRIMINATION
    from acceptance.evidence.mapping import _STAGE as MAPPING
    from acceptance.requirement.linking import _STAGE as LINKING
    from acceptance.requirement.obligations import _STAGE as DECOMPOSE

    declared = {
        DECOMPOSE,
        LINKING,
        OPEN_QUESTIONS,
        MAPPING,
        DISCRIMINATION,
        CLASSIFY,
        UNREQUESTED,
        DISPOSITION,
        RECOMMENDATIONS,
        DECLARATION,
    }

    missing = declared - set(_PIPELINE_ORDER)
    assert not missing, f"these stages are not in the footer's pipeline order: {sorted(missing)}"
    stale = set(_PIPELINE_ORDER) - declared
    assert not stale, f"the footer's pipeline order names stages nothing issues: {sorted(stale)}"


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
