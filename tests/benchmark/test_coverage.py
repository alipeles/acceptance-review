"""M3.3 acceptance: M3.1's implementation-coverage classification and M3.2's
unrequested-change detection feed the M-B0.3 gap-detection/false-alarm
metric. Archetypes #1 (missed obligation), #2 (missed qualifier), and #8
(unrequested change) each contribute a real, hand-calculable gap_recall/
gap_precision figure.

classify_case makes three schema-constrained calls per case (decompose,
classify_coverage, detect_unrequested_changes); per the replay-first
invariant the test client dispatches a fixed, hand-authored response per
call by its response schema name — no live calls.
"""

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from acceptance.benchmark.coverage import classify_case
from acceptance.benchmark.fixtures import build_benchmark_case
from acceptance.change.diff import extract_change_set
from acceptance.llm import Mode, ModelClient, TranscriptStore

ARCHETYPES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "archetypes"


def _client_dispatching(responses_by_schema: dict) -> ModelClient:
    def completion_fn(**kwargs):
        schema_name = kwargs["response_format"]["json_schema"]["name"]
        content = json.dumps(responses_by_schema[schema_name])
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

    return ModelClient(
        model="anthropic/claude-sonnet-5",
        mode=Mode.RECORD,
        store=TranscriptStore(tempfile.mkdtemp()),
        completion_fn=completion_fn,
    )


def _decomposition_response(obligations: list[dict]) -> dict:
    return {
        "obligations": [
            {
                "id": o["id"],
                "description": o["description"],
                "type": o["type"],
                "importance": "critical",
                "explicit": True,
                "observable_behavior": "...",
                "source_quote": o["source_quote"],
            }
            for o in obligations
        ],
        "open_questions": [],
    }


def _classification_response(classifications: list[dict]) -> dict:
    return {
        "classifications": [
            {
                "obligation_id": c["obligation_id"],
                "status": c["status"],
                "rationale": c.get("rationale", "..."),
                "diff_refs": c.get("diff_refs", []),
            }
            for c in classifications
        ]
    }


def test_archetype_1_missed_obligation_yields_full_recall_and_precision(tmp_path):
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")

    obligations = [
        {
            "id": "show-fields",
            "description": "Show the item name, quantity, and unit price",
            "type": "functional",
            "source_quote": "Show the item name, the quantity, and the unit price.",
        },
        {
            "id": "line-total",
            "description": "Include the line total (quantity times unit price)",
            "type": "functional",
            "source_quote": "Include the line total (quantity × unit price).",
        },
        {
            "id": "money-format",
            "description": "Format money as USD with two decimals and a leading $",
            "type": "functional",
            "source_quote": "Format every money value as USD with exactly two decimals",
        },
        {
            "id": "returns-in-parens",
            "description": "Show negative-quantity returns with the quantity and total in parentheses",
            "type": "boundary",
            "source_quote": "For returns (a negative quantity)",
        },
    ]
    client = _client_dispatching(
        {
            "_Decomposition": _decomposition_response(obligations),
            "_Coverage": _classification_response(
                [
                    {"obligation_id": "show-fields", "status": "addressed"},
                    {"obligation_id": "line-total", "status": "addressed"},
                    {"obligation_id": "money-format", "status": "addressed"},
                    {"obligation_id": "returns-in-parens", "status": "not_addressed"},
                ]
            ),
            "_Detections": {"unrequested_changes": []},
        }
    )

    scored = classify_case(case, client)

    gap_findings = [f for f in scored.reviewer_output.findings if f.type == "coverage_gap"]
    assert len(gap_findings) == 1
    assert gap_findings[0].related_obligation == (
        "Show negative-quantity returns with the quantity and total in parentheses"
    )
    assert scored.score.gap_recall == 1.0
    assert scored.score.gap_precision == 1.0


def test_archetype_2_missed_qualifier_yields_full_recall_and_precision(tmp_path):
    case = build_benchmark_case(ARCHETYPES_DIR / "02-qualifier-missed", tmp_path / "repo")

    obligations = [
        {
            "id": "parse-symbol",
            "description": "Parse a leading currency symbol into its ISO code ($ USD, GBP, EUR)",
            "type": "functional",
            "source_quote": "Parse a leading currency symbol into its ISO code",
        },
        {
            "id": "parse-amount",
            "description": "Parse the remaining numeric amount as a float",
            "type": "functional",
            "source_quote": "Parse the remaining numeric amount as a float.",
        },
        {
            "id": "backward-compat",
            "description": "Plain numeric strings with no symbol keep working and default to USD",
            "type": "compatibility",
            "source_quote": "Existing callers pass plain numeric strings with no symbol",
        },
    ]
    client = _client_dispatching(
        {
            "_Decomposition": _decomposition_response(obligations),
            "_Coverage": _classification_response(
                [
                    {"obligation_id": "parse-symbol", "status": "addressed"},
                    {"obligation_id": "parse-amount", "status": "addressed"},
                    {"obligation_id": "backward-compat", "status": "not_addressed"},
                ]
            ),
            "_Detections": {"unrequested_changes": []},
        }
    )

    scored = classify_case(case, client)

    gap_findings = [f for f in scored.reviewer_output.findings if f.type == "coverage_gap"]
    assert len(gap_findings) == 1
    assert gap_findings[0].related_obligation == (
        "Plain numeric strings with no symbol keep working and default to USD"
    )
    assert scored.score.gap_recall == 1.0
    assert scored.score.gap_precision == 1.0


def test_archetype_8_unrequested_change_gap_matches_via_its_obligation(tmp_path):
    fixture_dir = ARCHETYPES_DIR / "08-unrequested-change"
    case = build_benchmark_case(fixture_dir, tmp_path / "repo")
    # Discover the real hunk label for cart.py so the unrequested-change
    # finding carries a genuine diff_ref, same as the checker would produce.
    change_set = extract_change_set(
        Path(case.inputs.repo), case.inputs.base_revision, case.inputs.head_revision
    )
    cart = next(f for f in change_set.files if f.path.endswith("cart.py"))
    cart_ref = f"{cart.path}#0"

    obligations = [
        {
            "id": "apply-discount",
            "description": "Add apply_discount(total, percent) reducing the total by the given percentage, rounded to two decimals",
            "type": "functional",
            "source_quote": "Add `apply_discount(total, percent)` to `cart.py`",
        },
        {
            "id": "leave-existing",
            "description": "Leave existing behavior as-is; only apply_discount was requested",
            "type": "compatibility",
            "source_quote": "existing behavior should be left as-is",
        },
    ]
    client = _client_dispatching(
        {
            "_Decomposition": _decomposition_response(obligations),
            "_Coverage": _classification_response(
                [
                    {"obligation_id": "apply-discount", "status": "addressed"},
                    {
                        "obligation_id": "leave-existing",
                        "status": "partially_addressed",
                        "rationale": "checkout still defaults correctly but gained an untested tax_rate branch.",
                    },
                ]
            ),
            "_Detections": {
                "unrequested_changes": [
                    {
                        "kind": "public_interface",
                        "rationale": "checkout gained a tax_rate parameter and rounding; not requested.",
                        "diff_refs": [cart_ref],
                    }
                ]
            },
        }
    )

    scored = classify_case(case, client)
    findings_by_type = {f.type for f in scored.reviewer_output.findings}

    # Both M3.1 and M3.2 output are fed in as findings...
    assert findings_by_type == {"coverage_gap", "unrequested_change"}
    # ...but only the obligation-linked coverage gap moves the gap metric,
    # matching the ground-truth gap that is itself linked to leave-existing.
    assert scored.score.gap_recall == 1.0
    assert scored.score.gap_precision == 1.0


def test_classify_case_does_not_mutate_the_input_case(tmp_path):
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")
    client = _client_dispatching(
        {
            "_Decomposition": _decomposition_response([]),
            "_Coverage": {"classifications": []},
            "_Detections": {"unrequested_changes": []},
        }
    )

    classify_case(case, client)

    assert case.reviewer_output is None
    assert case.score is None
