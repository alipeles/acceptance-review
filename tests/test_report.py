"""M7.4 acceptance: the rendered §16 report shows obligation coverage, test
evidence with a per-line evidence tier, advisory unrequested changes, and the
computed verdict."""

from acceptance.review_state import (
    UNREQUESTED_CHANGE,
    CompletionResult,
    CompletionVerdict,
    Component,
    EvidenceTier,
    Finding,
    Link,
    Obligation,
    ObligationType,
    OpenQuestion,
    Review,
    TestRecommendation,
    UnrequestedChangeDisposition,
)
from acceptance.report import render_report


def test_empty_review_renders_the_full_shell():
    report = render_report(Review(mode="local", reviewed_revision="abc"))

    assert report == (
        "Task completion: INDETERMINATE\n"
        "\n"
        "Obligation coverage:\n"
        "  (none)\n"
        "\n"
        "Test evidence:\n"
        "  (none)\n"
        "\n"
        "Unrequested changes:\n"
        "  (none)\n"
        "\n"
        "Recommended next instruction: (none)"
    )


def _obligation(description: str, coverage: str | None, evidence: str | None) -> Obligation:
    return Obligation(
        id=description.lower().replace(" ", "-")[:20],
        description=description,
        type=ObligationType.FUNCTIONAL,
        importance="critical",
        explicit=True,
        observable_behavior="...",
        coverage_status=coverage,
        evidence_class=evidence,
        achieved_evidence_tier=EvidenceTier.STATIC if evidence else None,
    )


def test_report_renders_both_axes_with_tiers_and_the_verdict():
    review = Review(
        mode="local",
        reviewed_revision="abc",
        obligation_map=[
            _obligation("CSV generation implemented", "addressed", "strongly_supported"),
            _obligation("Active filters applied", "not_addressed", "unsupported"),
            _obligation("Column order preserved", "unclear", "indeterminate"),
        ],
        findings=[
            Finding(
                type=UNREQUESTED_CHANGE,
                severity="medium",
                description="Export filename behavior changed",
                evidence_tier=EvidenceTier.STATIC,
                produced_by=Component.STATIC_ANALYZER,
                links=[Link(kind="code", ref="export.py#@@ -1 +1 @@")],
                disposition=UnrequestedChangeDisposition.SEPARABLE,
            )
        ],
        completion=CompletionResult(
            verdict=CompletionVerdict.INCOMPLETE,
            rationale="1 obligation(s) not fully implemented.",
            limitations=["Judgments are static inferences unless a higher tier is recorded."],
        ),
        recommendation=".acceptance/next-instruction.md",
    )

    report = render_report(review)

    # The §16 headline is the real computed verdict.
    assert "Task completion: INCOMPLETE" in report
    assert "1 obligation(s) not fully implemented." in report
    # Implementation-coverage axis: ✓ addressed, ✗ not, ? uncertain.
    assert "  ✓ CSV generation implemented" in report
    assert "  ✗ Active filters applied" in report
    assert "  ? Column order preserved" in report
    # Test-evidence axis: every line carries its class AND its evidence tier.
    assert "  ✓ CSV generation implemented  [strongly supported; tier: static]" in report
    assert "  ✗ Active filters applied  [unsupported; tier: static]" in report
    # Unrequested changes are advisory, with their disposition shown (M7.6 spirit).
    assert "  ! [separable] Export filename behavior changed" in report
    assert "Evidence limitations:" in report
    assert "Recommended next instruction: .acceptance/next-instruction.md" in report


def test_every_test_evidence_line_shows_a_tier():
    # M7.4 acceptance: "every test-evidence line shows its evidence tier."
    review = Review(
        mode="local",
        reviewed_revision="abc",
        obligation_map=[
            _obligation("A", "addressed", "strongly_supported"),
            _obligation("B", "addressed", "partially_supported"),
            _obligation("C", "addressed", None),  # unclassified -> tier: none
        ],
    )

    evidence_section = render_report(review).split("Test evidence:")[1].split("Unrequested")[0]
    lines = [line for line in evidence_section.splitlines() if line.strip()]

    assert len(lines) == 3
    assert all("tier: " in line for line in lines)


def test_unclassified_obligation_renders_as_uncertain():
    review = Review(
        mode="local",
        reviewed_revision="abc",
        obligation_map=[_obligation("Not yet analyzed", None, None)],
    )

    report = render_report(review)

    assert "  ? Not yet analyzed" in report
    assert "[unclassified; tier: none]" in report


def test_open_questions_and_recommendations_are_rendered():
    review = Review(
        mode="local",
        reviewed_revision="abc",
        obligation_map=[_obligation("A", "addressed", "nominally_supported")],
        open_questions=[
            OpenQuestion(id="q-1", question="Minus sign or parentheses?"),
            OpenQuestion(id="q-2", question="Tax inclusive?", resolved=True),
        ],
        recommendations=[
            TestRecommendation(
                obligation_id="a",
                criterion="Daily rate uses days_in_month",
                required_inputs="A non-30-day month",
                boundary_conditions="0 days",
                expected_output="price/28*days",
                required_assertions=["assert prorate(280, 14, 28) == 140.0"],
                plausible_defect="hard-codes /30",
                repo_conventions="test_billing.py",
            )
        ],
    )

    report = render_report(review)

    assert "  [open] Minus sign or parentheses?" in report
    assert "  [resolved] Tax inclusive?" in report
    assert "Recommended tests:" in report
    assert "  - Daily rate uses days_in_month" in report
    assert "detects: hard-codes /30" in report
