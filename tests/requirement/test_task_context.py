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

from acceptance.requirement.obligations import _context_block, _user_prompt, decompose
from acceptance.requirement.registry import build_registry
from acceptance.requirement.task_file import ParsedTaskFile, parse_task_file
from acceptance.verdict import assess_mandate_coverage
from tests.support import client_returning_capturing_prompts, uncovered_summary

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


def _decompose(task: str, summary: dict | None = None):
    client, sent = client_returning_capturing_prompts(_RESPONSE, summary=summary)
    return decompose(parse_task_file(task), client), sent


def _decompose_prompts(sent: list[dict]) -> list[str]:
    """What the per-requirement decompose calls sent, in a stable order.

    The calls are issued concurrently, so arrival order is not stable.
    """
    return sorted(entry["prompt"] for entry in sent if entry["schema"] != "_SummarySpans")


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
    prompts = _decompose_prompts(sent)

    assert len(prompts) == 2
    for prompt in prompts:
        head, requirements = prompt.split("The complete set of requirements", 1)
        assert "BACKGROUND" in head
        assert _BACKGROUND in head
        # Outside the requirement list, and never rendered as a requirement.
        assert _BACKGROUND not in requirements
        assert f"] {_BACKGROUND}" not in prompt


def test_a_span_call_for_the_opening_summary_shows_the_context_too():
    """The summary's uncovered spans get calls of their own, through the same
    prompt builder but a different call site. Both have to pass the context."""
    _, sent = _decompose(_WITH_CONTEXT, summary=uncovered_summary(["Export invoices"]))
    span_prompts = [p for p in _decompose_prompts(sent) if "task-01-span-" in p]

    assert span_prompts, "the summary produced no span call"
    for prompt in span_prompts:
        assert _BACKGROUND in prompt.split("The complete set of requirements", 1)[0]


def test_adding_context_changes_the_prompt_only_by_the_context_block():
    """A file with the section and the same file without it send the same
    requirements, the same instructions and the same order. The block is the
    whole difference — so nothing about the mandate's own presentation moved."""
    _, with_sent = _decompose(_WITH_CONTEXT)
    _, without_sent = _decompose(_MANDATE)
    # Each line of the block is followed by a newline when the prompt is joined.
    block = "".join(f"{line}\n" for line in _context_block(parse_task_file(_WITH_CONTEXT).context))

    with_context = _decompose_prompts(with_sent)
    without = _decompose_prompts(without_sent)

    assert len(with_context) == len(without) == 2
    assert sorted(p.replace(block, "", 1) for p in with_context) == without
    assert all(block in p for p in with_context)


def test_no_context_means_no_background_block():
    registry = build_registry(parse_task_file(_MANDATE))

    assert _user_prompt(registry, "constraint-01", context=[]) == _user_prompt(
        registry, "constraint-01"
    )
    assert "BACKGROUND" not in _user_prompt(registry, "constraint-01")


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
