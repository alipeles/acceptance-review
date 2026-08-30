"""Scoring the ways of failing a review recorded, against labelled ones (#315).

Separates two failures the ratings alone cannot tell apart: **the enumerator
missed the defect**, and **the judge missed the kill**. They have different
causes and different fixes, and a single "evidence quality" number hides which
one moved — which is #252's shape, where a self-enumerated denominator lets a
thinner enumeration earn a stronger rating.

So `enumeration_recall` and `kill_agreement` are computed by separate functions
over separate denominators, and neither can move the other:

- a labelled defect the review never recorded lowers recall, and contributes
  **nothing at all** to kill agreement — it is not in that figure's denominator,
  so a thin enumeration cannot flatter its kill predictions;
- a matched defect whose predicted killers are wrong lowers kill agreement and
  leaves recall untouched.

`type_agreement` is third and equally separate: a defect recorded with the right
description and the wrong classification is a *match* with a type disagreement,
never a miss. Folding the two together would report a taxonomy problem as an
enumeration problem.

## What this module does not do

It does not produce defects and it does not predict kills. Predicted kills
arrive as `PredictedKills`, a plain mapping supplied by the caller — #314 fills
it, this module only scores it. Where nothing supplies a prediction the figure
is **absent, not zero**, on the same discipline `GroundTruthObligation.
expected_type` already follows: silence is not agreement, and a metric computed
over no data is not a score of zero.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from acceptance.benchmark.case import DefectScore, GroundTruthDefect, GroundTruthObligation
from acceptance.benchmark.twin_splitting import ReportMapping
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.review_state import Defect, DefectType

__all__ = [
    "DefectScore",
    "PredictedKills",
    "align_defects",
    "enumeration_recall",
    "kill_agreement",
    "mapping_from_defects",
    "other_share",
    "recall_by_type",
    "score_defects",
    "type_agreement",
]

# Recorded defect id -> the pytest node ids predicted to fail if the delivered
# code contained that defect. The one interface #314 fills and this module
# reads; changing its shape is a decision, not a refactor.
PredictedKills = Mapping[str, set[str]]


_SYSTEM_PROMPT = """\
You align two lists of DEFECTS: LABELLED (human-authored) and RECORDED
(produced by a tool). Each defect is a concrete way a piece of code could fail
one requirement.

Match each recorded defect to the ONE labelled defect describing the SAME way of
failing — the same mistake in the same rule, even if worded differently. Not
every defect has a match; leave unmatched ones out. Each labelled defect and
each recorded defect may appear in at most one match.

Match on the mistake described, not on surface wording. Two defects that would
be introduced by different edits are NOT the same defect, even when they mention
the same function, value or field. A defect about a wrong value and a defect
about a missing case are different defects. Do not match a defect describing a
failure of one rule to a defect describing a failure of a different rule.

Return the matches as pairs of the given labels (e.g. labelled "l2",
recorded "r0")."""


class _LabelMatch(StrictResponseModel):
    labelled: str
    recorded: str


class _DefectAlignment(StrictResponseModel):
    matches: list[_LabelMatch]


def _render_prompt(labelled: dict[str, GroundTruthDefect], recorded: dict[str, Defect]) -> str:
    lines = ["## Labelled defects", ""]
    for label, defect in labelled.items():
        lines.append(f"[{label}] {defect.description}")
    lines.append("")
    lines.append("## Recorded defects")
    lines.append("")
    for label, defect in recorded.items():
        lines.append(f"[{label}] {defect.description}")
    return "\n".join(lines)


def align_defects(
    labelled: Sequence[GroundTruthDefect],
    recorded: Sequence[Defect],
    client: ModelClient,
    stage: str | None = None,
) -> dict[str, str]:
    """Return a `recorded defect id -> labelled defect id` map, a bijection over
    the matched subset.

    By id, not by description: two defects of one review can legitimately carry
    near-identical descriptions under different obligations, and a
    description-keyed map would silently collapse them.

    Matching is a model judgement for the reason `align_obligations` is one — a
    real enumerator words a defect differently from the human who labelled it,
    and an exact-string join scores a perfect enumeration at zero. This does not
    reuse `align_obligations`: that prompt is written for acceptance criteria
    and asks which two state the same *requirement*, which is a different
    question from which two describe the same *mistake*. `case.py` already
    records the same misapplication risk for open questions.

    **Known limitation.** Alignment is global, not per obligation: a recorded
    defect may match a labelled defect belonging to a different obligation. The
    prompt argues against it, but nothing enforces it, so enumeration recall is
    an upper bound on per-obligation recall. Enforcing it needs the ground-truth
    and reviewer obligations aligned first, which is a second model call and a
    second thing to be wrong; not worth it until a case is observed where the
    two figures differ.
    """
    if not labelled or not recorded:
        return {}

    labelled_labels = {f"l{i}": d for i, d in enumerate(labelled)}
    recorded_labels = {f"r{i}": d for i, d in enumerate(recorded)}

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _render_prompt(labelled_labels, recorded_labels)},
    ]
    result = client.complete(messages, _DefectAlignment, stage=stage)

    alignment: dict[str, str] = {}
    used_labelled: set[str] = set()
    used_recorded: set[str] = set()
    for match in result.matches:
        if (
            match.labelled in labelled_labels
            and match.recorded in recorded_labels
            and match.labelled not in used_labelled
            and match.recorded not in used_recorded
        ):
            alignment[recorded_labels[match.recorded].id] = labelled_labels[match.labelled].id
            used_labelled.add(match.labelled)
            used_recorded.add(match.recorded)
    return alignment


def enumeration_recall(
    labelled: Sequence[GroundTruthDefect],
    alignment: Mapping[str, str],
) -> float | None:
    """Share of labelled defects the review recorded. `None` when nothing is
    labelled — a case that takes no position scores no recall, rather than 0.0.

    Reads only the alignment's labelled side, so it cannot see a prediction and
    cannot be moved by one.
    """
    if not labelled:
        return None
    matched = set(alignment.values())
    return sum(1 for d in labelled if d.id in matched) / len(labelled)


def recall_by_type(
    labelled: Sequence[GroundTruthDefect],
    alignment: Mapping[str, str],
) -> dict[DefectType, float]:
    """Enumeration recall per labelled `DefectType`.

    Only types the labels actually use appear. A type with no labelled defect is
    absent from the mapping rather than present at 0.0, for the same reason
    `enumeration_recall` returns `None` on an empty set: an unmeasured type and
    a type the enumerator missed entirely must not read alike.
    """
    matched = set(alignment.values())
    totals: dict[DefectType, list[int]] = {}
    for defect in labelled:
        bucket = totals.setdefault(defect.type, [0, 0])
        bucket[1] += 1
        if defect.id in matched:
            bucket[0] += 1
    return {t: hits / total for t, (hits, total) in totals.items()}


def type_agreement(
    labelled: Sequence[GroundTruthDefect],
    recorded: Sequence[Defect],
    alignment: Mapping[str, str],
) -> float | None:
    """Share of *matched* pairs whose classifications agree. `None` when nothing
    matched.

    Over matched pairs only, which is the whole point: a recorded defect that
    describes the right mistake under the wrong type is a classification
    disagreement, not a defect the review failed to record. Scoring it as a miss
    would report a taxonomy problem as an enumeration problem and send the fix
    to the wrong stage.
    """
    labelled_by_id = {d.id: d for d in labelled}
    recorded_by_id = {d.id: d for d in recorded}
    pairs = [
        (recorded_by_id[r], labelled_by_id[label])
        for r, label in alignment.items()
        if r in recorded_by_id and label in labelled_by_id
    ]
    if not pairs:
        return None
    return sum(1 for rec, lab in pairs if rec.type == lab.type) / len(pairs)


def other_share(recorded: Sequence[Defect]) -> float | None:
    """Share of recorded defects carrying the taxonomy's escape value.

    A standing figure, per DR-312: a rising share is a taxonomy gap, and a
    near-zero share alongside poor enumeration recall is odd defects being
    forced into the nearest slot rather than a taxonomy that fits. Neither
    reading is available from recall alone, which is why this is reported even
    when it looks uninteresting.
    """
    if not recorded:
        return None
    return sum(1 for d in recorded if d.type is DefectType.OTHER) / len(recorded)


def _jaccard(predicted: set[str], expected: set[str]) -> float:
    """Agreement between two test sets, with empty-vs-empty scored as exact.

    Empty against empty is 1.0 deliberately. A labelled defect with no killing
    test is a real label and the most important one in the corpus — archetype #4
    is exactly a present, relevant test that kills nothing — so a prediction of
    "no test catches this" is a correct prediction and must score as one. The
    usual convention of undefined-on-empty would drop that case out of the
    figure entirely, which is the one case it most needs to cover.
    """
    if not predicted and not expected:
        return 1.0
    union = predicted | expected
    return len(predicted & expected) / len(union)


def kill_agreement(
    labelled: Sequence[GroundTruthDefect],
    alignment: Mapping[str, str],
    predicted: PredictedKills | None,
) -> float | None:
    """How well the predicted killing tests agree with the labelled ones, over
    matched defects that carry a prediction. `None` when nothing supplies one.

    The denominator is matched defects with a prediction, and that is what keeps
    this figure independent of `enumeration_recall`. A labelled defect the
    review never recorded is outside the denominator, so failing to enumerate
    cannot raise or lower kill agreement; and a wrong prediction cannot reach
    recall, which never reads this argument.

    `None` rather than 0.0 when `predicted` is absent or covers none of the
    matched defects: before #314 exists there is nothing to score, and a zero
    would read as a stage that predicts badly rather than one that has not run.
    """
    if not predicted:
        return None
    labelled_by_id = {d.id: d for d in labelled}
    scores = [
        _jaccard(set(predicted[recorded_id]), set(labelled_by_id[labelled_id].killed_by))
        for recorded_id, labelled_id in alignment.items()
        if recorded_id in predicted and labelled_id in labelled_by_id
    ]
    if not scores:
        return None
    return sum(scores) / len(scores)


def mapping_from_defects(
    source: str,
    obligations: Sequence[GroundTruthObligation],
    recorded: Sequence[Defect],
    predicted: PredictedKills | None,
) -> ReportMapping:
    """The tests each obligation reaches *by way of* its recorded defects, in the
    shape `twin_splitting.twin_pairs` already consumes.

    Builds the input rather than duplicating the measure: whether two
    obligations stating the same demand receive the same tests is the same
    question before and after the defect-first change, and it deserves the same
    code. What moves is only how an obligation reaches a test — directly under
    the current mapping stage, and through its defects here — so recomputing the
    existing split rate over this mapping is a regression check on the change,
    not a new metric to calibrate.

    An obligation whose defects have no prediction reaches no test, which
    `twin_pairs` already handles: a pair where neither side maps a test scores
    no opportunities and so cannot register a split.
    """
    reached: dict[int, list[str]] = {}
    texts: dict[int, str] = {}
    defects_by_obligation: dict[str, list[Defect]] = {}
    for defect in recorded:
        defects_by_obligation.setdefault(defect.obligation_id, []).append(defect)

    for index, obligation in enumerate(obligations):
        texts[index] = obligation.description
        tests: set[str] = set()
        for defect in defects_by_obligation.get(obligation.id, []):
            if predicted:
                tests |= set(predicted.get(defect.id, ()))
        reached[index] = sorted(tests)
    return ReportMapping(source=source, obligations=texts, mapped_tests=reached)


def score_defects(
    labelled: Sequence[GroundTruthDefect],
    recorded: Sequence[Defect],
    alignment: Mapping[str, str],
    predicted: PredictedKills | None = None,
) -> DefectScore:
    """Every figure for one case, from an alignment already computed.

    Takes the alignment rather than a client so scoring itself makes no model
    call: the one model judgement in this module is `align_defects`, which the
    caller runs once, and everything here is arithmetic over its result.
    """
    return DefectScore(
        enumeration_recall=enumeration_recall(labelled, alignment),
        recall_by_type=recall_by_type(labelled, alignment),
        type_agreement=type_agreement(labelled, recorded, alignment),
        other_share=other_share(recorded),
        kill_agreement=kill_agreement(labelled, alignment, predicted),
        labelled=len(labelled),
        recorded=len(recorded),
        matched=len(alignment),
        predicted=len(predicted or {}),
    )
