"""Discrimination judgment (M5.2, §9.3 central question).

The core of test-semantic analysis: *would the mapped tests actually FAIL if the
implementation violated this criterion in a plausible way?* A test only
evidences a criterion if a realistic defect would make it fail — not because it
invokes the code, is named for it, or lives in a green suite (§9.3).

Per criterion, the model names one or more PLAUSIBLE defects (realistic mistakes
a competent-but-fallible developer might ship that violate that criterion), and
judges whether the mapped tests would catch each — reasoning over the three
§9.3 dimensions: do the test INPUTS distinguish the correct behavior from the
defect (or coincidentally give the same result?), are boundaries/negatives
exercised, do the ASSERTIONS target the required result. A criterion is
DISCRIMINATING iff its tests catch at least one plausible defect — §9.3's bright
line separating real evidence from nominal.

This is a semantic judgment (a static PREDICTION of which mapped mutants a test
would kill, §8.2), so it is a schema-constrained model call through the M0.4
harness — recorded for replay, never a live call in tests. M5.3 maps these
raw caught/survived verdicts onto the §9.3 strength classes; M8 later confirms
the predictions by execution.
"""

from __future__ import annotations

from collections.abc import Mapping

from acceptance.evidence.anchoring import RatingAnchor
from acceptance.evidence.classification import evidence_class_for
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.model_base import PersistableModel
from acceptance.review_state import ChangeSet, Obligation, TestEvidence
from acceptance.supplied_ids import UnusableAnswer, UnusableAnswerLog, constrain, scan

_STAGE = "discrimination judgment"

_SYSTEM_PROMPT = """\
You judge whether a criterion's mapped tests would actually FAIL if the
implementation violated that criterion in a PLAUSIBLE way. A test evidences a
criterion only if a realistic defect would make it fail — not merely because it
invokes the code or is named for it.

For each criterion (obligation):
1. Name one or more PLAUSIBLE defects: realistic mistakes a competent but
   fallible developer might actually ship that violate THIS criterion
   specifically — not arbitrary or absurd mutations.
2. For each defect decide whether the mapped test(s) would FAIL under it
   (catch it). Reason about: do the test INPUTS distinguish the correct
   behavior from the defect, or do they coincidentally produce the same result?
   Are boundary / negative cases exercised? Do the ASSERTIONS target the
   required result (e.g. does asserting a whole-number result exercise
   rounding)?
3. Give a short `reason`.

Set `would_be_caught` true only if some mapped test would genuinely fail under
the defect. A defect that produces the same output as the correct code for the
tested inputs is NOT caught (the input fails to discriminate).

Return, for each obligation id given, its list of defects with verdicts. Use
only the obligation ids provided."""

# Appended to the system prompt ONLY when some criterion carries a stored rating.
# Kept out of the base prompt for the same reason `_AnchoredDiscrimination` is a
# separate model: an unanchored request must stay byte-identical to what earlier
# runs recorded.
_ANCHOR_INSTRUCTIONS = """

Some criteria below carry a rating from an earlier review, listed with the
changes to that criterion's inputs since that rating was made. For those:

1. Judge the evidence on its merits, exactly as you would for any other
   criterion. Do not work backwards from the earlier rating.
2. If your defect verdicts imply a rating DIFFERENT from the recorded one,
   `rests_on` must name the id of the change that accounts for the difference.
3. If they imply the SAME rating, leave `rests_on` empty.

A rating moves when something about the criterion moved. Wording the judgement
differently from last time is not a reason for it to move, and a change listed
under a different criterion is not a reason either."""


class PlausibleDefect(PersistableModel):
    """A realistic violation of a criterion, and whether its tests catch it."""

    description: str
    would_be_caught: bool
    reason: str


class ObligationDiscrimination(PersistableModel):
    obligation_id: str
    defects: list[PlausibleDefect]
    # §9.3 bright line: do the mapped tests catch at least one plausible defect?
    discriminating: bool


class _Defect(StrictResponseModel):
    description: str
    would_be_caught: bool
    reason: str


class _ObligationDiscrimination(StrictResponseModel):
    obligation_id: str
    defects: list[_Defect]


class _Discrimination(StrictResponseModel):
    obligations: list[_ObligationDiscrimination]


class _AnchoredObligationDiscrimination(_ObligationDiscrimination):
    # The change ids this judgement rests on, empty unless it moves the rating.
    # `list[str]` rather than an optional single id so `constrain` can restrict
    # it: that helper handles `str` and `list[str]`, and `str | None` is neither.
    rests_on: list[str]


class _AnchoredDiscrimination(StrictResponseModel):
    """The anchored response shape, kept as a separate model on purpose.

    Adding `rests_on` to `_Discrimination` itself would change the schema of
    *every* discrimination request, and the schema name is hashed into the
    transcript key — so every existing recording would orphan and a first review,
    which has no stored rating to show anyone, would pay for a feature it does
    not use. A distinct model means only the anchored calls get a new key.
    """

    obligations: list[_AnchoredObligationDiscrimination]


def _evidence_by_obligation(
    obligations: list[Obligation], test_evidence: list[TestEvidence]
) -> dict[str, list[TestEvidence]]:
    by_obligation: dict[str, list[TestEvidence]] = {o.id: [] for o in obligations}
    for evidence in test_evidence:
        for obligation_id in evidence.mapped_obligations:
            if obligation_id in by_obligation:
                by_obligation[obligation_id].append(evidence)
    return by_obligation


def _render_prompt(
    obligations: list[Obligation],
    evidence_by_obligation: dict[str, list[TestEvidence]],
    change_set: ChangeSet,
    anchors: Mapping[str, RatingAnchor],
) -> str:
    by_id = {o.id: o for o in obligations}
    lines = ["## Criteria and their mapped tests", ""]
    for obligation_id, evidences in evidence_by_obligation.items():
        obligation = by_id[obligation_id]
        lines.append(f"### criterion id={obligation.id}: {obligation.description}")
        if obligation.observable_behavior:
            lines.append(f"observable behavior: {obligation.observable_behavior}")
        anchor = anchors.get(obligation_id)
        if anchor is not None:
            lines.append(f"rating recorded by the earlier review: {anchor.stored_class}")
            lines.append("changes to this criterion's inputs since that rating:")
            for change in anchor.changes:
                lines.append(f"- id={change.id} — {change.description}")
        lines.append("mapped tests:")
        for evidence in evidences:
            lines.append(f"- {evidence.identifier}")
            if evidence.inputs:
                lines.append(f"    inputs: {'; '.join(evidence.inputs)}")
            if evidence.assertions:
                lines.append(f"    assertions: {'; '.join(evidence.assertions)}")
            if evidence.expected_value_provenance:
                lines.append(f"    expected-value provenance: {evidence.expected_value_provenance}")
        lines.append("")

    lines.append("## Changed production code")
    for file_change in change_set.files:
        if file_change.category != "source":
            continue
        lines.append(f"### {file_change.path}")
        for hunk in file_change.hunks:
            lines.append(hunk.content)
    return "\n".join(lines)


def _rejection(anchor: RatingAnchor, fresh_class: str, named: list[str]) -> UnusableAnswer:
    """The report of a rating move that named no change it was given (#292)."""
    if named:
        problem = (
            f"named {', '.join(named)}, which "
            f"{'is a change' if len(named) == 1 else 'are changes'} "
            "to a different criterion"
        )
    else:
        problem = "named no change at all"
    return UnusableAnswer(
        stage=_STAGE,
        field="rests_on",
        returned_id=anchor.obligation_id,
        reason=(
            f"this judgement moves the rating from {anchor.stored_class} to {fresh_class} "
            f"but {problem}. The changes it was given were: "
            f"{', '.join(change.id for change in anchor.changes)}. "
            f"The recorded rating {anchor.stored_class} stands."
        ),
    )


def judge_discrimination(
    obligations: list[Obligation],
    test_evidence: list[TestEvidence],
    change_set: ChangeSet,
    client: ModelClient,
    unusable: UnusableAnswerLog | None = None,
    anchors: Mapping[str, RatingAnchor] | None = None,
) -> list[ObligationDiscrimination]:
    """Judge, per criterion with mapped tests, whether those tests would fail
    under a plausible defect (§9.3). Criteria with no mapped test are not
    judged here — they are unsupported, classified by M5.3.

    `anchors` carries, per criterion, the rating an earlier review recorded and
    the changes to that criterion's dependencies since (#292). A judgement about
    an anchored criterion that moves the rating without resting on one of those
    changes is **rejected here, as the response is read** — not discouraged in
    the prompt, which is advice a model is free to decline. The rejection holds
    the stored rating and is reported through `unusable`.
    """
    anchors = anchors or {}
    if anchors and unusable is None:
        raise ValueError(
            "anchored discrimination needs an UnusableAnswerLog: a rejected "
            "judgement that cannot be reported is a suppressed one"
        )
    evidence_by_obligation = {
        oid: evidences
        for oid, evidences in _evidence_by_obligation(obligations, test_evidence).items()
        if evidences
    }
    if not evidence_by_obligation:
        return []

    # Only criteria actually being asked about can be anchored; an anchor for a
    # criterion outside this call would put change ids into the enum that no
    # section of the prompt explains.
    anchors = {oid: anchors[oid] for oid in evidence_by_obligation if oid in anchors}

    system_prompt = _SYSTEM_PROMPT + _ANCHOR_INSTRUCTIONS if anchors else _SYSTEM_PROMPT
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": _render_prompt(obligations, evidence_by_obligation, change_set, anchors),
        },
    ]
    allowed = {"obligation_id": list(evidence_by_obligation)}
    response_model: type[_Discrimination] = _Discrimination
    if anchors:
        # Sorted so two runs over the same input build the same enum, and so the
        # request key does not move with dict iteration order.
        allowed["rests_on"] = sorted(
            {change.id for anchor in anchors.values() for change in anchor.changes}
        )
        response_model = _AnchoredDiscrimination
    result = client.complete(
        messages, constrain(response_model, allowed), parse_as=response_model, stage=_STAGE
    )
    if unusable is not None and unusable.record(scan(result, allowed, _STAGE)):
        # An obligation we asked about but got no usable judgment for is not
        # "no defect survives" — it is a judgment we never obtained. Saying
        # otherwise would let a re-run claim discrimination it never assessed.
        unusable.mark_indeterminate(
            obligation_id
            for obligation_id in evidence_by_obligation
            if obligation_id not in {item.obligation_id for item in result.obligations}
        )

    returned = {
        item.obligation_id: item
        for item in result.obligations
        if item.obligation_id in evidence_by_obligation
    }

    discriminations: list[ObligationDiscrimination] = []
    for obligation_id in evidence_by_obligation:
        item = returned.get(obligation_id)
        raw_defects = item.defects if item is not None else []
        defects = [
            PlausibleDefect(
                description=d.description, would_be_caught=d.would_be_caught, reason=d.reason
            )
            for d in raw_defects
        ]

        anchor = anchors.get(obligation_id)
        if anchor is not None and item is not None:
            # The judge returns defects, not a rating; the rating is the M5.3
            # reduce over them. So whether this judgement "alters the rating" is
            # only knowable after that reduce, which is why it is applied here
            # for the one criterion rather than left to the classifier.
            fresh_class = evidence_class_for(True, [d.would_be_caught for d in defects])
            if fresh_class != anchor.stored_class:
                named = list(getattr(item, "rests_on", []))
                justified = [change_id for change_id in named if change_id in anchor.change_ids]
                if not justified:
                    assert unusable is not None  # guaranteed by the check above
                    unusable.record([_rejection(anchor, fresh_class, named)])
                    unusable.hold_rating(obligation_id, anchor.stored_class)

        discriminations.append(
            ObligationDiscrimination(
                obligation_id=obligation_id,
                defects=defects,
                discriminating=any(d.would_be_caught for d in defects),
            )
        )
    return discriminations
