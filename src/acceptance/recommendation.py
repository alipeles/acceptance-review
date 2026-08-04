"""On-demand retrieval of a §9.5 test recommendation (M7.3.r1, #167).

Replaces the pushed `.acceptance/next-instruction.md`. That file was written
speculatively by whichever run last found gaps, keyed to no task and no
revision, and never cleaned up — so a later clean run printed "(none)" while a
stale file on disk still asserted gaps, and only the report was telling the
truth. Moving from push to pull removes the whole class of defect: nothing is
written speculatively, so nothing can go stale, and there is no path that needs
keying to a task or a SHA.

Retrieval reads the M0 review-state store. It never re-runs analysis, so it
makes no model call and costs nothing — the recommendation it returns is the one
the review already reached, not a fresh judgment that might differ.

The §9.5 fields stay PROSE inside a machine-readable envelope: structure for the
agent, sentences inside it where the reasoning lives. Flattening
`plausible_defect` to a terse token is what makes a recommendation unactionable.
"""

from __future__ import annotations

from acceptance.review_state import Review, TestRecommendation
from acceptance.serialization import canonical_json

# §9.5's discrete prescriptions, plus the criterion they serve. Ordered as §9.5
# lists them — a reader works down from what to feed the test to what it must
# assert — though `canonical_json` sorts keys on the way out, so the ordering
# here is documentation rather than the wire format.
_FIELDS = (
    "obligation_id",
    "criterion",
    "required_inputs",
    "boundary_conditions",
    "expected_output",
    "required_assertions",
    "plausible_defect",
    "repo_conventions",
)


def lookup(review: Review, criterion: str) -> TestRecommendation | None:
    """The stored recommendation for `criterion`, or None if it has none.

    None is an ordinary answer, not a failure: an obligation that is strongly
    supported earns no recommendation, and asking about one is a reasonable
    thing for an agent to do.
    """
    for recommendation in review.recommendations:
        if recommendation.obligation_id == criterion:
            return recommendation
    return None


def render_json(recommendation: TestRecommendation | None) -> str:
    """Canonical JSON, so two retrievals over unchanged state are byte-identical.

    An absent recommendation renders as `{}` rather than `null`: a caller
    parsing the output gets the same *type* either way and can test emptiness
    without special-casing, which is the difference between "no recommendation"
    being data and being an error to handle.
    """
    if recommendation is None:
        return canonical_json({})
    payload = {field: getattr(recommendation, field) for field in _FIELDS}
    return canonical_json(payload)


def render_text(recommendation: TestRecommendation | None) -> str:
    """The same content for a human reading a terminal."""
    if recommendation is None:
        return "(no recommendation for this criterion)"
    lines = [f"Criterion: {recommendation.criterion}", ""]
    for field in _FIELDS:
        if field in ("obligation_id", "criterion"):
            continue
        value = getattr(recommendation, field)
        label = field.replace("_", " ")
        if isinstance(value, list):
            lines.append(f"{label}:")
            lines.extend(f"  - {item}" for item in value)
        else:
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


def render(recommendation: TestRecommendation | None, fmt: str) -> str:
    return render_text(recommendation) if fmt == "text" else render_json(recommendation)
