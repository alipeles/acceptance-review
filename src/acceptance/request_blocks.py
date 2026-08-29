"""Assemble a stage's request out of ranked content blocks.

Providers that reuse a repeated prompt reuse a **prefix**: they match the request
against what they have already seen, from the first byte, and stop at the first
difference. So what a request opens with decides how much of it can be reused,
and two requests that carry the same material share nothing unless that material
sits at the front of both, written the same way.

Before this module every stage built one hand-ordered string and put its own
instructions in the `system` message. That loses on both counts. The system
message differs per stage, so any two stages diverge at the very first message
and share no prefix at all; and inside the user message the stage-specific part
usually came first, so even sibling calls of one stage diverged early.

The fix is to stop writing the order by hand. A stage declares *what* it is
carrying — `Block(BlockKind.DIFF, ...)`, `Block(BlockKind.SUBJECT, ...)` — and
`assemble` puts the blocks in `BlockKind`'s declared order, which runs from the
material the most requests of a run carry down to the material only this request
carries. Two requests then agree for as long as their content agrees, by
construction rather than by each author remembering.

**The order is a claim about the run, and it is checked rather than trusted.**
`BlockKind`'s order says `DIFF` is carried by more of a run's requests than
`OBLIGATIONS`, and `OBLIGATIONS` by more than `INSTRUCTIONS`. That is true of the
pipeline today — five stages carry the diff, two carry the obligation list, and a
stage's instructions are carried only by that stage's own calls — but it is a
property of the pipeline, not of this module, so it can drift. The test that
counts the blocks of a real run and compares the counts against this order is
what keeps the claim honest.

## Two things this module deliberately does not do

**It does not decide what a stage carries.** Blocks are handed in; nothing here
adds material to a request or takes any away. A stage that shows the model a
filtered view of the diff keeps its filtered view — `evidence/discrimination.py`
does exactly that, and its `## Changed production code` is different *content*
from the shared `## Diff` rather than a different rendering of it. Making the two
match would mean feeding one stage something it does not receive today.

**It does not mark where the reusable opening ends.** Anthropic-family models
need an explicit `cache_control` breakpoint and OpenAI-family models need none,
so the marker is provider-specific and belongs with the client that knows which
provider it is talking to. `llm.py` places it. A stage cannot place one, because
a block carries a plain string and a breakpoint is a structured content part —
see `assemble` for why that is the guarantee rather than a text scan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# The one system message every request of a run carries, byte for byte.
#
# It is deliberately thin. Everything specific to a judgement — what to look for,
# what the fields mean, what to do when unsure — moved into a `BlockKind.
# INSTRUCTIONS` block inside the user message, because a system message that
# differed per stage put a difference in the first message of every request and
# so made a shared prefix impossible. What is left here is only what is true of
# every call the pipeline makes.
#
# **It says nothing about the order of the request's parts, deliberately.** It
# used to open "You are given material to judge and, after it, the instructions
# for one specific judgement", and that was false: `assemble` puts INSTRUCTIONS
# before SUBJECT, so for a stage carrying neither a diff nor an obligation list
# the instructions come first. It is not repairable by restating the order
# either, because the order is not the same for every stage — a stage carrying a
# DIFF block genuinely does get material first. A sentence that is true of some
# requests and false of others is worse than no sentence, since the model reads
# it on every one of them.
SHARED_PREAMBLE = (
    "You are an acceptance reviewer. Answer only in the requested schema, and "
    "answer only the question the instructions ask."
)

# Names a provider gives to a reusable-opening breakpoint. Used by
# `tests/test_request_blocks.py` to check the text stages AUTHOR — their
# instructions — and deliberately not used to scan a request at runtime. See
# `assemble` for why that distinction is load-bearing.
PROVIDER_CACHE_MARKERS = ("cache_control", "<<<cache-breakpoint>>>")


class BlockKind(Enum):
    """The kinds of content a request carries, **most widely shared first**.

    Declaration order is the assembly order, so adding a member in the wrong
    place changes every request. Place a new kind by asking how many of a single
    run's requests carry that content: more than the kind above it, or fewer?

    `auto()` is not used, and the values are spaced, so that a kind can be
    inserted between two others without renumbering the rest.
    """

    #: The labelled `## Diff` block from `coverage/prompt.py::render_diff_section`.
    #: Five stages carry it — coverage classification, unrequested-change
    #: detection, test recommendation, open-question resolution and declaration
    #: comparison — and it is by far the largest thing any of them carries.
    DIFF = 10

    #: The changed *production* code, source files only and without hunk labels
    #: — `evidence/discrimination.py`'s narrower view of the change. It is a
    #: kind of its own rather than a `DIFF` because it is different content, not
    #: a different rendering: unifying the two would change what that stage is
    #: shown. Ranked here because it is invariant across that stage's calls and
    #: is the largest thing they carry.
    CHANGED_CODE = 15

    #: The obligation list. Carried by fewer requests than the diff, and by no
    #: request that does not also carry something above it.
    OBLIGATIONS = 20

    #: The stage's own instructions — what used to be its `system` message.
    #: Shared by every call *that stage* makes and by no other stage's.
    INSTRUCTIONS = 30

    #: What this one call is about: its batch, its criteria, the single change
    #: being judged. Shared with nothing, so it goes last.
    SUBJECT = 40


@dataclass(frozen=True)
class Block:
    """One labelled piece of a request.

    `text` is used verbatim. Two blocks count as the same content when their
    text is equal, so a renderer shared between stages is what makes the content
    shared — naming two different strings `DIFF` does not make them one block.
    """

    kind: BlockKind
    text: str


class BlockError(ValueError):
    """A request was described in a way `assemble` refuses to build."""


def assemble(blocks: list[Block]) -> list[dict]:
    """Order `blocks` and return the messages for `ModelClient.complete`.

    Blocks are sorted by `BlockKind`'s declared order. Sorting is **stable**, so
    two blocks of the same kind stay in the order the caller gave them — a stage
    that splits its subject across several blocks keeps control of their
    sequence.

    Empty blocks are dropped rather than joined, so an absent optional section
    cannot leave a blank run in the middle of a request and split an otherwise
    shared prefix.

    ## Why the result is three messages and not two

    Everything above `SUBJECT` is content some other request of the run also
    carries; `SUBJECT` is what only this call carries. Emitting that split as a
    message boundary rather than joining it into one string is what lets the
    client mark where the reusable opening ends without re-deriving the
    boundary from the text — which it could not do, because by then the blocks
    are a single string with nothing to distinguish them.

    So the messages are `[preamble, reusable opening, subject]`, and either of
    the last two is omitted when it would be empty. Nothing about the *content*
    changes: a provider sees the same bytes in the same order it would have seen
    from one joined message.

    ## Why there is no runtime scan for provider markers

    An earlier version of this function rejected any block whose text contained
    `cache_control`, on the reasoning that a stage writing one would be doing the
    client's job. It was wrong, and a dogfood run of this very change is what
    showed it: **a block's text is mostly not the stage's own words.** The
    subject of a mapping request is the source of the tests under review, and the
    diff block is the diff under review. Reviewing any repository that mentions
    prompt caching — this one, now — made the tool abort at the mapping stage
    with a `BlockError` about a string it had merely been shown.

    The scan was also unnecessary. A block carries a `str`, and a provider
    breakpoint is not a string: `llm.mark_reusable_opening` expresses it by
    replacing a message's content with a list of content parts. A stage
    therefore *cannot* emit one through this function, whatever it writes.
    `tests/test_request_blocks.py` pins both halves — that assembled contents are
    always plain strings, and that no prompt a stage AUTHORS mentions a marker,
    checked against `authored_prompts()` rather than against a live request.
    """
    if not blocks:
        raise BlockError("a request must carry at least one block")

    present = [block for block in blocks if block.text.strip()]
    if not present:
        raise BlockError("every block of this request is empty")

    ordered = sorted(present, key=lambda block: block.kind.value)
    opening = [block for block in ordered if block.kind is not BlockKind.SUBJECT]
    subject = [block for block in ordered if block.kind is BlockKind.SUBJECT]

    if not opening:
        # Required so that `reusable_opening` can find the boundary from the
        # messages alone. Without it, `[preamble, X]` would be ambiguous — X
        # could be an opening with no subject or a subject with no opening — and
        # the client would have to guess which, on every request.
        #
        # No stage is affected: every one of them passes its INSTRUCTIONS, which
        # is an opening block. A request that really is nothing but its subject
        # has no instructions either, and is a mistake worth failing on.
        raise BlockError(
            "a request must carry at least one block above SUBJECT — normally "
            "its INSTRUCTIONS. Without one there is no reusable opening for the "
            "client to mark."
        )

    messages = [
        {"role": "system", "content": SHARED_PREAMBLE},
        {"role": "user", "content": "\n\n".join(block.text for block in opening)},
    ]
    if subject:
        messages.append({"role": "user", "content": "\n\n".join(b.text for b in subject)})
    return messages


#: How many leading messages of an assembled request are its reusable opening.
#: Fixed rather than searched for: `assemble` always emits the preamble and then
#: exactly one message holding every block above `SUBJECT`, so the boundary is a
#: property of the shape and the client never has to infer it from the text.
REUSABLE_OPENING_MESSAGES = 2


def reusable_opening(messages: list[dict]) -> list[dict]:
    """The leading messages a provider may be able to reuse across requests.

    Everything `assemble` puts before the subject: the shared preamble, and the
    blocks other requests of the run also carry.

    Defined here, beside the code that creates the split, so the client does not
    carry a second idea of where the opening ends. A message list this module did
    not build — a hand-rolled one from a test — is returned whole, since the
    convention it relies on does not hold and marking less would be a guess.
    """
    if len(messages) <= REUSABLE_OPENING_MESSAGES:
        return list(messages)
    return messages[:REUSABLE_OPENING_MESSAGES]


def authored_prompts() -> dict[str, str]:
    """Every system prompt a review-pipeline stage authors, by stage name.

    Exists so a test can check the text stages WRITE for provider markers,
    without scanning the text they QUOTE. See `assemble`'s note on why that
    distinction had to be drawn.
    """
    import importlib

    modules = [
        "acceptance.requirement.obligations",
        "acceptance.requirement.linking",
        "acceptance.evidence.mapping",
        "acceptance.evidence.discrimination",
        "acceptance.coverage.classify",
        "acceptance.coverage.open_questions",
        "acceptance.coverage.unrequested",
        "acceptance.coverage.disposition",
        "acceptance.coverage.recommendations",
        "acceptance.coverage.declaration_comparison",
    ]
    prompts: dict[str, str] = {}
    for name in modules:
        module = importlib.import_module(name)
        stage = getattr(module, "_STAGE", name)
        for attr in dir(module):
            if "SYSTEM_PROMPT" in attr:
                value = getattr(module, attr)
                if isinstance(value, str) and value.strip():
                    prompts[f"{stage}:{attr}"] = value
    return prompts
