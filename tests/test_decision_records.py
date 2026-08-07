"""Decision Records state what they resolved (#202).

A DR whose Open section still lists a question the change settled sends the next
session to re-derive a decision that was already made and recorded elsewhere —
which is the failure mode `docs/DR-180` §Open is currently in, and the reason
CLAUDE.md asks for a DR when a decision is resolved rather than after.

Asserting on prose is unusual and deliberately narrow: these check that a
specific settled question is stated as settled, not that the document reads well.
"""

from __future__ import annotations

import pathlib

DOCS = pathlib.Path(__file__).resolve().parents[1] / "docs"
DR_202 = DOCS / "DR-202-decomposition-requirement-mapping.md"
DR_216 = DOCS / "DR-216-parser-accounts-decomposer-splits.md"


def _flat(text: str) -> str:
    """Whitespace-normalised, so an assertion survives a reflow of the prose it
    is checking. Hard-wrapping a paragraph must not fail a test about content."""
    return " ".join(text.split())


def _open_section(text: str) -> str:
    """The document's `## Open` section, or "" when it has none."""
    marker = "\n## Open\n"
    if marker not in text:
        return ""
    return text.split(marker, 1)[1].split("\n## ", 1)[0]


def test_dr_202_records_the_requirement_id_decision_as_resolved():
    text = DR_202.read_text()

    flat = _flat(text)

    assert "## Resolved after acceptance" in text
    assert "Requirement id stability — settled as an interim scheme" in flat
    # The scheme itself, so a future edit cannot leave the heading and lose it.
    assert "`section + ordinal`" in flat


def test_dr_202_records_the_three_disposition_set_and_parse_time_completeness():
    """M1.2.r2 (#217). Decision 3 named three dispositions and the
    implementation shipped four, so the DR and the code disagreed while both
    read as settled. A reader arriving at decision 3 must meet the amendment
    there rather than infer it from the absence of `UNDISPOSED` in the code.
    """
    flat = _flat(DR_202.read_text())

    assert "Amended by M1.2.r2" in flat
    assert "UNDISPOSED" in flat and "has been removed" in flat
    # The mechanism, not just the fact: enforcement moved to parse time.
    assert "Completeness is now enforced at parse" in flat


def test_dr_202_no_longer_lists_requirement_id_stability_as_open():
    """The half that matters. Adding a Resolved section while leaving the
    question under Open records the decision and hides it at the same time."""
    assert "Requirement id stability" not in _flat(_open_section(DR_202.read_text()))


def test_dr_202_records_what_the_interim_scheme_defers():
    """An interim decision that does not say what it defers reads as a final
    one, and the deferral is the whole reason it was acceptable to take."""
    flat = _flat(DR_202.read_text())

    assert "#209" in flat
    assert "a requirement id is not comparable across two versions" in flat


def test_dr_216_records_the_nested_content_decision_as_resolved():
    """#216's Completion expectations require the choice between
    nested-as-requirement and nested-as-unread to be *recorded in the
    repository*, and #216's own body offers both as open.

    The record is the only place that choice survives — nothing in the parser
    distinguishes "this is the policy" from "this is how it happens to behave"
    — so an edit that drops it leaves the next session re-deriving a decision
    already made. That is the failure this module exists to catch.
    """
    text = DR_216.read_text()
    flat = _flat(text)

    # The choice itself, stated as chosen rather than surveyed.
    assert "Nested content under a claimed list item becomes its own requirement" in flat
    # Its scope: both shapes #216 reports, not only nested bullets.
    assert "nested bullets and second or subsequent paragraphs" in flat
    # The ground it rests on, so the decision can be revisited on its merits.
    assert "lossy versus noisy" in flat


def test_dr_216_states_the_decision_uniformly_rather_than_per_block_type():
    """The constraint is that the choice is made ONCE and applied uniformly.
    A record that settled nested bullets while leaving fences and tables to a
    separate rule would satisfy the letter and lose the property."""
    flat = _flat(DR_216.read_text())

    assert "The parser never judges block type" in flat
    assert "A nested fence, a nested table and a nested bullet are treated alike" in flat


def test_dr_216_records_that_the_real_corpora_cannot_falsify_the_guard():
    """DR-216 decision 5. Without this the coverage assertion is green on a
    corpus containing zero nested bullets — the same shape of hole #216
    exists to close, rebuilt inside its own fix."""
    flat = _flat(DR_216.read_text())

    assert "contain zero nested bullets" in flat
    assert "purpose-built fixtures" in flat
    assert "tests/fixtures/nested-blocks/" in flat
