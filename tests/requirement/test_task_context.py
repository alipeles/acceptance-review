"""The optional `## Context` section (#212).

Background that explains a mandate is not part of it. Under `# Task` it was read
as mandate, and a sentence describing today's behaviour became an obligation to
keep it. A Context section is read, shown to the decomposer labelled as
background, and never becomes a requirement.

What is pinned here, against the issue's Acceptance:

- the SECTION decides, not the wording: the same paragraph gets a requirement id
  under `# Task` and none under `## Context`;
- context reaches every decompose call, set apart from the requirement list;
- mandate coverage is identical with and without the section;
- a file with no Context section sends exactly the prompt it sent before. The
  committed recordings replaying is the byte-level proof of that; the tests
  below prove the narrower thing a recording cannot, that adding the section
  changes nothing in the prompt except adding the block.
"""

from __future__ import annotations

import json

from acceptance.requirement.obligations import _context_text, decompose
from acceptance.requirement.registry import build_registry
from acceptance.requirement.task_file import ParsedTaskFile, parse_task_file
from acceptance.supplied_ids import UnusableAnswerLog
from acceptance.verdict import assess_mandate_coverage
from tests.support import (
    _completed,
    _fake_response,
    _schema_name,
    _supplied_enum,
    message_text,
    model_client_with,
    sent_text,
    uncovered_summary,
)

_BACKGROUND = "Today the export writes amounts with as many decimals as the float has."

_MANDATE = """# Task
Export invoices to a CSV file.

## Constraints
- The amount column is written with exactly two decimal places.
- The export writes a header row naming every column.
"""

_WITH_CONTEXT = f"""# Task
Export invoices to a CSV file.

## Context
{_BACKGROUND}

## Constraints
- The amount column is written with exactly two decimal places.
- The export writes a header row naming every column.
"""

# The same paragraph, moved under `# Task`. Nothing about its wording changes.
_AS_TASK = f"""# Task
Export invoices to a CSV file.

{_BACKGROUND}

## Constraints
- The amount column is written with exactly two decimal places.
- The export writes a header row naming every column.
"""

# The same paragraph under a heading the format does not recognise. The
# contrast case for coverage: this is what happened to a Context section before
# #212, and it must still be reported as unread.
_UNRECOGNISED = _WITH_CONTEXT.replace("## Context", "## Background")

_AMOUNT = "The amount column is written with exactly two decimal places."

_RESPONSE = {
    "requirement_dispositions": [],
    "open_questions": [],
    "obligations": [
        {
            "id": "amount-two-decimals",
            "description": "Amounts are written with exactly two decimal places.",
            "type": "functional",
            "importance": "normal",
            "explicit": True,
            "observable_behavior": "...",
            "source_quote": _AMOUNT,
            "required_evidence": "code_and_tests",
            "required_evidence_reason": "",
        }
    ],
}


def _decompose(
    task: str,
    summary: dict | None = None,
    response: dict = _RESPONSE,
    unusable: UnusableAnswerLog | None = None,
):
    """Decompose `task` against `response`, recording what every call sent.

    `client_returning`, plus a record of each call — a fixed response alone
    cannot show what the stage put in front of the model. Each entry holds the
    response schema's name, the whole text sent, each message's text separately
    (the separation the stage promises is a message boundary), and the quotations
    the schema offered.
    """
    sent: list[dict] = []

    def completion_fn(**kwargs):
        sent.append(
            {
                "schema": _schema_name(**kwargs),
                "prompt": sent_text(kwargs["messages"]),
                "messages": [message_text(m) for m in kwargs["messages"]],
                "quotable": _supplied_enum("source_quote", **kwargs),
            }
        )
        chosen = response
        if _schema_name(**kwargs) == "_SummarySpans":
            chosen = summary if summary is not None else {}
        return _fake_response(json.dumps(_completed(chosen, **kwargs)))

    client = model_client_with(completion_fn)
    return decompose(parse_task_file(task), client, unusable), sent


def _decompose_calls(sent: list[dict]) -> list[dict]:
    """The per-requirement decompose calls, in a stable order.

    The calls are issued concurrently, so arrival order is not stable.
    """
    calls = [entry for entry in sent if entry["schema"] != "_SummarySpans"]
    return sorted(calls, key=lambda entry: entry["prompt"])


def _decompose_prompts(sent: list[dict]) -> list[str]:
    return [entry["prompt"] for entry in _decompose_calls(sent)]


# --- the parse --------------------------------------------------------------


def test_a_context_paragraph_is_recorded_as_context_with_an_exact_span():
    parsed = parse_task_file(_WITH_CONTEXT)

    (block,) = parsed.context
    assert block.text == _BACKGROUND
    assert parsed.source[block.start : block.end] == block.text


def test_context_is_neither_mandate_nor_unread():
    parsed = parse_task_file(_WITH_CONTEXT)

    assert [b.text for b in parsed.behavior] == ["Export invoices to a CSV file."]
    assert parsed.unclaimed == []


def test_every_block_kind_under_context_is_context():
    """Background is often a list of measurements or a table, not prose. Each
    block becomes its own span, as under every other section (DR-216)."""
    task = """# Task
Do the thing.

## Context
Measured on the last run:

- 20 of 29 requirements yielded obligations.

| run | lost |
|---|---|
| 4 | 9 |
"""
    parsed = parse_task_file(task)

    assert len(parsed.context) == 3
    assert parsed.context[1].text == "20 of 29 requirements yielded obligations."
    assert "| run | lost |" in parsed.context[2].text
    for span in parsed.context:
        assert parsed.source[span.start : span.end] == span.text
    assert parsed.unclaimed == []


def test_a_sub_heading_inside_context_stays_context():
    """Background organised under its own sub-headings is still background.
    Every heading used to reset the section, so the blocks after `### Measured`
    became unread source."""
    task = """# Task
Do the thing.

## Context
Why it matters.

### Measured
Nine of 29 requirements were lost.

## Constraints
- Keep it fast.
"""
    parsed = parse_task_file(task)

    assert [c.text for c in parsed.context] == [
        "Why it matters.",
        "Nine of 29 requirements were lost.",
    ]
    assert [c.text for c in parsed.constraints] == ["Keep it fast."]
    assert parsed.unclaimed == []


def test_a_sub_heading_naming_a_mandate_section_ends_context():
    """The owner's ruling at #212's Gate 2: a `### Constraints` under Context
    is read as constraints, not swallowed into background. If the author meant
    background, the result is a visible extra requirement; if they meant
    mandate, the other reading would have lost it silently (DR-216 decision 2).
    """
    task = """# Task
Do the thing.

## Context
Why it matters.

### Constraints
- Every call is retried three times.
"""
    parsed = parse_task_file(task)

    assert [c.text for c in parsed.context] == ["Why it matters."]
    assert [c.text for c in parsed.constraints] == ["Every call is retried three times."]
    assert [r.id for r in build_registry(parsed)] == ["task-01", "constraint-01"]
    assert parsed.unclaimed == []


def test_context_survives_persistence():
    parsed = parse_task_file(_WITH_CONTEXT)
    assert ParsedTaskFile.from_dict(parsed.to_dict()) == parsed


def test_a_file_without_context_parses_exactly_as_before():
    parsed = parse_task_file(_MANDATE)

    assert parsed.context == []
    assert "context" not in {k for k, v in parsed.to_dict().items() if v}


# --- the section decides, not the wording -----------------------------------


def test_a_context_paragraph_gets_no_requirement_id():
    with_context = build_registry(parse_task_file(_WITH_CONTEXT))
    without = build_registry(parse_task_file(_MANDATE))

    assert [r.id for r in with_context] == [r.id for r in without]
    assert all(_BACKGROUND not in r.text for r in with_context)


def test_the_same_paragraph_under_task_gets_a_requirement_id():
    """The converse, and the reason the test above means anything: if the
    parser dropped the paragraph for its wording, it would drop it here too."""
    registry = build_registry(parse_task_file(_AS_TASK))

    assert any(r.id == "task-02" and r.text == _BACKGROUND for r in registry)


def test_a_context_paragraph_produces_no_obligation_and_no_disposition():
    decomposition, _ = _decompose(_WITH_CONTEXT)

    disposed = {d.requirement_id for d in decomposition.requirement_map.dispositions}
    assert disposed == {"task-01", "constraint-01", "constraint-02"}
    assert [o.id for o in decomposition.obligations] == ["amount-two-decimals"]


# --- what the model is shown ------------------------------------------------


def test_every_decompose_call_shows_the_context_labelled_as_background():
    _, sent = _decompose(_WITH_CONTEXT)
    calls = _decompose_calls(sent)

    assert len(calls) == 2
    for call in calls:
        assert "TASK CONTEXT" in call["prompt"]
        assert _BACKGROUND in call["prompt"]
        # Never rendered as a requirement line.
        assert f"] {_BACKGROUND}" not in call["prompt"]


def test_the_context_travels_in_a_different_message_from_the_requirement_list():
    """Kept apart by the request's structure, not only by a label: the message
    holding the requirement list does not contain the background, and the
    message holding the background does not contain the list."""
    _, sent = _decompose(_WITH_CONTEXT)

    for call in _decompose_calls(sent):
        holding_background = [m for m in call["messages"] if _BACKGROUND in m]
        holding_requirements = [
            m for m in call["messages"] if "The complete set of requirements" in m
        ]
        assert len(holding_background) == 1
        assert len(holding_requirements) == 1
        assert holding_background[0] is not holding_requirements[0]
        assert "The complete set of requirements" not in holding_background[0]
        assert _BACKGROUND not in holding_requirements[0]
        assert "TASK CONTEXT" in holding_background[0]
        # The background comes first, so the requirements are read in its light.
        messages = call["messages"]
        assert messages.index(holding_background[0]) < messages.index(holding_requirements[0])


# --- context can never be the source of an obligation ------------------------


def test_the_context_is_never_offered_as_a_quotation():
    """The structural barrier. Every obligation names the text it came from,
    and the response schema offers only the answering requirement's own text.
    The background is shown to every call and quotable by none of them."""
    _, sent = _decompose(_WITH_CONTEXT)
    calls = _decompose_calls(sent)

    assert calls
    for call in calls:
        assert call["quotable"], "the call offered no quotation at all"
        assert all(_BACKGROUND not in quote for quote in call["quotable"])
        assert all(quote not in _BACKGROUND for quote in call["quotable"])


def test_an_obligation_quoting_the_context_is_reported_not_attributed_to_it():
    """A provider that ignores the schema and quotes the background anyway.
    The obligation is not dropped — losing an obligation is the worse failure,
    see `_obligations_from` — but it is not given a source span in the Context
    section, and the stage reports the quotation as an unusable answer."""
    keep_floats = {
        **_RESPONSE["obligations"][0],
        "id": "keep-float-decimals",
        "description": "Amounts keep as many decimals as the float has.",
        "source_quote": _BACKGROUND,
    }
    response = {**_RESPONSE, "obligations": [*_RESPONSE["obligations"], keep_floats]}
    unusable = UnusableAnswerLog()
    parsed = parse_task_file(_WITH_CONTEXT)
    (context_span,) = parsed.context

    decomposition, _ = _decompose(_WITH_CONTEXT, response=response, unusable=unusable)

    reported = [a for a in unusable.answers if a.field == "source_quote"]
    assert [a.returned_id for a in reported] == ["keep-float-decimals"]
    for obligation in decomposition.obligations:
        for span in obligation.source_spans:
            assert not (context_span.start <= span.start < context_span.end), (
                f"{obligation.id} cites the Context section"
            )


def test_a_span_call_for_the_opening_summary_shows_the_context_too():
    """The summary's uncovered spans get calls of their own, through the same
    prompt builder but a different call site. Both have to pass the context."""
    _, sent = _decompose(_WITH_CONTEXT, summary=uncovered_summary(["Export invoices"]))
    span_prompts = [p for p in _decompose_prompts(sent) if "task-01-span-" in p]

    assert span_prompts, "the summary produced no span call"
    for prompt in span_prompts:
        assert _BACKGROUND in prompt


def test_adding_context_changes_the_prompt_only_by_the_context_block():
    """A file with the section and the same file without it send the same
    requirements, the same instructions and the same order. The block is the
    whole difference — so nothing about the mandate's own presentation moved."""
    _, with_sent = _decompose(_WITH_CONTEXT)
    _, without_sent = _decompose(_MANDATE)
    # `assemble` joins the blocks of one message with a blank line.
    block = "\n\n" + _context_text(parse_task_file(_WITH_CONTEXT).context)

    with_context = _decompose_prompts(with_sent)
    without = _decompose_prompts(without_sent)

    assert len(with_context) == len(without) == 2
    assert all(block in p for p in with_context)
    assert sorted(p.replace(block, "", 1) for p in with_context) == without


def test_no_context_means_no_background_block():
    _, sent = _decompose(_MANDATE)

    assert _context_text([]) == ""
    for prompt in _decompose_prompts(sent):
        assert "TASK CONTEXT" not in prompt


# --- mandate coverage ---------------------------------------------------------


def test_adding_context_does_not_move_mandate_coverage():
    with_context, _ = _decompose(_WITH_CONTEXT)
    without, _ = _decompose(_MANDATE)

    covered = assess_mandate_coverage(with_context.requirement_map, with_context.obligations)
    baseline = assess_mandate_coverage(without.requirement_map, without.obligations)

    assert covered == baseline
    assert covered.complete


def test_the_same_text_under_an_unrecognised_heading_still_bounds_coverage():
    """The contrast that makes the test above discriminating. Before #212 a
    Context heading was an unrecognised one, so its text was unread source and
    the mandate could not be complete. Any other unknown heading still is."""
    decomposition, _ = _decompose(_UNRECOGNISED)

    coverage = assess_mandate_coverage(decomposition.requirement_map, decomposition.obligations)

    assert coverage.unread_source_blocks == 1
    assert not coverage.complete
