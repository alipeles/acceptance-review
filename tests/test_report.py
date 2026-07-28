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
import re

from acceptance.report import render_next_instruction, render_report


def test_empty_review_renders_the_full_shell():
    report = render_report(Review(mode="local", reviewed_revision="abc"))

    assert report == (
        "Task completion: INDETERMINATE\n"
        "\n"
        "Obligations:\n"
        "  (none)\n"
        "\n"
        "Unrequested changes:\n"
        "  (none)\n"
        "\n"
        "Recommended next instruction: (none)"
    )


def _obligation(
    description: str,
    coverage: str | None,
    evidence: str | None,
    coverage_refs: list[str] | None = None,
    tests: list[str] | None = None,
) -> Obligation:
    return Obligation(
        id=description.lower().replace(" ", "-")[:20],
        description=description,
        type=ObligationType.FUNCTIONAL,
        importance="critical",
        explicit=True,
        observable_behavior="...",
        coverage_status=coverage,
        coverage_refs=coverage_refs or [],
        evidence_class=evidence,
        test_evidence=tests or [],
        achieved_evidence_tier=EvidenceTier.STATIC if evidence else None,
    )


def test_report_renders_each_obligation_with_both_axes_numbered():
    review = Review(
        mode="local",
        reviewed_revision="abc",
        obligation_map=[
            _obligation(
                "CSV generation implemented", "addressed", "strongly_supported",
                coverage_refs=["export.py#@@ -1 +9 @@"],
                tests=["tests/test_export.py::test_generates_csv"],
            ),
            _obligation("Active filters applied", "not_addressed", "unsupported"),
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

    assert "Task completion: INCOMPLETE" in report
    # Obligations are numbered, with both axes nested beneath each.
    assert "  1. CSV generation implemented" in report
    assert "  2. Active filters applied" in report
    assert "       code evidence: addressed" in report
    assert "       test evidence: strongly supported  [tier: static]" in report
    assert "       code evidence: not addressed" in report
    # Evidence items are numbered <obligation>.<item>, continuously across axes.
    assert "         1.1  export.py#@@ -1 +9 @@" in report
    assert "         1.2  tests/test_export.py::test_generates_csv" in report
    # An obligation with neither axis satisfied says so explicitly.
    assert "(no corresponding change)" in report
    assert "(no mapped test)" in report
    # Unrequested changes are advisory, numbered, with their disposition.
    assert "  1. [separable] Export filename behavior changed" in report
    assert "Evidence limitations:" in report
    assert "Recommended next instruction: .acceptance/next-instruction.md" in report


def test_status_is_stated_in_words_not_symbols():
    review = Review(
        mode="local",
        reviewed_revision="abc",
        obligation_map=[
            _obligation("A", "addressed", "strongly_supported"),
            _obligation("B", "not_addressed", "unsupported"),
            _obligation("C", "unclear", "indeterminate"),
        ],
    )

    report = render_report(review)

    assert "\u2713" not in report and "\u2717" not in report
    for word in ("addressed", "not addressed", "unclear", "strongly supported", "unsupported"):
        assert word in report


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

    report = render_report(review)
    evidence_lines = [ln for ln in report.splitlines() if "test evidence:" in ln]

    assert len(evidence_lines) == 3
    assert all("tier: " in line for line in evidence_lines)


def test_test_citations_name_the_test_not_just_the_file():
    review = Review(
        mode="local",
        reviewed_revision="abc",
        obligation_map=[
            _obligation(
                "A", "addressed", "strongly_supported",
                tests=["tests/test_billing.py::test_half_of_a_month"],
            )
        ],
    )

    report = render_report(review)

    assert "tests/test_billing.py::test_half_of_a_month" in report


def test_unclassified_obligation_renders_as_unclassified():
    review = Review(
        mode="local",
        reviewed_revision="abc",
        obligation_map=[_obligation("Not yet analyzed", None, None)],
    )

    report = render_report(review)

    assert "  1. Not yet analyzed" in report
    assert "code evidence: unclassified" in report
    assert "test evidence: unclassified  [tier: none]" in report


def test_open_questions_and_recommendations_are_numbered():
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

    assert "  1. [open] Minus sign or parentheses?" in report
    assert "  2. [resolved] Tax inclusive?" in report
    assert "  1. Daily rate uses days_in_month" in report
    assert "detects: hard-codes /30" in report


def test_tier_label_comes_from_the_recorded_tier_not_a_hardcoded_string():
    """Every other fixture uses STATIC, so a hardcoded "tier: static" would
    pass. Use a higher tier to prove the label is read from the obligation."""
    obligation = _obligation("Executed behavior", "addressed", "strongly_supported")
    review = Review(
        mode="local",
        reviewed_revision="abc",
        obligation_map=[
            obligation.model_copy(update={"achieved_evidence_tier": EvidenceTier.DEFECT_KILLED})
        ],
    )

    report = render_report(review)

    assert "[tier: defect-killed]" in report
    assert "tier: static" not in report


def test_multi_word_verdict_renders_as_the_16_headline():
    """NO_MATERIAL_GAPS is the multi-word case: underscores become hyphens and
    the whole verdict is upper-cased. Other tests only cover INCOMPLETE."""
    review = Review(
        mode="local",
        reviewed_revision="abc",
        obligation_map=[_obligation("A", "addressed", "strongly_supported")],
        completion=CompletionResult(
            verdict=CompletionVerdict.NO_MATERIAL_GAPS,
            rationale="Every obligation is addressed and strongly supported.",
            limitations=["No material gaps found at the achievable evidence tier."],
        ),
    )

    report = render_report(review)

    assert "Task completion: NO-MATERIAL-GAPS" in report
    # §3.7: a positive verdict must carry its bounding caveat.
    assert "achievable evidence tier" in report


def test_the_two_axes_render_independently_for_the_same_obligation():
    """The load-bearing case: code that responds (coverage `addressed`) whose
    tests do NOT discriminate (`nominally_supported`). A renderer that
    collapsed the two axes into one label would show this as fine on both."""
    review = Review(
        mode="local",
        reviewed_revision="abc",
        obligation_map=[
            _obligation("Daily rate uses days_in_month", "addressed", "nominally_supported")
        ],
    )

    report = render_report(review)

    assert "code evidence: addressed" in report
    assert "test evidence: nominally supported" in report


# --- M7.3: the §10.1 step-12 next instruction ---


def _gap_finding(obligation_description: str) -> Finding:
    return Finding(
        type="coverage_gap", severity="high", description="missing",
        evidence_tier=EvidenceTier.STATIC, produced_by=Component.STATIC_ANALYZER,
        links=[Link(kind="requirement", ref="x", text="x")],
        related_obligation=obligation_description,
    )


def _recommendation(criterion: str, defect: str) -> TestRecommendation:
    return TestRecommendation(
        obligation_id=criterion.lower().replace(" ", "-")[:20],
        criterion=criterion,
        required_inputs="a non-30-day month",
        boundary_conditions="0 days used, a full month",
        expected_output="price/days_in_month * days, rounded",
        required_assertions=["assert prorate(280, 14, 28) == 140.0"],
        plausible_defect=defect,
        repo_conventions="test_billing.py",
    )


def test_multi_gap_review_names_each_gap_and_its_distinguishing_test():
    """M7.3 acceptance: on a multi-gap review the instruction names each gap
    and the discriminating test that closes it (§10.1 style)."""
    review = Review(
        mode="local",
        reviewed_revision="abc",
        obligation_map=[_obligation("Daily rate", "not_addressed", "unsupported")],
        findings=[
            _gap_finding("Daily rate is monthly_price divided by days_in_month"),
            _gap_finding("Round the result to two decimals"),
        ],
        recommendations=[
            _recommendation("Daily rate uses days_in_month", "hard-codes price/30"),
            _recommendation("Rounding to two decimals", "drops the round() call"),
        ],
        completion=CompletionResult(
            verdict=CompletionVerdict.INCOMPLETE, rationale="2 gaps.",
        ),
    )

    instruction = render_next_instruction(review)

    # Each gap is named...
    assert "Daily rate is monthly_price divided by days_in_month" in instruction
    assert "Round the result to two decimals" in instruction
    # ...and each distinguishing test, with the defect it must catch.
    assert "Daily rate uses days_in_month" in instruction
    assert "Must fail if: hard-codes price/30" in instruction
    assert "Must fail if: drops the round() call" in instruction
    assert "assert prorate(280, 14, 28) == 140.0" in instruction
    # §10.1 closes by asking for the declaration to be refreshed.
    assert "Update the builder declaration after the changes." in instruction


def test_no_instruction_when_there_are_no_material_gaps():
    """§10.1 step 12 produces an instruction only WHEN GAPS EXIST.

    Carries leftover recommendations deliberately: with an empty review the
    "nothing actionable" guard would return None on its own and the verdict
    gate would never be exercised. Recommendations present + a positive
    verdict isolates the gate as the only thing that can suppress output.
    """
    review = Review(
        mode="local",
        reviewed_revision="abc",
        obligation_map=[_obligation("A", "addressed", "strongly_supported")],
        recommendations=[_recommendation("Some criterion", "some defect")],
        completion=CompletionResult(
            verdict=CompletionVerdict.NO_MATERIAL_GAPS, rationale="all good",
        ),
    )

    assert render_next_instruction(review) is None


def test_unresolved_open_questions_lead_the_instruction():
    """A needs-clarification review can't be closed by writing code, so the
    questions come first (#113)."""
    review = Review(
        mode="local",
        reviewed_revision="abc",
        open_questions=[
            OpenQuestion(id="q-1", question="Minus sign or parentheses?"),
            OpenQuestion(id="q-2", question="Already answered", resolved=True),
        ],
        completion=CompletionResult(
            verdict=CompletionVerdict.NEEDS_CLARIFICATION, rationale="1 open question.",
        ),
    )

    instruction = render_next_instruction(review)

    assert "Answer these first" in instruction
    assert "Minus sign or parentheses?" in instruction
    assert "Already answered" not in instruction  # resolved questions are not asked again


def test_no_instruction_when_a_non_positive_verdict_has_nothing_actionable():
    """unable-to-determine with no gaps, recommendations or open questions has
    nothing to instruct — better silence than an empty template."""
    review = Review(
        mode="local",
        reviewed_revision="abc",
        completion=CompletionResult(
            verdict=CompletionVerdict.UNABLE_TO_DETERMINE, rationale="nothing analyzed",
        ),
    )

    assert render_next_instruction(review) is None


def test_instruction_contains_only_review_content_and_invents_nothing():
    """Obligation 4's real test: the instruction is a PROJECTION, so it must
    contain exactly the review's own gaps and recommendations and nothing more.

    Compares the FULL SET of rendered items against the review's own content.
    An earlier version enumerated expected prefixes ("1. ", "2. ") and so
    missed an injected "0. " line -- a superset check that could not detect a
    superset. Set equality is what actually closes that."""
    review = Review(
        mode="local",
        reviewed_revision="abc",
        findings=[_gap_finding("Only gap A")],
        recommendations=[_recommendation("Only criterion A", "defect A")],
        completion=CompletionResult(
            verdict=CompletionVerdict.INCOMPLETE, rationale="1 gap.",
        ),
    )

    instruction = render_next_instruction(review)

    def numbered_items(section: str) -> set[str]:
        """Every `<n>. <text>` item in a section, regardless of its number."""
        return {
            re.sub(r"\*\*", "", m.group(1)).strip()
            for m in (re.match(r"^\d+\.\s+(.*)$", ln) for ln in section.splitlines())
            if m
        }

    implement = instruction.split("## Implement")[1].split("## ")[0]
    tests_section = instruction.split("## Add these tests")[1]

    # EXACTLY the review's own content -- nothing invented, nothing dropped.
    assert numbered_items(implement) == {"Only gap A"}
    assert numbered_items(tests_section) == {"Only criterion A"}


def test_instruction_omits_satisfied_obligations_and_advisory_items():
    """Obligation 6: the instruction SELECTS. A review deliberately mixing an
    actionable gap with a satisfied obligation, an advisory unrequested change
    and an evidence limitation must surface only the gap."""
    review = Review(
        mode="local",
        reviewed_revision="abc",
        obligation_map=[
            _obligation("A satisfied obligation", "addressed", "strongly_supported"),
        ],
        findings=[
            _gap_finding("A real remaining gap"),
            Finding(
                type=UNREQUESTED_CHANGE, severity="medium",
                description="An advisory unrequested change",
                evidence_tier=EvidenceTier.STATIC, produced_by=Component.STATIC_ANALYZER,
                links=[Link(kind="code", ref="x.py#@@ -1 +1 @@")],
                disposition=UnrequestedChangeDisposition.SEPARABLE,
            ),
        ],
        completion=CompletionResult(
            verdict=CompletionVerdict.INCOMPLETE, rationale="1 gap.",
            limitations=["An evidence limitation note"],
        ),
    )

    instruction = render_next_instruction(review)

    assert "A real remaining gap" in instruction
    assert "A satisfied obligation" not in instruction
    assert "An advisory unrequested change" not in instruction
    assert "An evidence limitation note" not in instruction
