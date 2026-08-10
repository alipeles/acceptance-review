"""M7.4 acceptance: the rendered §16 report shows obligation coverage, test
evidence with a per-line evidence tier, advisory unrequested changes, and the
computed verdict."""

from acceptance.review_state import (
    AdmissibleEvidence,
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
    # A command, not a file (M7.3.r1): the file was written speculatively by
    # whichever run last found gaps and outlived it.
    assert "acceptance recommendation --criterion" in report
    assert "next-instruction.md" not in report


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

    # The recommendation renders inside its obligation's block, on the test
    # evidence axis it explains — not in a separate numbered list (#218, §16).
    obligation_block = report.split("Obligations:")[1].split("Unrequested changes:")[0]
    assert "recommended test: Daily rate uses days_in_month" in obligation_block
    assert "detects: hard-codes /30" in obligation_block
    assert "full detail: acceptance recommendation --criterion a" in obligation_block

    # Asserted by COUNT, not by the absence of a header string. A standalone
    # block restates the criterion, so "appears exactly once" catches one under
    # any heading — or none — where `"Recommended tests:" not in report` only
    # catches the old spelling.
    assert report.count("Daily rate uses days_in_month") == 1
    assert report.count("detects: hard-codes /30") == 1


def test_a_recommendation_sits_under_its_own_obligation_and_no_other():
    """The join key is `obligation_id`, and using it for placement is the whole
    point: §16 organises by obligation so a criterion's axes sit together rather
    than in separate lists the reader must join by eye."""
    review = Review(
        mode="local",
        reviewed_revision="abc",
        obligation_map=[
            _obligation("Weak one", "addressed", "nominally_supported"),
            _obligation("Strong one", "addressed", "strongly_supported"),
        ],
        recommendations=[
            TestRecommendation(
                obligation_id="weak-one",
                criterion="Weak one",
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
    blocks = report.split("Obligations:")[1].split("Unrequested changes:")[0]
    weak_block, strong_block = blocks.split("  2. Strong one")

    assert "recommended test:" in weak_block
    assert "recommended test:" not in strong_block


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


# --- incremental re-run rendering (M7.5) ------------------------------------


def _rerun_obligation(**overrides):
    from acceptance.review_state import Obligation, ObligationType

    fields = {
        "id": "ties-to-even",
        "description": "Ties go to the even neighbour",
        "type": ObligationType.FUNCTIONAL,
        "importance": "critical",
        "explicit": True,
        "observable_behavior": "...",
        "coverage_status": "addressed",
        "evidence_class": "strongly_supported",
    }
    fields.update(overrides)
    return Obligation(**fields)


def test_a_carried_forward_obligation_says_so_and_names_the_revision():
    """A carried judgment is evidence about an older head. Rendering it exactly
    like a fresh one would present what this run did NOT check as if it had."""
    from acceptance.review_state import Review

    review = Review(
        mode="local",
        reviewed_revision="b" * 40,
        obligation_map=[_rerun_obligation(carried_forward_from="a" * 40)],
    )

    output = render_report(review)

    assert "carried forward from aaaaaaaa" in output
    assert "not re-derived for this head" in output


def test_a_fresh_obligation_carries_no_such_label():
    from acceptance.review_state import Review

    review = Review(
        mode="local", reviewed_revision="b" * 40, obligation_map=[_rerun_obligation()]
    )

    assert "carried forward" not in render_report(review)


def test_the_report_states_what_closed_since_the_prior_review():
    """§13.5 #9's payoff: the previous review told the agent what to fix, and
    this is the answer to whether it did."""
    from acceptance.review_state import ObligationChange, Review, ReviewDelta

    review = Review(
        mode="local",
        reviewed_revision="b" * 40,
        obligation_map=[_rerun_obligation()],
        delta=ReviewDelta(
            prior_reviewed_revision="a" * 40,
            previous_verdict="incomplete",
            verdict="no_material_gaps",
            obligation_changes=[
                ObligationChange(
                    obligation_id="ties-to-even",
                    description="Ties go to the even neighbour",
                    previous_coverage_status="addressed",
                    coverage_status="addressed",
                    previous_evidence_class="nominally_supported",
                    evidence_class="strongly_supported",
                )
            ],
        ),
    )

    output = render_report(review)

    assert "Changes since aaaaaaaa" in output
    assert "closed:" in output
    assert "nominally supported -> strongly supported" in output
    assert "INCOMPLETE -> NO-MATERIAL-GAPS" in output


def test_a_first_review_renders_no_changes_section():
    """Nothing to compare against, so the section would be noise."""
    from acceptance.review_state import Review

    review = Review(
        mode="local", reviewed_revision="b" * 40, obligation_map=[_rerun_obligation()]
    )

    assert "Changes since" not in render_report(review)


def test_a_review_with_gaps_closes_by_pointing_at_the_retrieval_command():
    """The positive branch of `_has_gaps`, which nothing covered.

    Only `"Recommended next instruction: (none)"` was asserted anywhere — the
    no-gaps branch. The line this exists to produce appeared in no test at all,
    just in committed fixture logs that assert nothing. Found by the tool's own
    Gate 2 on #218, and dismissed as tautological before being checked.

    It matters because the line is the only thing telling an agent the full
    prescription is retrievable; M7.3.r1 replaced a written file with it
    precisely so a stale artifact could not contradict the report.
    """
    review = Review(
        mode="local",
        reviewed_revision="abc",
        obligation_map=[_obligation("A", "addressed", "nominally_supported")],
        completion=CompletionResult(
            verdict=CompletionVerdict.INCOMPLETE,
            rationale="1 obligation(s) with non-discriminating test evidence.",
        ),
    )

    report = render_report(review)

    assert report.endswith(
        "Next: retrieve a criterion's full recommendation with\n"
        "  acceptance recommendation --criterion <id>"
    )
    assert "Recommended next instruction: (none)" not in report


def test_a_review_with_no_obligations_does_not_advertise_retrieval():
    """The second condition of `_has_gaps`, and the reason it is not simply
    "the verdict is not positive". A review with no obligations is
    `unable_to_determine` because there was nothing to assess — pointing it at
    the retrieval command would advertise detail that does not exist."""
    review = Review(
        mode="local",
        reviewed_revision="abc",
        completion=CompletionResult(
            verdict=CompletionVerdict.UNABLE_TO_DETERMINE,
            rationale="No obligations were derived.",
        ),
    )

    assert render_report(review).endswith("Recommended next instruction: (none)")


# --- #153: a respected boundary must not read as a missing test ---------------


def test_a_boundary_obligation_renders_as_not_applicable_not_as_a_missing_test():
    """#153's acceptance: a reader can tell "this boundary was respected" from
    "this requirement lacks tests".

    The negative assertion is the load-bearing one. Rendering "(no mapped test)"
    under a boundary obligation is textually identical to an ordinary
    requirement whose tests are missing, so a reader scanning the report cannot
    distinguish a satisfied exclusion from a genuine evidence gap — which is
    exactly what #146 observed when the exclusion came back
    "test evidence: partially supported".
    """
    boundary = Obligation(
        id="pagination",
        description="The change does not alter how the invoice list is paginated",
        type=ObligationType.INVARIANT,
        importance="critical",
        explicit=True,
        observable_behavior="...",
        coverage_status="addressed",
        evidence_class=None,
        admissible_evidence=AdmissibleEvidence.CODE_ONLY,
    )
    ordinary = _obligation("Active filters applied", "not_addressed", "unsupported")

    report = render_report(
        Review(mode="local", reviewed_revision="abc", obligation_map=[boundary, ordinary])
    )

    lines = report.splitlines()
    boundary_line = next(
        line for line in lines if "test evidence" in line and "not applicable" in line
    )
    assert "confirmed by code evidence alone" in boundary_line

    # The ordinary obligation still reports its missing tests, so the
    # distinction is between the two renderings rather than a blanket change.
    assert any("(no mapped test)" in line for line in lines)
    boundary_index = lines.index(boundary_line)
    assert "(no mapped test)" not in lines[boundary_index + 1]
