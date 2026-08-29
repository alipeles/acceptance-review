"""Enumerate the ways the changed code could plausibly fail each obligation.

The first stage of the defect-first shape (#312, #313), and the one place the
whole design's premise is enforced: **this stage is never shown a test.**

That is the mitigation for #252. A denominator chosen by something that can see
what is already covered drifts toward it — enumerate the defects the tests
already catch, and a thin enumeration earns a strong rating. So the change set
this stage renders is filtered to non-test files before it reaches the prompt,
in code, rather than by asking the model not to look.

One call per obligation. Batching would put the checklist for one obligation
type in front of an obligation of another, and #317 measured what happens when a
call is shown several units and asked about one: it answers for the others. A
per-obligation call also makes the carry unit and the request unit the same
thing, so a reworded obligation re-enumerates exactly itself.
"""

from __future__ import annotations

import hashlib

from acceptance.carry import carry_key, decide
from acceptance.coverage.prompt import diff_block, hunk_label, hunk_labels
from acceptance.defects.taxonomy import DESCRIPTIONS, checklist_for, enumerable
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.partition import partition
from acceptance.request_blocks import Block, BlockKind, assemble
from acceptance.review_state import (
    ChangeSet,
    Defect,
    DefectSet,
    DefectType,
    Obligation,
)
from acceptance.serialization import canonical_json
from acceptance.supplied_ids import UnusableAnswerLog, constrain, scan

__all__ = [
    "DEFECT_STAGE_LOGIC_VERSION",
    "ONE_OBLIGATION_PER_CALL",
    "enumerate_defects",
    "non_test_changes",
    "region_digests_for",
]

_STAGE = "defect enumeration"

# Bumped when the code that turns a response into a `DefectSet` changes in a way
# the request key cannot see — a different id scheme, a changed empty-set rule.
# The request key covers the prompt and the schema; this covers everything after
# the response comes back (`acceptance.carry`, check 3).
DEFECT_STAGE_LOGIC_VERSION = 1

# One obligation per call. Stated as a partition size rather than a bare loop so
# the size lands in the request key: a recording made under batching must not
# replay as though nothing had moved (#154).
ONE_OBLIGATION_PER_CALL = 1

_SYSTEM_PROMPT = """\
You are given ONE acceptance criterion and the changed production code of a
proposed implementation. Enumerate the concrete ways that code could plausibly
FAIL that criterion.

You are enumerating candidate defects, not judging whether any of them is
present. Each one is a specific, checkable claim about what could be wrong —
something a reader could go and look for in the code you were shown.

Walk the checklist you are given, in order, and ask of each entry: could the
delivered code fail this criterion in that way? Record one defect for each way
that is genuinely plausible given the code in front of you. The checklist is a
prompt for your attention, not a quota: skip an entry that does not apply.

Where a plausible way of failing fits no entry on the checklist, record it with
type `other` and say what it is in the description. Do not force a defect into
the nearest entry.

DESCRIPTIONS

Write each description as the failure, not as the requirement. "The rate is
computed from a 30-day month, so February is wrong" — not "the rate must be
computed correctly". A reader must be able to tell what to go and check.

Give each defect a short `slug`: lowercase words joined by hyphens, naming the
specific failure. It is a label, not a sentence.

CODE REFERENCES

`code_refs` are the labels (like `path#0`) of the changed regions the defect
would live in. Cite the regions a reader would have to inspect to tell whether
the defect is present. Leave it empty only when the defect is about code that is
ABSENT from the change — a case the criterion covers and the diff never touches.

AN EMPTY SET IS A REAL ANSWER

Some criteria have no plausible static defect. A criterion satisfied by
construction — one the delivered shape makes true, so that no code path could
violate it — earns no defect, and saying so is the correct answer.

When you return no defects, `reason` MUST say why the set is empty, specifically
enough that a reader can disagree with it. When you return defects, leave
`reason` empty.

Never invent a defect to avoid returning an empty set. A made-up defect is worse
than an empty one: it will be counted in a denominator, and the criterion will
look better tested than it is."""


class _Defect(StrictResponseModel):
    slug: str
    # `str`, not `DefectType`, so `constrain` can narrow it to this obligation's
    # own checklist. Declaring the enum here would offer every defect type to
    # every obligation and leave the checklist as advice in the prompt; narrowing
    # a string field to exactly the permitted values is what makes an off-
    # checklist type unrepresentable. Converted back to `DefectType` in
    # `_defects_from`, which is where an unconvertible value is reported.
    type: str
    description: str
    code_refs: list[str]


class _Enumeration(StrictResponseModel):
    obligation_id: str
    defects: list[_Defect]
    reason: str


def non_test_changes(change_set: ChangeSet) -> ChangeSet:
    """`change_set` with every test-category file removed.

    The enumerator's test-blindness, enforced where it cannot be talked out of:
    a filtered change set has nothing to leak. Asking the prompt to ignore the
    tests would leave the tests in the request, one instruction away from being
    read — and #252 is about a denominator that drifts, which is exactly the
    failure an instruction cannot rule out.

    `ignored_paths` is carried through unchanged. It records what the reviewed
    repo's own ignore rules excluded, which is a fact about the change set
    rather than about this stage's view of it.
    """
    return change_set.model_copy(
        update={"files": [file for file in change_set.files if file.category != "test"]}
    )


def region_digests_for(change_set: ChangeSet, labels: list[str]) -> dict[str, str]:
    """Content digest of each named `path#hunk` region of `change_set`.

    A label naming no region in this change set is omitted rather than recorded
    as absent, and that is the conservative direction: an omitted region makes
    the recomputed key differ from the stored one, so the set re-enumerates. The
    alternative — a sentinel for "gone" — would let a set whose implicated code
    was DELETED compare equal and carry forward over nothing.
    """
    by_label = {}
    for file_change in change_set.files:
        for index, hunk in enumerate(file_change.hunks):
            by_label[hunk_label(file_change.path, index)] = hunk.content
    return {
        label: hashlib.sha256(by_label[label].encode("utf-8")).hexdigest()
        for label in sorted(set(labels))
        if label in by_label
    }


def _key(
    client: ModelClient,
    obligation: Obligation,
    text: str,
    region_digests: dict[str, str],
) -> str:
    """What a stored defect set is valid under.

    The criterion's text and the CONTENTS of the regions its defects implicate —
    the mandate's rule stated exactly: a set is reused while both are unchanged.
    Not which files were touched: #293 deleted that comparison because it fires
    when a byte-identical region moves within a file.

    **The UNCONSTRAINED schema, deliberately.** The schema this stage actually
    sends carries two per-call enum sets — the criterion's own id, and every
    hunk label in the change set — and folding either into this key would break
    the rule above. The id would re-enumerate a criterion that was only renamed,
    which is exactly what carrying on text exists to avoid; the hunk labels
    would re-enumerate every criterion whenever any unrelated file gained a
    hunk. What the key needs from the schema is its SHAPE, which is what moves
    when the response model changes.

    The checklist is named instead, because it is what the per-call `type` enum
    would otherwise have contributed: a criterion whose checklist changed must
    re-enumerate, and nothing else in this key would notice.
    """
    return carry_key(
        system_prompt=_SYSTEM_PROMPT,
        response_schema=_Enumeration.model_json_schema(),
        model=client.model_for(_STAGE),
        temperature=client.temperature,
        seed=client.seed,
        stage_logic_version=DEFECT_STAGE_LOGIC_VERSION,
        inputs={
            "obligation_text": text,
            "checklist": [t.value for t in checklist_for(obligation.type)],
            "region_digests": region_digests,
        },
    )


def obligation_text(obligation: Obligation) -> str:
    """The identity a defect set is carried on.

    Both fields the enumerator is shown, and only those. Adding a field the
    prompt never renders would re-enumerate on a change that could not have
    altered the answer; leaving one out would carry a set across a change that
    could.
    """
    return canonical_json(
        {
            "description": obligation.description,
            "observable_behavior": obligation.observable_behavior,
        }
    )


def _subject(obligation: Obligation) -> str:
    """The one call's own content: the criterion, and its checklist."""
    lines = [
        "## Criterion",
        "",
        f"id={obligation.id} [{obligation.type.value}]",
        f"description: {obligation.description}",
        f"observable behaviour: {obligation.observable_behavior}",
        "",
        "## Checklist",
        "",
    ]
    for defect_type in checklist_for(obligation.type):
        lines.append(f"- {defect_type.value}: {DESCRIPTIONS[defect_type]}")
    lines.append("- other: a plausible way of failing that no entry above names")
    return "\n".join(lines)


def _defects_from(
    result: _Enumeration, obligation: Obligation, label_to_ref: dict[str, object]
) -> list[Defect]:
    """Turn one answer into identified `Defect` records.

    Ids are composed here rather than taken from the answer. The mandate wants
    an identifier unique within the review, and a model-chosen slug cannot carry
    that guarantee across obligations — two criteria about the same code invite
    the same slug. Prefixing with the obligation id makes uniqueness structural,
    and the numeric suffix settles a collision inside one answer.
    """
    defects: list[Defect] = []
    seen: set[str] = set()
    for entry in result.defects:
        base = f"{obligation.id}/{entry.slug}"
        defect_id = base
        suffix = 2
        while defect_id in seen:
            defect_id = f"{base}-{suffix}"
            suffix += 1
        seen.add(defect_id)
        defects.append(
            Defect(
                id=defect_id,
                obligation_id=obligation.id,
                type=_defect_type(entry.type),
                description=entry.description,
                code_refs=[ref for ref in entry.code_refs if ref in label_to_ref],
            )
        )
    return defects


def _defect_type(value: str) -> DefectType:
    """The returned type, or the escape when it is not one this vocabulary has.

    Unreachable through the schema, which offers only the checklist's own values
    plus `other`. Kept because the defect is still worth having if it happens:
    `scan` records the off-list value in the unusable-answer log, which surfaces
    as a finding, so the event is visible rather than silent — while dropping the
    defect entirely, or raising, would lose a real observation over a label.
    """
    try:
        return DefectType(value)
    except ValueError:
        return DefectType.OTHER


def enumerate_defects(
    obligations: list[Obligation],
    change_set: ChangeSet,
    client: ModelClient,
    unusable: UnusableAnswerLog | None = None,
    prior: list[DefectSet] | None = None,
) -> list[DefectSet]:
    """One `DefectSet` per enumerable obligation, in the order given.

    An obligation whose type is not enumerable gets **no entry at all** — not an
    empty one. `test_demand` and `human_review` are excluded by DR-313 decision
    2, and an empty set means "looked, found nothing plausible, here is why".
    Recording that about an obligation this stage never examined would be a
    false negative wearing a reason.

    With `prior`, a set whose obligation text and implicated region contents are
    both unchanged is reused and no call is issued for it.
    """
    visible = non_test_changes(change_set)
    label_to_ref = hunk_labels(visible)
    prior_by_text = {entry.obligation_text: entry for entry in (prior or [])}
    asking = [o for o in obligations if enumerable(o.type)]
    order = {o.id: index for index, o in enumerate(asking)}

    sets: list[DefectSet] = []
    for obligation in asking:
        text = obligation_text(obligation)
        candidate = prior_by_text.get(text)
        constrained = constrain(_Enumeration, _allowed(obligation, label_to_ref))
        # Against the regions the STORED set implicates, because the question is
        # whether that set is still valid. Computing it over this run's regions
        # would be circular: they are not known until the call this check exists
        # to avoid has already been made.
        current = _key(client, obligation, text, region_digests_for(visible, _labels(candidate)))
        decision = decide(
            obligation.id,
            prior=candidate,
            prior_key=candidate.carry_key if candidate else None,
            current_key=current,
        )
        if decision.carried:
            # Re-identified onto this run's obligation id, which may differ from
            # the one the set was recorded under: the carry matched on text.
            # Everything else is the stored answer, untouched.
            carried = candidate.model_copy(
                update={
                    "obligation_id": obligation.id,
                    "defects": [
                        defect.model_copy(update={"obligation_id": obligation.id})
                        for defect in candidate.defects
                    ],
                    "carried_from": candidate.carry_key,
                }
            )
            sets.append(carried)
            continue
        sets.append(
            _ask_about(obligation, visible, label_to_ref, constrained, client, unusable, text)
        )

    return sorted(sets, key=lambda entry: order[entry.obligation_id])


def _allowed(obligation: Obligation, label_to_ref: dict) -> dict[str, list[str]]:
    """What this call's answer may say, as the enum sets folded into its schema.

    `type` is the one that carries the guarantee. Restricted to this obligation
    type's own checklist plus the escape, a defect typed against a different
    obligation type's checklist is unrepresentable rather than filtered
    afterwards — the standard DR-163 set, and what #317 showed is worth more
    than a check applied to the answer.
    """
    return {
        "obligation_id": [obligation.id],
        "type": [t.value for t in checklist_for(obligation.type)] + [DefectType.OTHER.value],
        "code_refs": list(label_to_ref),
    }


def _labels(candidate: DefectSet | None) -> list[str]:
    """The regions a stored set implicates, which is what its key was built over.

    Read off the stored `region_digests` rather than off its defects' `code_refs`
    so that a stored set and the key recomputed against it always cover the same
    regions, even if the two ever disagree.
    """
    return list(candidate.region_digests) if candidate else []


def _ask_about(
    obligation: Obligation,
    visible: ChangeSet,
    label_to_ref: dict,
    constrained: type[_Enumeration],
    client: ModelClient,
    unusable: UnusableAnswerLog | None,
    text: str,
) -> DefectSet:
    """One call, about `obligation` alone, over the test-free change set.

    `constrained` is passed in rather than rebuilt: the carry check above needs
    the same schema to compute the same key, and two constructions of it are two
    things that can drift apart.
    """
    messages = assemble(
        [
            diff_block(visible),
            Block(BlockKind.INSTRUCTIONS, _SYSTEM_PROMPT),
            Block(BlockKind.SUBJECT, _subject(obligation)),
        ]
    )
    allowed = _allowed(obligation, label_to_ref)
    batch = partition([obligation], ONE_OBLIGATION_PER_CALL, key=lambda o: o.id)[0]
    result = client.complete(
        messages,
        constrained,
        batch.request_partition(),
        parse_as=_Enumeration,
        stage=_STAGE,
    )
    if unusable is not None:
        unusable.record(scan(result, allowed, _STAGE))

    defects = _defects_from(result, obligation, label_to_ref)
    # An answer with neither defects nor a reason is not an empty set, it is a
    # non-answer. Saying so keeps "no plausible static defect, and here is why"
    # distinguishable from a stage that returned nothing (#275's shape).
    reason = result.reason.strip()
    if not defects and not reason:
        reason = "The enumeration returned no defects and gave no reason for the empty set."
    implicated = [ref for defect in defects for ref in defect.code_refs]
    digests = region_digests_for(visible, implicated)
    return DefectSet(
        obligation_id=obligation.id,
        defects=defects,
        reason="" if defects else reason,
        obligation_text=text,
        carry_key=_key(client, obligation, text, digests),
        region_digests=digests,
    )
