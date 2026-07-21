"""M1.2 acceptance: decompose a task into typed obligations.

Decomposition is a schema-constrained model call; per the M0.4/M0.5 replay-first
invariant these tests inject the recorded model response (a hand-authored
fixture) via the harness's completion_fn — no live calls. The response is what a
good model returns for the §9.1 example and archetype #1; the test verifies the
pipeline turns it into typed Obligations with ids and source spans. The model's
actual decomposition accuracy is measured separately by the benchmark (M-B*).
"""

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from acceptance.llm import Mode, ModelClient, TranscriptStore
from acceptance.requirement.obligations import decompose
from acceptance.requirement.task_file import parse_task_file
from acceptance.review_state import ObligationType

ARCHETYPES = Path(__file__).resolve().parents[1] / "fixtures" / "archetypes"

# The §9.1 floating-rate mandate as a §7.1 task file.
FLOATING_RATE_TASK = """# Task
Add floating-rate bonds using an index curve plus contractual spread. Accrual periods run the 26th through the 25th. Missing rate observations must produce an explicit error. Existing fixed-rate behavior must not change.
"""

# Recorded model response for the §9.1 example: the five derived criteria (§9.1).
FLOATING_RATE_RESPONSE = {
    "obligations": [
        {
            "id": "coupons-use-index-plus-spread",
            "description": "Coupons use the index curve plus the contractual spread.",
            "type": "functional",
            "importance": "critical",
            "explicit": True,
            "observable_behavior": "coupon = index(date) + contractual spread",
            "source_quote": "using an index curve plus contractual spread",
        },
        {
            "id": "accrual-26th-to-25th",
            "description": "Rate selection follows the 26th-through-25th accrual period.",
            "type": "boundary",
            "importance": "critical",
            "explicit": True,
            "observable_behavior": "the fixing chosen falls in the 26th-to-25th window",
            "source_quote": "Accrual periods run the 26th through the 25th.",
        },
        {
            "id": "missing-observation-errors",
            "description": "A missing rate observation produces an explicit error.",
            "type": "error_handling",
            "importance": "critical",
            "explicit": True,
            "observable_behavior": "a structured error is raised when an observation is missing",
            "source_quote": "Missing rate observations must produce an explicit error.",
        },
        {
            "id": "fixed-rate-unchanged",
            "description": "Existing fixed-rate behavior is unchanged.",
            "type": "regression",
            "importance": "critical",
            "explicit": True,
            "observable_behavior": "fixed-rate coupons match pre-change output",
            "source_quote": "Existing fixed-rate behavior must not change.",
        },
        {
            "id": "expose-selected-observation-and-spread",
            "description": "Outputs expose the selected observation and the spread.",
            "type": "explanation_observability",
            "importance": "normal",
            "explicit": False,
            "observable_behavior": "the result reports the fixing date and spread used",
            "source_quote": "using an index curve plus contractual spread",
        },
    ]
}


def _client_returning(response: dict) -> ModelClient:
    def completion_fn(**kwargs):
        content = json.dumps(response)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

    # Isolated ephemeral store so the injected response is always used and no
    # transcript leaks into the repo's .acceptance/ cache.
    return ModelClient(
        model="anthropic/claude-sonnet-5",
        mode=Mode.RECORD,
        store=TranscriptStore(tempfile.mkdtemp()),
        completion_fn=completion_fn,
    )


def test_floating_rate_example_yields_five_typed_criteria():
    parsed = parse_task_file(FLOATING_RATE_TASK)
    obligations = decompose(parsed, _client_returning(FLOATING_RATE_RESPONSE))

    assert len(obligations) == 5
    types = [o.type for o in obligations]
    assert types == [
        ObligationType.FUNCTIONAL,
        ObligationType.BOUNDARY,
        ObligationType.ERROR_HANDLING,
        ObligationType.REGRESSION,
        ObligationType.EXPLANATION_OBSERVABILITY,
    ]
    # Every obligation has a unique id.
    assert len({o.id for o in obligations}) == 5


def test_each_obligation_links_to_its_source_span():
    parsed = parse_task_file(FLOATING_RATE_TASK)
    obligations = decompose(parsed, _client_returning(FLOATING_RATE_RESPONSE))

    for obligation in obligations:
        assert obligation.source_spans, f"{obligation.id} has no source span"
        for span in obligation.source_spans:
            assert parsed.source[span.start : span.end] == span.text


def test_archetype_1_includes_the_omitted_obligation():
    """On archetype #1 the omitted (negative-quantity) obligation is present."""
    task = (ARCHETYPES / "01-missed-obligation" / "task.md").read_text()
    parsed = parse_task_file(task)

    response = {
        "obligations": [
            {
                "id": "show-fields",
                "description": "Show the item name, quantity, and unit price.",
                "type": "functional",
                "importance": "critical",
                "explicit": True,
                "observable_behavior": "the line shows name, quantity, unit price",
                "source_quote": "Show the item name, the quantity, and the unit price.",
            },
            {
                "id": "line-total",
                "description": "Include the line total (quantity times unit price).",
                "type": "functional",
                "importance": "critical",
                "explicit": True,
                "observable_behavior": "the line shows quantity times unit price",
                "source_quote": "Include the line total (quantity × unit price).",
            },
            {
                "id": "money-format",
                "description": "Format money as USD with two decimals and a leading $.",
                "type": "functional",
                "importance": "critical",
                "explicit": True,
                "observable_behavior": "money renders as $ with two decimals",
                "source_quote": "Format every money value as USD with exactly two decimals and a leading `$`.",
            },
            {
                "id": "returns-in-parentheses",
                "description": "Show negative-quantity returns in parentheses.",
                "type": "boundary",
                "importance": "critical",
                "explicit": True,
                "observable_behavior": "a return shows quantity and total in parentheses",
                "source_quote": "For returns (a negative quantity), show the quantity and the line total in",
            },
        ]
    }

    obligations = decompose(parsed, _client_returning(response))
    ids = {o.id for o in obligations}
    assert "returns-in-parentheses" in ids
    returns = next(o for o in obligations if o.id == "returns-in-parentheses")
    assert returns.source_spans
    assert parsed.source[returns.source_spans[0].start : returns.source_spans[0].end] == returns.source_spans[0].text


def test_duplicate_ids_are_made_unique():
    parsed = parse_task_file(FLOATING_RATE_TASK)
    response = {
        "obligations": [
            {
                "id": "dup",
                "description": "First.",
                "type": "functional",
                "importance": "normal",
                "explicit": True,
                "observable_behavior": "...",
                "source_quote": "floating-rate bonds",
            },
            {
                "id": "dup",
                "description": "Second.",
                "type": "functional",
                "importance": "normal",
                "explicit": True,
                "observable_behavior": "...",
                "source_quote": "contractual spread",
            },
        ]
    }
    obligations = decompose(parsed, _client_returning(response))
    assert [o.id for o in obligations] == ["dup", "dup-2"]
