"""M3.3 acceptance: M3.1's implementation-coverage classification and M3.2's
unrequested-change detection feed the M-B0.3 gap-detection/false-alarm
metric. Archetypes #1 (missed obligation), #2 (missed qualifier), and #8
(unrequested change) each contribute a real, hand-calculable gap_recall/
gap_precision figure.

M3.5.1 (DR-081) adds the unrequested-change axis: archetype #8 also
contributes an unrequested_precision/unrequested_recall figure, scored by
file against `unrequested_changes` ground truth — never via any obligation's
coverage classification, since an unrequested-change finding carries no
`related_obligation` at all.

M5.5 adds the test-evidence chain (discover -> map -> extract -> discriminate
-> classify strength) ahead of coverage: archetype #1 also contributes a real
evidence_agreement figure, backed by the checker's own classification of its
real candidate tests.

classify_case makes several schema-constrained calls per case (decompose,
test mapping, discrimination when a criterion has a mapped test, coverage
classification, unrequested-change detection); per the replay-first
invariant the test client dispatches a fixed, hand-authored response per
call by its response schema name — no live calls.
"""

from pathlib import Path

from acceptance.benchmark.coverage import classify_case
from acceptance.benchmark.fixtures import build_benchmark_case
from acceptance.change.diff import extract_change_set
from tests.support import client_dispatching as _client_dispatching

ARCHETYPES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "archetypes"


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
            "_Mappings": {"mappings": []},
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
            "_Recommendations": {"recommendations": []},
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
    # M7.2: a real coverage gap yields an `incomplete` verdict.
    assert scored.reviewer_output.completion.verdict.value == "incomplete"


def test_archetype_1_evidence_agreement_reports_a_real_number(tmp_path):
    """M5.5 acceptance: the checker's own evidence-strength classification —
    fed by real M4.1 discovery + M4.2 mapping + M5.1 extraction + M5.2
    discrimination — agrees with archetype #1's ground truth."""
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")

    obligations = [
        {"id": "show-fields", "description": "Show the item name, quantity, and unit price",
         "type": "functional", "source_quote": "Show the item name, the quantity, and the unit price."},
        {"id": "line-total", "description": "Include the line total (quantity times unit price)",
         "type": "functional", "source_quote": "Include the line total (quantity × unit price)."},
        {"id": "money-format", "description": "Format money as USD with two decimals and a leading $",
         "type": "functional", "source_quote": "Format every money value as USD with exactly two decimals"},
        {"id": "returns-in-parens",
         "description": "Show negative-quantity returns with the quantity and total in parentheses",
         "type": "boundary", "source_quote": "For returns (a negative quantity)"},
    ]
    pos = "test_receipt.py::test_positive_line"
    two = "test_receipt.py::test_two_decimal_formatting"
    client = _client_dispatching(
        {
            "_Decomposition": _decomposition_response(obligations),
            "_Mappings": {
                "mappings": [
                    {"test_id": pos, "obligation_ids": ["show-fields", "line-total", "money-format"], "rationale": "."},
                    {"test_id": two, "obligation_ids": ["show-fields", "line-total", "money-format"], "rationale": "."},
                ]
            },
            "_Discrimination": {
                "obligations": [
                    {"obligation_id": "show-fields", "defects": [
                        {"description": "wrong/omitted field", "would_be_caught": True, "reason": "exact line string asserted"},
                    ]},
                    {"obligation_id": "line-total", "defects": [
                        {"description": "wrong total formula", "would_be_caught": True, "reason": "exact total asserted"},
                    ]},
                    {"obligation_id": "money-format", "defects": [
                        {"description": "wrong currency formatting", "would_be_caught": True, "reason": "exact $ format asserted"},
                    ]},
                    # returns-in-parens has no mapped test, so it's never sent here.
                ]
            },
            "_Coverage": _classification_response(
                [
                    {"obligation_id": "show-fields", "status": "addressed"},
                    {"obligation_id": "line-total", "status": "addressed"},
                    {"obligation_id": "money-format", "status": "addressed"},
                    {"obligation_id": "returns-in-parens", "status": "not_addressed"},
                ]
            ),
            "_Detections": {"unrequested_changes": []},
            "_Recommendations": {"recommendations": []},
        }
    )

    scored = classify_case(case, client)

    by_id = {o.id: o for o in scored.reviewer_output.obligation_map}
    assert by_id["show-fields"].evidence_class == "strongly_supported"
    assert by_id["line-total"].evidence_class == "strongly_supported"
    assert by_id["money-format"].evidence_class == "strongly_supported"
    assert by_id["returns-in-parens"].evidence_class == "unsupported"  # no mapped test

    # Reviewer descriptions match ground truth exactly by construction here, so
    # exact-string scoring (no alignment client) already agrees fully: 4/4.
    assert scored.score.evidence_agreement == 1.0


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
            "_Mappings": {"mappings": []},
            "_Decomposition": _decomposition_response(obligations),
            "_Coverage": _classification_response(
                [
                    {"obligation_id": "parse-symbol", "status": "addressed"},
                    {"obligation_id": "parse-amount", "status": "addressed"},
                    {"obligation_id": "backward-compat", "status": "not_addressed"},
                ]
            ),
            "_Detections": {"unrequested_changes": []},
            "_Recommendations": {"recommendations": []},
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
            "description": "Preserve the existing checkout behavior; only apply_discount was requested",
            "type": "compatibility",
            "source_quote": "existing behavior should be left as-is",
        },
    ]
    client = _client_dispatching(
        {
            "_Mappings": {"mappings": []},
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
                        "requested_by_obligation": False,
                    }
                ]
            },
            # cart.py is modified (not a pure addition) and leave-existing is not
            # `addressed`, so the disposition escalates to a model judgment.
            "_DispositionJudgment": {
                "disposition": "risky",
                "rationale": "edits checkout's existing public signature; could hide a regression.",
            },
            "_Recommendations": {"recommendations": []},
        }
    )

    scored = classify_case(case, client)
    findings_by_type = {f.type for f in scored.reviewer_output.findings}

    # Both M3.1 and M3.2 output are fed in as findings, plus M6.1's
    # declaration-absent finding (this archetype ships no declaration.md)...
    assert findings_by_type == {"coverage_gap", "unrequested_change", "declaration_absent"}
    # ...but only the obligation-linked coverage gap moves the gap metric,
    # matching the ground-truth gap that is itself linked to leave-existing.
    assert scored.score.gap_recall == 1.0
    assert scored.score.gap_precision == 1.0
    # The unrequested-change axis is scored independently, by file, from the
    # unrequested_change finding itself.
    assert scored.score.unrequested_recall == 1.0
    assert scored.score.unrequested_precision == 1.0


def test_archetype_8_unrequested_change_metric_does_not_route_through_coverage(tmp_path):
    """M3.5.1 acceptance: even if leave-existing's coverage classification
    finds nothing wrong (addressed, not partially_addressed — so the gap
    metric misses it entirely), the unrequested-change axis still catches
    the unrequested change on its own, because it is scored from the
    unrequested_change finding directly, never through any obligation."""
    fixture_dir = ARCHETYPES_DIR / "08-unrequested-change"
    case = build_benchmark_case(fixture_dir, tmp_path / "repo")
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
            "description": "Preserve the existing checkout behavior; only apply_discount was requested",
            "type": "compatibility",
            "source_quote": "existing behavior should be left as-is",
        },
    ]
    client = _client_dispatching(
        {
            "_Mappings": {"mappings": []},
            "_Decomposition": _decomposition_response(obligations),
            "_Coverage": _classification_response(
                [
                    {"obligation_id": "apply-discount", "status": "addressed"},
                    # Deliberately wrong/optimistic: a checker that missed the
                    # regression in its coverage classification entirely.
                    {"obligation_id": "leave-existing", "status": "addressed"},
                ]
            ),
            "_Detections": {
                "unrequested_changes": [
                    {
                        "kind": "public_interface",
                        "rationale": "checkout gained a tax_rate parameter and rounding; not requested.",
                        "diff_refs": [cart_ref],
                        "requested_by_obligation": False,
                    }
                ]
            },
            # cart.py is modified (not a pure addition) and leave-existing is not
            # `addressed`, so the disposition escalates to a model judgment.
            "_DispositionJudgment": {
                "disposition": "risky",
                "rationale": "edits checkout's existing public signature; could hide a regression.",
            },
            "_Recommendations": {"recommendations": []},
        }
    )

    scored = classify_case(case, client)

    # No coverage_gap finding at all — leave-existing was (wrongly) addressed.
    assert not [f for f in scored.reviewer_output.findings if f.type == "coverage_gap"]
    assert scored.score.gap_recall == 0.0
    # But the unrequested-change axis still scores full recall/precision,
    # entirely independent of the (wrong) coverage classification.
    assert scored.score.unrequested_recall == 1.0
    assert scored.score.unrequested_precision == 1.0


def test_declaration_present_is_parsed_onto_the_review(tmp_path):
    # M6.1: archetype #7 ships a real (partial, 4-of-9-section) declaration.md
    # -- it must be parsed onto Review.declaration, and NO declaration_absent
    # finding should appear since one was actually supplied.
    case = build_benchmark_case(ARCHETYPES_DIR / "07-declaration-mismatch", tmp_path / "repo")

    obligations = [
        {
            "id": "get-user",
            "description": "Return the user record matching user_id from the users mapping",
            "type": "functional",
            "source_quote": "returning the user record (a dict) that matches `user_id`",
        },
    ]
    client = _client_dispatching(
        {
            "_Mappings": {"mappings": []},
            "_Decomposition": _decomposition_response(obligations),
            "_Coverage": _classification_response(
                [{"obligation_id": "get-user", "status": "addressed"}]
            ),
            "_Detections": {"unrequested_changes": []},
            "_Recommendations": {"recommendations": []},
            "_Mismatches": {"mismatches": []},
        }
    )

    scored = classify_case(case, client)
    review = scored.reviewer_output

    assert review.declaration is not None
    assert review.declaration.mandate_as_understood == (
        "Provide a lookup that returns a user record by its id."
    )
    # Sections the fixture omits are empty, not missing.
    assert review.declaration.scope_exclusions == ""
    assert "declaration_absent" not in {f.type for f in review.findings}


def test_archetype_7_declaration_overclaim_produces_a_mismatch_finding(tmp_path):
    # M6.2 acceptance: archetype #7's declaration claims get_user raises
    # KeyError on a missing id, but the code returns None and no test exercises
    # it -- a declaration_mismatch finding, obligation-less and advisory.
    case = build_benchmark_case(ARCHETYPES_DIR / "07-declaration-mismatch", tmp_path / "repo")

    obligations = [
        {
            "id": "get-user",
            "description": "Return the user record matching user_id from the users mapping",
            "type": "functional",
            "source_quote": "returning the user record (a dict) that matches `user_id`",
        },
    ]
    client = _client_dispatching(
        {
            "_Mappings": {"mappings": []},
            "_Decomposition": _decomposition_response(obligations),
            "_Coverage": _classification_response(
                [{"obligation_id": "get-user", "status": "addressed"}]
            ),
            "_Detections": {"unrequested_changes": []},
            "_Recommendations": {"recommendations": []},
            "_Mismatches": {
                "mismatches": [
                    {
                        "claim": "get_user raises KeyError with a clear message on a missing id",
                        "rationale": (
                            "The implementation returns None on a missing id and no test "
                            "exercises the missing-id path."
                        ),
                    }
                ]
            },
        }
    )

    scored = classify_case(case, client)
    findings = scored.reviewer_output.findings
    mismatch_findings = [f for f in findings if f.type == "declaration_mismatch"]

    assert len(mismatch_findings) == 1
    assert mismatch_findings[0].related_obligation is None  # obligation-less
    assert mismatch_findings[0].severity == "low"  # advisory, not acceptance-blocking


def test_classify_case_does_not_mutate_the_input_case(tmp_path):
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")
    client = _client_dispatching(
        {
            "_Mappings": {"mappings": []},
            "_Decomposition": _decomposition_response([]),
            "_Coverage": {"classifications": []},
            "_Detections": {"unrequested_changes": []},
            "_Recommendations": {"recommendations": []},
        }
    )

    classify_case(case, client)

    assert case.reviewer_output is None
    assert case.score is None
