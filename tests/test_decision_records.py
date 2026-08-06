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
