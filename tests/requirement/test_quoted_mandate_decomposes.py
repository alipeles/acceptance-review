"""A mandate containing a quotation mark must decompose.

At #340's Gate 1 it did not. `source_quote` is constrained to an enum of the
answering requirement's own spans, the double quote reached the generated JSON
Schema intact, and the provider's strict structured-output mode refused the whole
request:

    Invalid schema for response_format '_Decomposition': In
    context=(...,'source_quote'), " is not allowed in string literals for
    structured outputs (strict=true)

The review died on an unhandled `litellm.BadRequestError`, part-paid, with no
partial result and no diagnostic. Quotation marks are ordinary English and a
client mandate is prose, so the only way past it was to reword the client's own
requirements — which changes the decomposition.

The three assertions below are the three things that have to hold together. Any
one alone is satisfiable by a repair that breaks another: stripping the character
would satisfy the first and break the second, and folding the substitution into
`normalise` would satisfy both and break the third.
"""

from __future__ import annotations

from acceptance.requirement.obligations import _Decomposition, constrain
from acceptance.requirement.spans import locate_in_text, offerable, quotable_spans

_QUOTED = 'An obligation phrased "a test asserts that X" is derived into an obligation stating X.'


def _string_literals(node: object) -> list[str]:
    """Every `const` and `enum` value in a JSON Schema, at any depth.

    The refusal was about string LITERALS, not about the schema's own syntax,
    which is quotation marks all the way down — so the assertion has to reach the
    values rather than the serialised document.
    """
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "const" and isinstance(value, str):
                found.append(value)
            elif key == "enum" and isinstance(value, list):
                found.extend(v for v in value if isinstance(v, str))
            else:
                found.extend(_string_literals(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_string_literals(item))
    return found


class TestTheSchemaIsAcceptable:
    """No span a mandate offers may carry the refused character into the schema."""

    def test_no_offered_span_carries_a_double_quote(self):
        assert '"' in _QUOTED, "the fixture must contain the character under test"
        assert all('"' not in span for span in quotable_spans(_QUOTED))

    def test_the_constrained_schema_is_free_of_it(self):
        """The assertion on the artefact the provider actually refused.

        Checked on the serialised schema rather than on the span list, because
        the refusal was about the JSON Schema `const`, and a repair that cleaned
        the list while something downstream re-introduced the character would
        pass the test above and still abort a review.
        """
        model = constrain(
            _Decomposition,
            {"requirement_id": ["task-01"], "source_quote": quotable_spans(_QUOTED)},
        )
        literals = _string_literals(model.model_json_schema())

        assert any("asserts that X" in value for value in literals), (
            "the quoted span must reach the schema, or this asserts nothing"
        )
        assert all('"' not in value for value in literals)


class TestTheAnswerStillLocates:
    """A substituted span must still be found in the source, which is untouched.

    This is the half a naive repair loses. The substitution happens on the way
    out, so the model answers with the stand-in while the mandate still holds the
    original; a character-for-character match would then reject the answer for a
    substitution we made ourselves, and the obligation would lose its source span
    — silently, since a span that cannot be located is recorded and the
    obligation kept.
    """

    def test_a_substituted_quotation_locates_in_the_original(self):
        offered = offerable(_QUOTED)
        assert offered != _QUOTED, "the fixture must exercise the substitution"

        located = locate_in_text(_QUOTED, 0, offered)

        assert located is not None
        # The span carries the SOURCE text, not the offered stand-in, so the
        # typed-and-linked invariant still points at what the mandate says.
        assert located.text == _QUOTED
        assert _QUOTED[located.start : located.end] == _QUOTED

    def test_a_sentence_span_locates_inside_a_longer_requirement(self):
        body = "First sentence. " + _QUOTED + " Third sentence."
        offered = [s for s in quotable_spans(body) if "asserts" in s]
        assert offered, "the quoted sentence must be among the offered spans"

        located = locate_in_text(body, 0, offered[-1])

        assert located is not None
        assert '"a test asserts that X"' in located.text


class TestAQuotationFreeMandateIsUnchanged:
    """The repair must orphan no recorded transcript.

    The offered spans go into the hashed request, so if this substitution moved
    the spans of a mandate that has no quotation mark in it, every recorded
    decomposition would stop replaying and every benchmark figure spanning the
    stage would stop being comparable. It must be a no-op on text that does not
    contain the character.
    """

    def test_offerable_is_the_identity_on_unquoted_text(self):
        plain = "A pair the review drops has not been decided. It is recorded."
        assert offerable(plain) == plain

    def test_the_offered_spans_are_unchanged(self):
        plain = "A pair the review drops has not been decided. It is recorded."
        assert quotable_spans(plain) == [
            plain,
            "A pair the review drops has not been decided.",
            "It is recorded.",
        ]
