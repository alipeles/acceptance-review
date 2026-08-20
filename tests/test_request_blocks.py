"""What every request of a run must look like, and who is allowed to say so.

These are the guards for the ordering rules in `request_blocks`. Three of them
correspond one-to-one to a Completion expectation of the mandate: a request must
not put its own content ahead of content it shares, two requests must not write
the same content differently, and a stage must not mark its own reusable
opening.

The unit tests below pin the assembler. `test_pipeline_request_openings.py` pins
the same rules over the requests a **real run** issues, which is the half that
catches a stage quietly bypassing the assembler.
"""

from __future__ import annotations

import pytest

from acceptance.request_blocks import (
    PROVIDER_CACHE_MARKERS,
    REUSABLE_OPENING_MESSAGES,
    SHARED_PREAMBLE,
    Block,
    BlockError,
    BlockKind,
    assemble,
    authored_prompts,
    reusable_opening,
)


def _user_text(messages: list[dict]) -> str:
    return "\n\n".join(m["content"] for m in messages if m["role"] == "user")


def test_shared_content_precedes_content_unique_to_the_request():
    """The mandate's first Completion expectation.

    Declared in the wrong order on purpose: the caller does not control the
    sequence, `BlockKind` does.
    """
    messages = assemble(
        [
            Block(BlockKind.SUBJECT, "only this call"),
            Block(BlockKind.INSTRUCTIONS, "how to judge"),
            Block(BlockKind.DIFF, "the diff"),
        ]
    )

    text = _user_text(messages)
    assert text.index("the diff") < text.index("how to judge") < text.index("only this call")


def test_a_block_kind_carried_by_more_requests_sorts_before_one_carried_by_fewer():
    """The rule the previous test demonstrates, stated over the whole enum.

    Fails if a kind is ever inserted in the wrong place — which is the only way
    the ordering can silently regress, since nothing else decides it.
    """
    values = [kind.value for kind in BlockKind]
    assert values == sorted(values), "BlockKind members must be declared most-shared first"
    assert list(BlockKind)[-1] is BlockKind.SUBJECT, "SUBJECT is carried by one request, so it ends"


def test_the_same_content_is_written_the_same_way_in_two_requests():
    """The mandate's second Completion expectation, at the assembler.

    Two requests carrying an equal block must open with equal bytes, whatever
    else differs after it.
    """
    diff = Block(BlockKind.DIFF, "## Diff\nthe same hunks")

    first = assemble([diff, Block(BlockKind.INSTRUCTIONS, "A"), Block(BlockKind.SUBJECT, "x")])
    second = assemble([diff, Block(BlockKind.INSTRUCTIONS, "B"), Block(BlockKind.SUBJECT, "y")])

    assert first[0] == second[0], "the preamble is shared by every request"
    assert first[1]["content"].startswith("## Diff\nthe same hunks")
    assert second[1]["content"].startswith("## Diff\nthe same hunks")


def test_every_request_opens_with_the_same_preamble():
    """What makes a cross-stage opening possible at all.

    A system message that differed per stage would put a difference in the first
    message of every request, and no two stages could share anything.
    """
    one = assemble([Block(BlockKind.INSTRUCTIONS, "map tests")])
    two = assemble([Block(BlockKind.INSTRUCTIONS, "classify coverage")])

    assert one[0] == two[0] == {"role": "system", "content": SHARED_PREAMBLE}


def test_a_stage_cannot_mark_the_end_of_its_own_reusable_opening():
    """The mandate's third Completion expectation, as a structural guarantee.

    A provider breakpoint is not a string — `llm.mark_reusable_opening` expresses
    it by replacing a message's content with a list of content parts. `assemble`
    only ever emits `str` contents, so no text a stage writes can become one.
    That is why this is checked as a type rather than as a search for a word.
    """
    messages = assemble(
        [
            Block(BlockKind.INSTRUCTIONS, "judge this. cache_control: here"),
            Block(BlockKind.SUBJECT, "the batch"),
        ]
    )

    assert all(isinstance(m["content"], str) for m in messages), (
        "a stage produced a structured content part, which is how — and only how "
        "— a reusable-opening breakpoint is expressed"
    )


def test_no_prompt_a_stage_authors_mentions_a_provider_breakpoint():
    """The other half: stages should not be writing marker text either.

    Checked against the prompts stages AUTHOR, never against a live request.
    Scanning a request would scan the diff and the test sources it was handed —
    content quoted from the repository under review, not the stage's own words —
    and this repository now mentions `cache_control` in `llm.py`.
    """
    offenders = {
        name: marker
        for name, prompt in authored_prompts().items()
        for marker in PROVIDER_CACHE_MARKERS
        if marker in prompt
    }

    assert not offenders, (
        f"these stage prompts mention a provider breakpoint: {offenders}. Where a "
        "request's reusable opening ends is the client's to mark — see llm."
        "mark_reusable_opening."
    )


def test_reviewing_a_repository_that_mentions_prompt_caching_still_works():
    """The regression a dogfood run of this change actually found.

    An earlier guard rejected any block containing `cache_control`. The mapping
    stage's subject is the SOURCE of the tests under review, so reviewing this
    repository aborted the whole run at mapping — over a string the tool had
    merely been shown. Content under review is data, never an instruction.
    """
    messages = assemble(
        [
            Block(BlockKind.DIFF, "## Diff\n+    last['cache_control'] = {'type': 'ephemeral'}"),
            Block(BlockKind.INSTRUCTIONS, "classify the diff"),
            Block(BlockKind.SUBJECT, "def test_marker():\n    assert 'cache_control' in sent"),
        ]
    )

    assert "cache_control" in _user_text(messages)


def test_reordering_a_request_leaves_it_carrying_the_same_content():
    """`constraint-04`: only the order moves.

    Compared as a set of block texts, because comparing the joined strings would
    pass trivially — the point is that assembly neither drops nor invents.
    """
    blocks = [
        Block(BlockKind.SUBJECT, "subject text"),
        Block(BlockKind.DIFF, "diff text"),
        Block(BlockKind.OBLIGATIONS, "obligations text"),
        Block(BlockKind.INSTRUCTIONS, "instructions text"),
    ]

    text = _user_text(assemble(blocks))

    for block in blocks:
        assert block.text in text
    assert len(text.split("\n\n")) == len(blocks)


def test_an_empty_block_is_dropped_rather_than_joined():
    """An absent optional section must not leave a blank run mid-request, which
    would be a difference in the middle of an otherwise shared opening."""
    messages = assemble(
        [
            Block(BlockKind.DIFF, "diff text"),
            Block(BlockKind.OBLIGATIONS, "   "),
            Block(BlockKind.INSTRUCTIONS, "instructions text"),
        ]
    )

    assert _user_text(messages) == "diff text\n\ninstructions text"


def test_the_reusable_opening_is_everything_before_the_subject():
    messages = assemble(
        [
            Block(BlockKind.DIFF, "diff text"),
            Block(BlockKind.INSTRUCTIONS, "instructions text"),
            Block(BlockKind.SUBJECT, "subject text"),
        ]
    )

    opening = reusable_opening(messages)

    assert len(opening) == REUSABLE_OPENING_MESSAGES
    assert "subject text" not in "\n".join(m["content"] for m in opening)
    assert "diff text" in opening[1]["content"]


def test_a_request_with_no_subject_is_reusable_all_the_way_to_its_end():
    """Coverage classification and unrequested-change detection are shaped this
    way: one call per run, carrying nothing that is unique to a sibling."""
    messages = assemble(
        [Block(BlockKind.DIFF, "diff text"), Block(BlockKind.INSTRUCTIONS, "instructions text")]
    )

    assert len(messages) == REUSABLE_OPENING_MESSAGES
    assert reusable_opening(messages) == messages


def test_a_request_that_is_only_a_subject_is_refused():
    """Not a style rule. `reusable_opening` finds the boundary by position, so
    `[preamble, X]` must never be ambiguous between an opening and a subject."""
    with pytest.raises(BlockError, match="above SUBJECT"):
        assemble([Block(BlockKind.SUBJECT, "the batch")])


def test_a_request_with_no_blocks_at_all_is_refused():
    with pytest.raises(BlockError):
        assemble([])
