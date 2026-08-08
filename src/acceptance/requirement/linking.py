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

from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.requirement.obligations import Decomposition
from acceptance.review_state import (
    Obligation,
    RequirementDisposition,
    RequirementMap,
)
from acceptance.supplied_ids import UnusableAnswerLog, constrain, scan

_STAGE = "obligation linking"


_SYSTEM_PROMPT = """You are de-duplicating the obligations derived from one task \
file.

Each obligation below was derived from exactly one requirement. Because a mandate \
and its acceptance criteria naturally restate each other, and because a \
requirement is often followed by a clause giving the reason for it, the same \
requirement is frequently stated more than once — and each statement produced its \
own obligation.

Your job is to find the obligations that state the SAME requirement, and link \
them. Report each duplicate as a pair: the obligation that survives, and the \
obligation that states the same requirement as it.

**The test for sameness, and the only one that matters.** Two obligations state \
the same requirement if and only if BOTH hold:

1. They are true under exactly the same conditions and false under exactly the \
same conditions. If you can describe any delivered change that satisfies one and \
violates the other, they are different requirements.
2. The same test would demonstrate both. Not two tests in the same file, and not \
two assertions about the same function — the SAME test, asserting the same thing.

Apply that test explicitly before reporting any pair. Similar wording, a shared \
subject, and belonging to the same feature are not evidence of sameness; the two \
conditions above are.

Cases that pass the test:
- The same demanded behavior stated in different words.
- A requirement and a clause giving the REASON for that requirement. The reason \
is not separately checkable, so no test can distinguish them.
- A constraint and the acceptance criterion that restates it as something a test \
must assert.

Cases that FAIL the test, and are the common mistakes:
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

Report only the pairs you are confident about. Reporting no pairs at all is a \
valid answer."""


class _LinkedPair(StrictResponseModel):
    """One duplicate, as a pair of ids.

    A link is a typed field and nothing else (#144). Stating it in prose — in a
    description, a rationale, or any other free-text field — is not a link: it
    cannot be validated against the supplied ids, cannot be counted by #211's
    link-precision measure, and cannot be told apart from the model narrating
    what it did. `reason` exists for the audit trail and carries no link; the
    relation is entirely in the two id fields.
    """

    canonical_obligation_id: str
    duplicate_obligation_id: str
    reason: str


class _Links(StrictResponseModel):
    links: list[_LinkedPair]


def _user_prompt(decomposition: Decomposition) -> str:
    """The derived obligations as typed, identified fields.

    Never the task file's markdown. The parse has already computed this
    structure, and handing the model raw source to re-derive is the shape the
    project's interchange invariant exists to forbid.
    """
    owner: dict[str, str] = {}
    for disposition in decomposition.requirement_map.dispositions:
        for obligation_id in disposition.obligation_ids:
            owner.setdefault(obligation_id, disposition.requirement_id)

    lines = ["The obligations derived from this task, one block each.", ""]
    for obligation in decomposition.obligations:
        lines.append(f"[{obligation.id}]")
        lines.append(f"  derived from requirement: {owner.get(obligation.id, 'unknown')}")
        lines.append(f"  description: {obligation.description}")
        lines.append(f"  observable behavior: {obligation.observable_behavior}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _clusters(ordered_ids: list[str], pairs: list[_LinkedPair]) -> dict[str, str]:
    """Map every merged-away obligation id to the id that survives it.

    Union-find over the reported pairs, so a chain (A~B reported, B~C reported)
    resolves to one cluster rather than depending on which pair is read first.
    The survivor is the cluster member earliest in derivation order — chosen
    here rather than read from `canonical_obligation_id`, so the result does not
    move when the model nominates a different member of the same cluster.
    """
    index = {obligation_id: position for position, obligation_id in enumerate(ordered_ids)}
    parent = {obligation_id: obligation_id for obligation_id in ordered_ids}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for pair in pairs:
        left, right = pair.canonical_obligation_id, pair.duplicate_obligation_id
        # An id the call was never given is recorded through `scan` and ignored
        # here; a self-link asserts nothing and is dropped the same way.
        if left not in index or right not in index or left == right:
            continue
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            survivor, absorbed = sorted((root_left, root_right), key=lambda i: index[i])
            parent[absorbed] = survivor

    return {
        obligation_id: min(
            (member for member in ordered_ids if find(member) == find(obligation_id)),
            key=lambda i: index[i],
        )
        for obligation_id in ordered_ids
    }


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
) -> Decomposition:
    """Link the obligations that state the same requirement.

    Returns a `Decomposition` whose obligations are the survivors and whose
    requirement map points every requirement at one. The input is returned
    unchanged when there is nothing that could be linked — fewer than two
    obligations means no call is made at all, so an empty or single-requirement
    task costs nothing.
    """
    obligations = decomposition.obligations
    if len(obligations) < 2:
        return decomposition

    ordered_ids = [obligation.id for obligation in obligations]
    allowed = {
        "canonical_obligation_id": ordered_ids,
        "duplicate_obligation_id": ordered_ids,
    }
    result = client.complete(
        [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _user_prompt(decomposition)},
        ],
        constrain(_Links, allowed),
        None,
        parse_as=_Links,
        stage=_STAGE,
    )
    if unusable_answers is not None:
        unusable_answers.record(scan(result, allowed, _STAGE))

    survivor_of = _clusters(ordered_ids, result.links)
    return decomposition.model_copy(
        update={
            "obligations": _merged_obligations(obligations, survivor_of),
            "requirement_map": _relinked_map(decomposition.requirement_map, survivor_of),
        }
    )
