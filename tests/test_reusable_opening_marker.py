"""Who marks the end of a request's reusable opening, and when (#265).

`request_blocks` decides where the opening *ends* — that is a fact about the
request. This is about how that boundary is expressed, which is a fact about the
provider: Anthropic-family models reuse an opening only where a `cache_control`
breakpoint says one ends, and OpenAI-family models do it automatically and offer
no parameter at all.

Two constraints of the mandate live here. The client marks it and no
request-building code does; and the client does not mark an opening shorter than
the shortest one the model in use can reuse. Below that minimum Anthropic
ignores the breakpoint, with no error, so a marker there is a wasted hint. The
minimum is per model and is not monotonic across generations, which is why it
is a table (#414).

A third property is load-bearing and easy to lose: the marker must not reach the
hashed request. It is provider-specific, so hashing it would make the same review
irreproducible across providers and would orphan every transcript the first time
the minimum changed.
"""

from __future__ import annotations

import pytest

from acceptance.llm import _minimum_reusable_opening, mark_reusable_opening
from acceptance.request_blocks import Block, BlockKind, assemble

_LONG = "sentence about the diff. " * 800  # comfortably over any provider minimum
_SHORT = "tiny."


def _request(opening_text: str) -> list[dict]:
    return assemble(
        [
            Block(BlockKind.DIFF, opening_text),
            Block(BlockKind.INSTRUCTIONS, "judge it"),
            Block(BlockKind.SUBJECT, "this batch"),
        ]
    )


def _markers(messages: list[dict]) -> list[dict]:
    found = []
    for message in messages:
        content = message.get("content")
        if isinstance(content, list):
            found.extend(part for part in content if "cache_control" in part)
    return found


def test_a_provider_needing_a_breakpoint_gets_one_at_the_end_of_the_opening():
    marked = mark_reusable_opening(_request(_LONG), "anthropic/claude-sonnet-5")

    assert len(_markers(marked)) == 1, "exactly one breakpoint, at one boundary"
    # On the opening's last message, so everything the provider may reuse is
    # before it and the subject is after it.
    assert isinstance(marked[1]["content"], list)
    assert isinstance(marked[2]["content"], str), "the subject is not part of the opening"


def test_a_provider_that_needs_no_breakpoint_is_sent_the_request_untouched():
    """OpenAI reuses a repeated opening on prefix stability alone. There is no
    parameter, so the honest behaviour is to change nothing — not to invent a
    marker the provider will read as prompt text."""
    messages = _request(_LONG)

    assert mark_reusable_opening(messages, "openai/gpt-5.4-mini") == messages


def test_an_opening_below_the_models_minimum_is_left_unmarked():
    """The mandate's `constraint-06`. Anthropic ignores a breakpoint under the
    model's minimum, so a marker there buys nothing."""
    marked = mark_reusable_opening(_request(_SHORT), "anthropic/claude-sonnet-5-5")

    assert _markers(marked) == []


@pytest.mark.parametrize(
    "model",
    ["anthropic/claude-sonnet-5-5", "anthropic/claude-opus-5-5", "anthropic/claude-haiku-5-5"],
)
def test_the_current_models_mark_an_opening_over_512_tokens(model):
    """Anthropic's documented minimum for Claude Sonnet 5.5, Opus 5.5 and Haiku
    5.5 is 512 tokens (#414). Under the old flat 1,024, every opening between
    the two went unmarked and never cached."""
    between = "word " * 700  # about 700 tokens: over 512, under 1,024

    assert _markers(mark_reusable_opening(_request(between), model))


@pytest.mark.parametrize(
    ("model", "minimum"),
    [
        ("anthropic/claude-sonnet-5-5", 512),
        ("anthropic/claude-opus-5-5", 512),
        ("anthropic/claude-haiku-5-5", 512),
        ("anthropic/claude-sonnet-5", 1024),
        ("anthropic/claude-opus-4-8", 1024),
        ("anthropic/claude-opus-4-7", 2048),
        ("anthropic/claude-haiku-4-5", 4096),
        ("anthropic/claude-haiku-4-5-20251001", 4096),
    ],
)
def test_each_model_gets_its_own_minimum(model, minimum):
    """The longest matching name wins, so `sonnet-5-5` is not read as `sonnet-5`
    and a dated snapshot gets its family's minimum. The minimum does not fall
    monotonically: Haiku 4.5's is eight times Haiku 5.5's."""
    assert _minimum_reusable_opening(model) == minimum


def test_an_opening_between_two_models_minimums_is_marked_on_one_only():
    """Not a detail: an opening between two minimums is markable on one model
    and not on the other, and the table is what keeps that straight."""
    between = "word " * 700  # over 512 tokens, under 1,024

    assert _markers(mark_reusable_opening(_request(between), "anthropic/claude-sonnet-5-5"))
    assert not _markers(mark_reusable_opening(_request(between), "anthropic/claude-sonnet-5"))


def test_marking_does_not_mutate_the_messages_it_was_given():
    """The request the client hashed and recorded must not acquire a provider
    detail after the fact."""
    messages = _request(_LONG)
    before = [dict(m) for m in messages]

    mark_reusable_opening(messages, "anthropic/claude-sonnet-5")

    assert messages == before


def test_the_marker_is_absent_from_the_hashed_request():
    """The property that keeps a review reproducible across providers.

    `build_request` is what gets hashed and stored; the marker is applied on the
    way out to the provider, after that. So two clients differing only in model
    family still describe the same question.
    """
    from acceptance.llm import ModelClient, StrictResponseModel

    class _Answer(StrictResponseModel):
        verdict: str

    request = ModelClient(model="anthropic/claude-sonnet-5", store=None).build_request(  # type: ignore[arg-type]
        _request(_LONG), _Answer
    )

    assert "cache_control" not in str(request["messages"])
