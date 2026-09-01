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

import json
from pathlib import Path

from acceptance.benchmark.coverage import classify_case
from acceptance.benchmark.fixtures import build_benchmark_case
from acceptance.change.diff import extract_change_set
from acceptance.cli import run_check
from acceptance.config import DEFAULT_EMBEDDING_MODEL, DEFAULT_MODEL, RunConfig
from acceptance.llm import Mode, ModelClient, TranscriptStore
from acceptance.review_store import ReviewStore
from tests.support import (
    _EMPTY_BY_SCHEMA,
    WHOLE_SUMMARY_UNCOVERED,
    _completed,
    _fake_response,
    _supplied_enum,
    client_finding_nothing,
    constant_embedding_fn,
)
from tests.support import client_dispatching as _client_dispatching

ARCHETYPES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "archetypes"

# Archetype #1's criteria, for the tests that need the pipeline to reach its
# later stages at all rather than to score a particular figure.
_CRITERIA = [
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
]


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
        "requirement_dispositions": [],
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
    pos = "test_receipt.py::test_positive_line"
    two = "test_receipt.py::test_two_decimal_formatting"
    client = _client_dispatching(
        {
            "_Decomposition": _decomposition_response(obligations),
            # One way to fail per criterion. `obligation_id` is filled per call
            # by the double, since the enumerator answers for one at a time.
            "_Enumeration": {
                "obligation_id": "",
                "defects": [
                    {
                        "slug": "is-wrong",
                        "type": "other",
                        "description": "the stated rule is not honoured",
                        "code_refs": [],
                    }
                ],
                "reason": "",
            },
            # The two real tests catch the three implemented rules and catch
            # nothing about returns, which is the gap archetype #1 poses.
            "_PairVerdicts": {
                "tests": [
                    {
                        "test_id": test_id,
                        "defects": [
                            {"defect_id": f"{oid}/is-wrong", "fails": True, "reason": "asserted"}
                            for oid in ("show-fields", "line-total", "money-format")
                        ]
                        + [{"defect_id": "returns-in-parens/is-wrong", "fails": False}],
                    }
                    for test_id in (pos, two)
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
            # This archetype's task file is a Task paragraph and nothing else,
            # so every obligation comes from the summary step (#317): with the
            # covered answer there is no bullet for the ordinary decomposer to
            # answer about, and the case would score an empty obligation set.
            "_SummarySpans": WHOLE_SUMMARY_UNCOVERED,
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
            # This archetype's task file is a Task paragraph and nothing else,
            # so every obligation comes from the summary step (#317): with the
            # covered answer there is no bullet for the ordinary decomposer to
            # answer about, and the case would score an empty obligation set.
            "_SummarySpans": WHOLE_SUMMARY_UNCOVERED,
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


def test_cli_and_benchmark_share_one_pipeline(tmp_path, monkeypatch):
    """Regression guard for the divergence M7.4 fixed: the CLI and the
    benchmark must derive their Review from the SAME pipeline function.

    They drifted for several milestones — every capability from M4 on reached
    only `classify_case`, so `acceptance check` silently ran a shorter chain
    and could not report test evidence or a verdict. Asserting both paths call
    `pipeline.run_review` makes a future re-divergence fail loudly instead of
    quietly under-reporting.
    """
    import acceptance.benchmark.coverage as benchmark_coverage
    import acceptance.cli as cli_module

    calls: list[str] = []
    reviews: list = []
    real_run_review = benchmark_coverage.run_review

    def tracking_run_review(**kwargs):
        calls.append("called")
        review = real_run_review(**kwargs)
        reviews.append(review)
        return review

    monkeypatch.setattr(benchmark_coverage, "run_review", tracking_run_review)
    monkeypatch.setattr(cli_module, "run_review", tracking_run_review)

    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")
    classify_case(case, client_finding_nothing())
    assert len(calls) == 1  # the benchmark path routes through run_review

    task_file = tmp_path / "task.md"
    task_file.write_text(case.inputs.task_text)
    run_check(
        task=str(task_file),
        base=case.inputs.base_revision,
        head=case.inputs.head_revision,
        config=RunConfig(),
        store=ReviewStore(tmp_path / "reviews"),
        repo=Path(case.inputs.repo),
        client=client_finding_nothing(),
    )
    assert len(calls) == 2  # ...and so does the CLI path

    # Both invocations must run the SAME stages, not merely call the same
    # helper: a conditional inside run_review that skipped a stage for one
    # consumer would keep the call count at 2 while silently diverging again.
    #
    # `task_source.identifier` is excluded for the same reason as
    # `reviewed_revision`: it is where the input came from, not what the pipeline
    # did with it. The CLI read a file and names its path; the benchmark holds the
    # task inline and has no path to name. The digest and text — the parts a
    # re-run actually compares (M7.5) — are still required to match.
    ignore = {"provenance", "reviewed_revision"}
    benchmark_review, cli_review = reviews
    benchmark_state = benchmark_review.model_dump(exclude=ignore)
    cli_state = cli_review.model_dump(exclude=ignore)
    assert benchmark_state["task_source"]["snapshot"] == cli_state["task_source"]["snapshot"]
    for state in (benchmark_state, cli_state):
        del state["task_source"]["identifier"]
    assert benchmark_state == cli_state


def test_the_shared_pipeline_runs_every_stage(tmp_path):
    """The divergence guard proves the two consumers AGREE; it cannot prove the
    shared pipeline is COMPLETE — a stage dropped from run_review would vanish
    from both callers identically and still compare equal.

    So assert the assembled Review carries an artifact from each stage, using a
    client that returns non-empty responses for every schema. A pipeline that
    silently stopped running mapping, strength classification, coverage,
    recommendations or the verdict would leave its artifact empty here.
    """
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")
    change_set = extract_change_set(
        Path(case.inputs.repo), case.inputs.base_revision, case.inputs.head_revision
    )
    receipt = next(f.path for f in change_set.files if f.path.endswith("receipt.py"))
    test_file = next(f.path for f in change_set.files if f.path.endswith("test_receipt.py"))
    test_id = f"{test_file}::test_positive_line"

    client = _client_dispatching(
        {
            "_Decomposition": _decomposition_response(
                [
                    {
                        "id": "show-fields",
                        "description": "Show the item name, quantity, and unit price",
                        "type": "functional",
                        "source_quote": "Show the item name, the quantity, and the unit price.",
                    }
                ]
            ),
            # Two ways to fail, one killed by the discovered test and one not, so
            # every downstream stage has something to do: the reduce sees a
            # partial denominator, the derived edge gets a linked test, and the
            # prescriber gets an uncovered defect to answer about.
            "_Enumeration": {
                "obligation_id": "show-fields",
                "defects": [
                    {
                        "slug": "omits-a-field",
                        "type": "other",
                        "description": "omits a field",
                        "code_refs": [],
                    },
                    {
                        "slug": "wrong-order",
                        "type": "other",
                        "description": "prints the fields in the wrong order",
                        "code_refs": [],
                    },
                ],
                "reason": "",
            },
            "_PairVerdicts": {
                "tests": [
                    {
                        "test_id": test_id,
                        "defects": [
                            {
                                "defect_id": "show-fields/omits-a-field",
                                "fails": True,
                                "reason": "it asserts on the field the defect drops",
                            },
                            {"defect_id": "show-fields/wrong-order", "fails": False},
                        ],
                    }
                ]
            },
            "_Coverage": _classification_response(
                [
                    {
                        "obligation_id": "show-fields",
                        "status": "addressed",
                        "diff_refs": [f"{receipt}#0"],
                    },
                ]
            ),
            "_Detections": {"unrequested_changes": []},
            "_Judgments": {"resolutions": []},
            "_Recommendations": {
                "recommendations": [
                    {
                        "defect_id": "show-fields/wrong-order",
                        "required_inputs": "a receipt line",
                        "boundary_conditions": "none",
                        "expected_output": "all three fields",
                        "required_assertions": ["assert name in line"],
                        "repo_conventions": "test_receipt.py",
                    }
                ]
            },
            "_Mismatches": {"mismatches": []},
        }
    )

    review = classify_case(case, client).reviewer_output
    obligation = review.obligation_map[0]

    assert obligation.description  # decomposition ran
    # Discovery, pair judgement and the derived edge all ran: the criterion's
    # linked test is the one a verdict says would fail on its defect (#316).
    assert obligation.test_evidence == [test_id]
    assert obligation.evidence_class is not None  # enumeration + pairs + the reduce ran
    assert (obligation.covered_defects, obligation.enumerated_defects) == (1, 2)
    assert obligation.achieved_evidence_tier is not None  # the reduce applied a tier
    assert obligation.coverage_status == "addressed"  # coverage classification ran
    assert obligation.coverage_refs  # coverage refs were carried through
    assert review.recommendations  # recommendation generation ran
    assert review.completion is not None  # the verdict was derived


def test_the_shared_pipeline_partitions_the_pair_call(tmp_path):
    """The batching mechanism has its own unit tests; this pins that the
    pipeline actually *calls* it, and that the batch-size control reaches it
    rather than stopping at the signature. A partitioner nothing routes through
    is the exact shape of hole defect injection keeps finding here.

    The control moved with the stage (#316). It used to size the
    test-to-criterion mapping call and is now `pair_batch_size`, sizing the
    (defect, test) judgement — the flag was repointed rather than left accepting
    a value that reached nothing.
    """
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")
    pair_calls: list[list[str]] = []

    def completion_fn(**kwargs):
        spec = kwargs["response_format"]["json_schema"]
        if spec["name"] == "_PairVerdicts":
            # Every pair the call is allowed to answer about, as (test, defect).
            pair_calls.append(
                [
                    (test_id, defect_id)
                    for test_id in _supplied_enum("test_id", **kwargs)
                    for defect_id in _supplied_enum("defect_id", **kwargs)
                ]
            )
        if spec["name"] == "_Decomposition":
            # Real criteria, because pairs are (defect, test) and defects hang
            # off criteria: the default double decomposes to nothing, so there
            # would be nothing to partition and the test would pass on zero.
            return _fake_response(
                json.dumps(_completed(_decomposition_response(_CRITERIA), **kwargs))
            )
        if spec["name"] == "_Enumeration":
            # Two defects per criterion, so a batch size of one has to split.
            return _fake_response(
                json.dumps(
                    _completed(
                        {
                            "obligation_id": "",
                            "defects": [
                                {
                                    "slug": slug,
                                    "type": "other",
                                    "description": f"the behaviour is wrong ({slug})",
                                    "code_refs": [],
                                }
                                for slug in ("is-wrong", "is-also-wrong")
                            ],
                            "reason": "",
                        },
                        **kwargs,
                    )
                )
            )
        return _fake_response(json.dumps(_completed(_EMPTY_BY_SCHEMA[spec["name"]], **kwargs)))

    def run(batch_size):
        pair_calls.clear()
        client = ModelClient(
            model=DEFAULT_MODEL,
            mode=Mode.RECORD,
            store=TranscriptStore(str(tmp_path / f"transcripts-{batch_size}")),
            completion_fn=completion_fn,
            # Two criteria means the linking stage runs, and #259's prefilter
            # embeds them before it asks anything.
            embedding_model=DEFAULT_EMBEDDING_MODEL,
            embedding_fn=constant_embedding_fn,
        )
        classify_case(case, client, pair_batch_size=batch_size)
        return [list(ids) for ids in pair_calls]

    one_per_call = run(1)
    batched = run(500)

    # The control reaches the stage: a smaller batch means more calls. Not "one
    # call at 500" — the stage partitions each test's pairs separately, so the
    # floor is one call per test however large the batch.
    assert len(one_per_call) > len(batched) > 0
    assert all(len(pairs) == 1 for pairs in one_per_call)
    # The same pairs judged either way. Partitioning changes the asking, not the
    # question, which is what makes the control safe to turn.
    assert sorted(p for call in one_per_call for p in call) == sorted(
        p for call in batched for p in call
    )


def test_neither_the_pipeline_nor_the_cli_writes_into_the_reviewed_repo(tmp_path):
    """The reviewed repo is an input, never an output.

    This mattered for the benchmark first: it runs the same review over fixture
    repos, so a write inside the pipeline would mutate the very fixtures the
    scores are computed from.

    It used to assert both halves of a boundary — pipeline writes nothing, CLI
    writes `next-instruction.md` — because an isolation that is trivially true
    proves nothing. M7.3.r1 removed that write entirely, so the contrast is gone
    and the claim is now the stronger one: NOTHING writes into the repo, on
    either path. The CLI's one remaining repo-touching behaviour is *removing* a
    legacy file, covered in `tests/test_cli.py`.
    """
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")
    repo = Path(case.inputs.repo)

    def snapshot() -> set:
        return {p.relative_to(repo) for p in repo.rglob("*") if ".git" not in p.parts}

    before = snapshot()
    classify_case(case, client_finding_nothing())
    assert snapshot() == before

    # The same repo through the CLI, with a review that has a real gap — the
    # case that used to write a file.
    task_file = tmp_path / "task.md"
    task_file.write_text(case.inputs.task_text)
    run_check(
        task=str(task_file),
        base=case.inputs.base_revision,
        head=case.inputs.head_revision,
        config=RunConfig(),
        store=ReviewStore(tmp_path / "reviews"),
        repo=repo,
        client=_client_dispatching(
            {
                "_Decomposition": _decomposition_response(
                    [
                        {
                            "id": "gap-ob",
                            "description": "Handle the empty case",
                            "type": "functional",
                            "source_quote": "Show the item name",
                        }
                    ]
                ),
                "_Mappings": {"mappings": []},
                "_Discrimination": {"discriminations": []},
                "_Coverage": _classification_response(
                    [
                        {"obligation_id": "gap-ob", "status": "not_addressed"},
                    ]
                ),
                "_Detections": {"unrequested_changes": []},
                "_Judgments": {"resolutions": []},
                "_Recommendations": {"recommendations": []},
                "_Mismatches": {"mismatches": []},
            }
        ),
    )
    assert snapshot() == before
    assert not (repo / ".acceptance" / "next-instruction.md").exists()


def test_archetype_4_cannot_reach_strongly_supported_while_its_defect_survives(tmp_path):
    """#316's acceptance, on the archetype it was written for.

    Archetype #4's only test asserts `prorate(30.0, 15, 30) == 15.0`. A 30-day
    month is exactly where a hard-coded `price / 30` and the correct
    `price / days_in_month` agree, so that test cannot tell them apart. The
    judge says so — the pair verdict is *survives* — and the criterion must not
    be strongly supported while it does.

    Asserted as a difference against the same run with the verdict flipped,
    because "not strongly supported" alone would pass on a pipeline that never
    reached the criterion at all.
    """
    case = build_benchmark_case(ARCHETYPES_DIR / "04-non-discriminating-input", tmp_path / "repo")
    test_id = "test_billing.py::test_half_of_a_month"
    defect_id = "daily-rate/hard-codes-thirty"

    def _client(fails: bool):
        verdict = {"defect_id": defect_id, "fails": fails}
        if fails:
            verdict["reason"] = "a non-30-day month would differ"
        return _client_dispatching(
            {
                "_Decomposition": _decomposition_response(
                    [
                        {
                            "id": "daily-rate",
                            "description": "Daily rate is monthly_price divided by days_in_month",
                            "type": "functional",
                            "source_quote": "the daily rate is",
                        }
                    ]
                ),
                # The task file is a Task paragraph and nothing else, so the
                # criterion comes from the summary step (#317) rather than from
                # a bullet the ordinary decomposer answers about.
                "_SummarySpans": WHOLE_SUMMARY_UNCOVERED,
                "_Enumeration": {
                    "obligation_id": "daily-rate",
                    "defects": [
                        {
                            "slug": "hard-codes-thirty",
                            "type": "other",
                            "description": "hard-codes price/30 instead of price/days_in_month",
                            "code_refs": [],
                        }
                    ],
                    "reason": "",
                },
                "_PairVerdicts": {"tests": [{"test_id": test_id, "defects": [verdict]}]},
                "_Coverage": _classification_response(
                    [{"obligation_id": "daily-rate", "status": "addressed"}]
                ),
                "_Detections": {"unrequested_changes": []},
            }
        )

    def rating(fails: bool):
        review = classify_case(case, _client(fails)).reviewer_output
        return next(o for o in review.obligation_map if o.id == "daily-rate")

    surviving = rating(fails=False)
    killing = rating(fails=True)

    assert surviving.evidence_class != "strongly_supported"
    assert killing.evidence_class == "strongly_supported"
    # And the denominator travels with both, so a reader can see what "strongly"
    # was measured over — one defect, which is thin and says so.
    assert (surviving.covered_defects, surviving.enumerated_defects) == (0, 1)
    assert (killing.covered_defects, killing.enumerated_defects) == (1, 1)
