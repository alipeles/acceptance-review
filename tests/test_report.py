from acceptance.report import render_report
from acceptance.review_state import (
    Component,
    EvidenceTier,
    Finding,
    Link,
    Obligation,
    ObligationType,
    Review,
)


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


def test_populated_review_lists_obligations_and_findings():
    review = Review(
        mode="local",
        reviewed_revision="abc",
        obligation_map=[
            Obligation(
                id="coupons-use-spread",
                description="Coupons use index + spread.",
                type=ObligationType.FUNCTIONAL,
                importance="critical",
                explicit=True,
                observable_behavior="...",
            )
        ],
        findings=[
            Finding(
                type="weak_test_evidence",
                severity="high",
                description="Filter behavior unsupported",
                evidence_tier=EvidenceTier.STATIC,
                produced_by=Component.STATIC_ANALYZER,
                links=[Link(kind="test", ref="tests/t.py:1")],
            )
        ],
        recommendation=".acceptance/next-instruction.md",
    )

    report = render_report(review)

    assert "  ? Coupons use index + spread." in report
    assert "  - Filter behavior unsupported [static]" in report
    assert "Recommended next instruction: .acceptance/next-instruction.md" in report
