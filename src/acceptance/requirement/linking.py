"""Obligation de-duplication, as linking rather than deletion (#144).

Derivation accounts for each requirement on its own and performs no linking at
all (#204, DR-204): every obligation it produces is named by exactly one
requirement, and a requirement stated under both Constraints and Completion
expectations therefore yields two obligations saying nearly the same thing. That
is the correct output of that stage — the alternative, letting derivation link,
lost requirement content outright (#223) — and this is the pass that resolves it.

**The output is a link, not a deletion.** Recognising that two obligations state
one requirement makes one of them the survivor and points the other
requirement's disposition at it, so the merged obligation ends up named by every
requirement that stated it. Nothing is discarded: the survivor carries the union
of the source spans, so it still traces to every piece of task text that produced
it, and both requirements keep a disposition naming a real obligation.

**Bias toward under-merging, and it is load-bearing here.** Two obligations about
the same area of a change are not necessarily the same requirement. Leaving a
true duplicate unmerged costs a redundant obligation and some model spend;
merging two distinct requirements destroys one of them silently, which is the
failure this whole product exists to catch. DR-204 accepted the fuzzy judgement
back into this pass specifically because *this* pass's failure is noisy while
derivation's was lossy — that trade only holds while the bias does.

**Not partitioned, deliberately.** Every other multi-judgment stage batches its
requests (DR-164), and this one must not. The judgement is inherently pairwise
over the whole set, so a batch boundary decides which obligations *can* be
compared at all: a duplicate pair split across two batches is invisible to both
calls and silently under-merged. That failure looks exactly like the bias working
as intended, so it would never surface. If the obligation count later forces
partitioning, #211's link-precision measure needs to exist first, so the loss is
measured rather than assumed small.

The canonical obligation of a cluster is chosen **here, by derivation order**,
not taken from the model's answer. Two runs that agree on which obligations are
duplicates then agree on the survivor, so the merge is a pure function of the
model's judgement rather than of how it happened to order a response.
"""

from __future__ import annotations

from typing import Sequence

from acceptance.config import DEFAULT_LINK_PAIR_BATCH_SIZE
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.partition import partition
from acceptance.requirement.obligations import Decomposition
from acceptance.review_state import (
    Obligation,
    RequirementDisposition,
    RequirementMap,
)
from acceptance.supplied_ids import UnusableAnswer, UnusableAnswerLog, constrain, scan

_STAGE = "obligation linking"

_SYSTEM_PROMPT = """You are de-duplicating a set of obligations derived from the \
software requirements in one task file.

You are given PAIRS of obligations. For each pair, answer one question: do \
these two obligations state exactly the same requirement?

Most pairs will not, and "no" is the right answer for most of them. You are not \
choosing the best partner for anything and you are not searching for duplicates.

**One pair shape is never the same requirement, and it is decided before the \
criteria below.** If one obligation demands that a TEST assert something and \
the other demands the thing itself, answer `false`. Do not weigh the criteria \
for such a pair; they do not apply to it.

The criteria below would mislead you here, which is why this comes first: the \
same test that asserts X is also the evidence for X, so "the same test would \
demonstrate both" looks true. It is the wrong question. Code that already does \
X, with nobody having written the test, satisfies "X" and violates "a test \
asserts X" — they are separate pieces of work, and merging them silently drops \
the demand for the test.

**The test for sameness, and the only one that matters.** Two obligations state \
the exact same requirement if and only if BOTH hold:

1. They have identical truth conditions. They are true under exactly the same conditions \
and false under exactly the same conditions. If you can describe any delivered change \
that satisfies one and not the other, they are different requirements.
2. The exact same set of tests would demonstrate both. Not two tests in the same file, and not \
two assertions about the same function — the SAME test, asserting the same thing.

Apply that test explicitly before reporting any pair.

Note that sameness is transitive: if A and B are the same requirement, and B and C are the same requirement, \
then A and C are the same requirement. If you are unsure, do not link them.

Similar wording, a shared subject, or belonging to the same feature are not evidence of sameness; \
only the two conditions above are.

Cases that pass the test:
- The same demanded behavior stated in different words.
- A requirement and a clause giving the REASON for that requirement. The reason \
is not separately checkable, so no test can distinguish them.

Cases that FAIL the test, and are the common mistakes:
- A behavior and a requirement to TEST that behavior. "The export writes a header \
row" and "a test asserts the export writes a header row" are different \
requirements: code that already writes the header row, with nobody having written \
the test, satisfies the first and violates the second. Adding the behavior and \
adding its test are separate pieces of work and separate obligations.
- A behavior and the technology used to implement it. "The amount is written with \
two decimal places" and "the file is produced with the standard CSV library" can \
each hold while the other fails, and no single test shows both.
- A general requirement and a specific case of it. The specific case can pass \
while the general one fails.
- Two requirements about the same area of the change that demand different things.
- Obligations sharing vocabulary but not the demand.

**When you are unsure, do not link them.** Leaving two obligations separate costs \
a little redundancy. Linking two obligations that demand different things \
destroys one of the requirements, and nothing downstream can recover it. Prefer \
the redundancy.

Answer every pair you are given. Answering `false` for all of them is a valid \
and common outcome."""


class _PairVerdict(StrictResponseModel):
    """One answer about one pair.

    The unit is a pair the CODE chose, not a link the model found. That is what
    removes the choice: the model is never asked which of several obligations is
    the best partner, only whether these two state one requirement — so "no" is
    as available an answer as "yes".

    A link is a typed field and nothing else (#144). Stating it in prose is not a
    link: it cannot be validated against the supplied ids, cannot be counted by
    #211's link-precision measure, and cannot be told apart from the model
    narrating what it did. `reason` is an audit field and carries no relation.
    """

    pair_id: str
    # Declared BEFORE the verdict, deliberately. Structured output is generated
    # in field order, so a verdict field placed first is decided before any
    # analysis exists and the reason becomes a rationalisation of it. Measured,
    # not assumed: with the verdict first, two of five confirmations on this
    # repo's own task file carried a reason that argued the opposite —
    # "...which is the complementary condition and not the same requirement"
    # attached to `same_requirement: true`. Reasoning first makes the boolean a
    # conclusion rather than a commitment.
    reason: str
    same_requirement: bool


class _Verdicts(StrictResponseModel):
    verdicts: list[_PairVerdict]


def _pairs(ordered_ids: list[str]) -> list[tuple[str, str, str]]:
    """Every unordered pair, with a stable id, in derivation order.

    Quadratic and deliberately so. Every pair is asked, which is what makes the
    sweep complete — no duplicate can be invisible the way it would be if the
    obligations themselves were partitioned — and what makes an inconsistent
    answer detectable. Inferring a pair from two others would assume the model's
    judgments are consistent, and destroy the evidence that they are not.
    """
    # Ordered by the DISTANCE between the two obligations, not by the first of
    # them: (0,1),(1,2),(2,3)… then (0,2),(1,3)… and so on.
    #
    # The natural nesting — every pair of the first obligation, then every pair
    # of the second — puts all N-1 pairs of obligation 0 into the opening
    # batches. A call holding 25 pairs that all share one obligation is not 25
    # independent questions; it reads as "here is X, which of these is its
    # duplicate?", which is the selection task this sweep exists to remove,
    # reappearing one level down. Measured on this repo's task file: batch 0 of
    # that ordering produced 5 of the 7 confirmations in a contradicted
    # component, while the other batches said no to 12 of 14.
    #
    # By distance, each obligation appears about twice per diagonal, so no batch
    # is about any one obligation. Still every pair exactly once, and still a
    # pure function of derivation order.
    count = len(ordered_ids)
    ordered = [
        (left, left + distance) for distance in range(1, count) for left in range(count - distance)
    ]
    return [
        (f"pair-{index:04d}", ordered_ids[left], ordered_ids[right])
        for index, (left, right) in enumerate(ordered)
    ]


def _user_prompt(decomposition: Decomposition, batch: Sequence[tuple[str, str, str]]) -> str:
    """One batch of pairs, as typed identified fields.

    Never the task file's markdown. The parse has already computed this
    structure, and handing the model raw source to re-derive is the shape the
    project's interchange invariant exists to forbid.
    """
    owner: dict[str, str] = {}
    for disposition in decomposition.requirement_map.dispositions:
        for obligation_id in disposition.obligation_ids:
            owner.setdefault(obligation_id, disposition.requirement_id)
    by_id = {obligation.id: obligation for obligation in decomposition.obligations}

    def describe(obligation_id: str, label: str) -> list[str]:
        obligation = by_id[obligation_id]
        return [
            f"  {label}: [{obligation.id}] from requirement {owner.get(obligation.id, 'unknown')}",
            f"    description: {obligation.description}",
            f"    observable behavior: {obligation.observable_behavior}",
        ]

    lines = ["Answer for every pair below. Each is independent.", ""]
    for pair_id, left, right in batch:
        lines.append(f"[{pair_id}]")
        lines.extend(describe(left, "A"))
        lines.extend(describe(right, "B"))
        lines.append("")
    return "\n".join(lines).rstrip()


def _confirmed_clusters(
    ordered_ids: list[str],
    confirmed: set[frozenset[str]],
) -> tuple[dict[str, str], list[list[str]]]:
    """Survivor per obligation, plus the components rejected as inconsistent.

    Two steps, and the second is the conservative one.

    Connected components come first: `same_requirement` is transitive by
    definition, since the criterion is identical truth conditions, so a
    confirmed A-B and B-C put all three in one component.

    But transitivity of the RELATION does not make the model's ANSWERS
    consistent. Confirming A-B and B-C while denying A-C is not an intransitive
    relation, it is three answers that cannot all be right — and because every
    pair was asked, we can see it. A component merges only if it is a complete
    clique: every pair among its members confirmed. One that is not merges
    NOTHING, all its members stay separate, and it is returned for recording.

    Blunt on purpose. Resolving the contradiction ourselves would mean picking
    which answer to believe, and every failure this pass has had has been an
    over-merge — so it fails toward under-merging, which is the direction the
    issue's bias accepts, and it says so rather than deciding quietly.
    """
    index = {obligation_id: position for position, obligation_id in enumerate(ordered_ids)}
    parent = {obligation_id: obligation_id for obligation_id in ordered_ids}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for pair in confirmed:
        left, right = sorted(pair, key=lambda i: index[i])
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            survivor, absorbed = sorted((root_left, root_right), key=lambda i: index[i])
            parent[absorbed] = survivor

    components: dict[str, list[str]] = {}
    for obligation_id in ordered_ids:
        components.setdefault(find(obligation_id), []).append(obligation_id)

    survivor_of: dict[str, str] = {}
    inconsistent: list[list[str]] = []
    for members in components.values():
        complete = all(
            frozenset((left, right)) in confirmed
            for position, left in enumerate(members)
            for right in members[position + 1 :]
        )
        if not complete:
            inconsistent.append(members)
            for member in members:
                survivor_of[member] = member
            continue
        for member in members:
            survivor_of[member] = members[0]
    return survivor_of, inconsistent


def _merged_obligations(
    obligations: list[Obligation], survivor_of: dict[str, str]
) -> list[Obligation]:
    """The surviving obligations, each carrying the union of its cluster's spans."""
    absorbed_spans: dict[str, list] = {}
    for obligation in obligations:
        survivor = survivor_of[obligation.id]
        if survivor != obligation.id:
            absorbed_spans.setdefault(survivor, []).extend(obligation.source_spans)

    merged: list[Obligation] = []
    for obligation in obligations:
        if survivor_of[obligation.id] != obligation.id:
            continue
        extra = absorbed_spans.get(obligation.id, [])
        if not extra:
            merged.append(obligation)
            continue
        spans = list(obligation.source_spans)
        seen = {span.model_dump_json() for span in spans}
        for span in extra:
            key = span.model_dump_json()
            if key not in seen:
                seen.add(key)
                spans.append(span)
        merged.append(obligation.model_copy(update={"source_spans": spans}))
    return merged


def _relinked_map(requirement_map: RequirementMap, survivor_of: dict[str, str]) -> RequirementMap:
    """The same map, with every disposition pointing at surviving obligations.

    This is where the many-to-one link becomes real: two requirements that
    stated one requirement now name the same obligation id, which is itself the
    record that a merge happened (DR-202 decision 2). No disposition loses its
    last obligation, because a cluster always keeps one member.
    """
    dispositions: list[RequirementDisposition] = []
    for disposition in requirement_map.dispositions:
        relinked: list[str] = []
        for obligation_id in disposition.obligation_ids:
            survivor = survivor_of.get(obligation_id, obligation_id)
            if survivor not in relinked:
                relinked.append(survivor)
        dispositions.append(disposition.model_copy(update={"obligation_ids": relinked}))
    return requirement_map.model_copy(update={"dispositions": dispositions})


def link_duplicate_obligations(
    decomposition: Decomposition,
    client: ModelClient,
    unusable_answers: UnusableAnswerLog | None = None,
    pair_batch_size: int = DEFAULT_LINK_PAIR_BATCH_SIZE,
) -> Decomposition:
    """Link the obligations that state the same requirement.

    Sweeps every pair, in batches, and merges only cliques the model confirmed
    outright. Returns the input unchanged when there is nothing to compare —
    fewer than two obligations means no call is made at all.
    """
    obligations = decomposition.obligations
    if len(obligations) < 2:
        return decomposition

    ordered_ids = [obligation.id for obligation in obligations]
    confirmed: set[frozenset[str]] = set()

    for batch in partition(_pairs(ordered_ids), pair_batch_size, key=lambda pair: pair[0]):
        by_pair_id = {pair_id: (left, right) for pair_id, left, right in batch.items}
        allowed = {"pair_id": list(by_pair_id)}
        result = client.complete(
            [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _user_prompt(decomposition, batch.items)},
            ],
            constrain(_Verdicts, allowed),
            batch.request_partition(),
            parse_as=_Verdicts,
            stage=_STAGE,
        )
        if unusable_answers is not None:
            unusable_answers.record(scan(result, allowed, _STAGE))
        for verdict in result.verdicts:
            if verdict.same_requirement and verdict.pair_id in by_pair_id:
                confirmed.add(frozenset(by_pair_id[verdict.pair_id]))

    survivor_of, inconsistent = _confirmed_clusters(ordered_ids, confirmed)
    if unusable_answers is not None and inconsistent:
        unusable_answers.record(
            UnusableAnswer(
                stage=_STAGE,
                field="same_requirement",
                returned_id=", ".join(members),
                reason=(
                    "answers contradict each other: these obligations are linked "
                    "transitively but at least one pair among them was denied, so "
                    "none of them were merged"
                ),
            )
            for members in inconsistent
        )

    return decomposition.model_copy(
        update={
            "obligations": _merged_obligations(obligations, survivor_of),
            "requirement_map": _relinked_map(decomposition.requirement_map, survivor_of),
        }
    )
