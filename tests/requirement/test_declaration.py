"""M6.1 acceptance: the §7.4 nine-section builder declaration is parsed when
present (full or partial); its absence is recorded as a minor finding rather
than blocking or degrading the rest of the review.

Parsing is pure markdown structure (no model call, no comparison judgment —
that's M6.2, #31), so these tests assert real parsed output directly."""

from acceptance.evidence_tier import Component, EvidenceTier
from acceptance.requirement.declaration import declaration_absent_finding, parse_declaration
from acceptance.review_state import DECLARATION_ABSENT, BuilderDeclaration

_FULL = """\
# Builder Declaration
## Mandate as understood
Add a discount function to the cart.

## Implementation summary
Added `apply_discount(total, percent)`.

## Scope exclusions
Did not touch checkout.

## Assumptions
Percent is given as a whole number, e.g. 10 for 10%.

## Changed components
- cart.py

## Test evidence
test_apply_discount asserts the discounted total.

## Regression evidence
test_checkout_default_unchanged still passes.

## Known limitations
Does not validate percent is within 0-100.

## Additional behavioral changes
none
"""


def test_full_nine_section_declaration_is_parsed():
    declaration = parse_declaration(_FULL)

    assert declaration.mandate_as_understood == "Add a discount function to the cart."
    assert declaration.implementation_summary == "Added `apply_discount(total, percent)`."
    assert declaration.scope_exclusions == "Did not touch checkout."
    assert declaration.assumptions == "Percent is given as a whole number, e.g. 10 for 10%."
    assert declaration.changed_components == "- cart.py"
    assert declaration.test_evidence == "test_apply_discount asserts the discounted total."
    assert declaration.regression_evidence == "test_checkout_default_unchanged still passes."
    assert declaration.known_limitations == "Does not validate percent is within 0-100."
    assert declaration.additional_behavioral_changes == "none"


def test_partial_declaration_leaves_omitted_sections_empty():
    # Matches archetype #7's real fixture shape: only 4 of the 9 sections
    # are present. A partial declaration is a valid declaration, not an error.
    text = """\
# Builder declaration

## Mandate as understood
Provide a lookup that returns a user record by its id.

## Implementation summary
Added `get_user(users, user_id)`, which returns the matching user record.

## Test evidence
Covered the happy path: an existing id returns the expected record.

## Known limitations
Raises `KeyError` with a clear message when the id is not present.
"""
    declaration = parse_declaration(text)

    assert declaration.mandate_as_understood == "Provide a lookup that returns a user record by its id."
    assert declaration.implementation_summary.startswith("Added `get_user")
    assert declaration.test_evidence.startswith("Covered the happy path")
    assert declaration.known_limitations.startswith("Raises `KeyError`")
    # Omitted sections are "", not missing/rejected.
    assert declaration.scope_exclusions == ""
    assert declaration.assumptions == ""
    assert declaration.changed_components == ""
    assert declaration.regression_evidence == ""
    assert declaration.additional_behavioral_changes == ""


def test_empty_text_parses_to_an_all_empty_declaration():
    declaration = parse_declaration("")
    assert declaration.mandate_as_understood == ""
    assert declaration.additional_behavioral_changes == ""


def test_multi_paragraph_section_is_joined():
    text = """\
## Mandate as understood
First paragraph.

Second paragraph.
"""
    declaration = parse_declaration(text)
    assert declaration.mandate_as_understood == "First paragraph.\n\nSecond paragraph."


def test_bullet_list_section_is_rendered():
    text = """\
## Changed components
- cart.py
- checkout.py
"""
    declaration = parse_declaration(text)
    assert declaration.changed_components == "- cart.py\n- checkout.py"


def test_declaration_round_trips_through_persistence():
    declaration = parse_declaration(_FULL)
    assert BuilderDeclaration.from_dict(declaration.to_dict()) == declaration


def test_declaration_absent_finding_shape():
    finding = declaration_absent_finding()

    assert finding.type == DECLARATION_ABSENT
    assert finding.severity == "low"
    assert finding.evidence_tier == EvidenceTier.STATIC
    assert finding.produced_by == Component.STATIC_ANALYZER
    assert finding.related_obligation is None  # obligation-less by construction
    assert finding.links
    assert finding.links[0].kind == "declaration"
