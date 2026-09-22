"""Turns one named plausible defect into an actual edit at actual lines.

The only part of the mutation stage that calls a model. Each call is about one
defect (DR-171 Decision 1); since #334 a defect may take several calls, one per
candidate edit, each shown the candidates already refused (DR-171, revision of
2026-09-22). Folding this into defect enumeration
was rejected there for a reason worth restating: the enumerator is blind to the
tests so its denominator cannot drift toward what is already covered, and asking
the same call to also produce a working patch would reintroduce the drift from
the other side — the stage would favour defects it can express as an edit. A
recall stage must not be scored on executability.

The response shape is Decision 2's: a region label, an inclusive line span, and
the replacement text. `region_label` is narrowed to this defect's own regions
before the call, so an edit outside them is unrepresentable rather than merely
refused afterwards — the containment check in `validity.py` still runs, because
the line span inside a named region can still fall outside it.

**The model says what the code does before it edits.** `code_currently_does` is
the first field of the answer and decides what any edit means: "expected" makes
it an injection; "defective" makes the answer a finding that the code already
has the defect, with the edit kept as a repair to run the tests against;
"cannot_tell" is a decline. On #45's own review the model, told the direction
only in prose, still edited toward the expected behaviour in 9 of 66 edits.

**Declining is a real answer.** A defect the smallest-edit question has no good
answer for comes back with a named `DeclineKind` and a reason: it is not a
property of any code, or it needs more than one contiguous edit. Each becomes its
own outcome with the model's reason attached, and the defect goes to the static
judge. A stage that
invented an edit rather than declining would produce a mutant that tests nothing
and a survival that means nothing.
"""

from __future__ import annotations

import threading
from collections.abc import Sequence
from typing import Literal

from acceptance.change.context import RetrievalResult
from acceptance.concurrency import map_calls
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.mutation.attempt import (
    AlreadyDefective,
    CandidateCause,
    DeclineKind,
    DescriptorAnswer,
    DescriptorDecline,
    MutationDescriptor,
    SetAsideCandidate,
)
from acceptance.mutation.region import Region
from acceptance.mutation.surrounding import contexts_for, region_spans, render_contexts
from acceptance.partition import partition
from acceptance.request_blocks import Block, BlockKind, assemble
from acceptance.review_state import Defect
from acceptance.supplied_ids import UnusableAnswer, UnusableAnswerLog, constrain, scan

__all__ = ["ONE_DEFECT_PER_CALL", "LiveDescriptorBuilder", "build_descriptors", "from_mapping"]

_STAGE = "mutation descriptor"

#: One defect per call. The same reasoning as defect enumeration's: a call shown
#: several units and asked about one answers for the others (#317), and a
#: per-defect call keeps the request unit and the defect unit the same thing.
ONE_DEFECT_PER_CALL = 1

_SYSTEM_PROMPT = """You are given ONE named plausible defect and the source of the \
regions it implicates, with line numbers as they are in the file right now.

Produce the SMALLEST edit that would make that defect real.

THE EDIT

You may also be shown the surrounding code: the definitions the regions sit in, \
and where those are called from. Read it to understand what the code does. Your \
edit must still land inside one of the offered regions.

Replace one contiguous run of lines in ONE file. Give:

- `region_label`: which of the offered regions the edit lands in.
- `start_line` and `end_line`: the first and last line to replace, inclusive,
  using the line numbers shown. To change a single line, set both to it.
- `replacement`: the text those lines become, including its indentation and its
  trailing newline. An empty string deletes them.

The replacement must keep the file valid. For code that means it still parses \
and still loads — an edit that stops the module importing tests nothing, because \
every test then fails for a reason that has nothing to do with the defect.

SMALLEST MEANS SMALLEST

Change the behavior the defect names and nothing else. Do not rename anything, \
do not reformat, do not fix unrelated things you notice. The edit is read by a \
person deciding whether the defect it created is the one that was named, and a \
large edit makes that impossible.

A defect is not made real by deleting the feature. Break it the way a careless \
implementation would: an off-by-one, a wrong constant, a flipped comparison, a \
dropped case, a wrong unit. The point is an edit a plausible mistake would \
produce.

FILES THAT ARE NOT CODE

A requirement stated in prose can be broken in prose. If the defect is about \
what a document says, edit the document — the tests that read it are the ones \
that would catch it.

FIRST, SAY WHICH BEHAVIOUR THE CODE HAS NOW

The defect comes with two behaviours: EXPECTED (what the code must do) and \
DEFECTIVE (what it would do if the defect were present). Exactly one of them \
describes the code as it is. Read the code, then answer `code_currently_does` \
before anything else:

- "expected": the code does the EXPECTED behaviour. Give the edit that makes it \
  do the DEFECTIVE behaviour instead. After your edit the DEFECTIVE sentence must \
  be true of the code and the EXPECTED sentence false.
- "defective": the code ALREADY does the DEFECTIVE behaviour. That is a finding \
  about the code, and your answer to this field is what records it. Name in \
  `reason` the lines that do it. Then give the edit that REPAIRS it — the \
  smallest edit that makes the code do the EXPECTED behaviour. The candidate \
  tests are run against that repair to see whether any test notices.
- "cannot_tell": you cannot see enough of the code to decide. Say in `reason` \
  what you could not see, and give no edit. Do not guess.

The edit you give always moves the code AWAY from what `code_currently_does` \
says. An edit that leaves the behaviour the same is never an answer.

When no EXPECTED and DEFECTIVE behaviours are given, use the defect's \
description as the DEFECTIVE behaviour and its opposite as the EXPECTED one.

DECLINING IS A REAL ANSWER

Some defects cannot be made true by any edit. A defect that is not about what \
any file says or does — a process, a question someone would need to check — has \
no content to change; set `decline` to "not_a_code_property".

Other defects cannot be expressed as one contiguous replacement. A defect about \
behavior that is ABSENT has no span to replace when the code genuinely omits it \
— though note that when the code DOES do the right thing, "nothing calls it" is \
injected by deleting the call, which is an ordinary edit. A defect needing \
coordinated edits in several places is not one span either. Set `decline` to \
"not_one_contiguous_edit".

When you decline, say exactly why in `reason`, leave `region_label` and \
`replacement` empty and both line numbers 0.

Never invent an edit to avoid declining. A mutant that does not make the named \
defect true tests nothing, and the tests that survive it will be recorded as \
proven weak on evidence that does not exist.

When you do not decline, set `decline` to "none"."""


class _Descriptor(StrictResponseModel):
    # First, so the model commits to what the code does before it writes an
    # edit — and so the direction of the edit is read from this field rather
    # than inferred from the edit itself.
    code_currently_does: Literal["expected", "defective", "cannot_tell"]
    region_label: str
    start_line: int
    end_line: int
    replacement: str
    # "none" for an edit; otherwise one of `DeclineKind`'s values. A literal
    # rather than an optional enum because strict mode has no optional fields.
    decline: Literal["none", "not_a_code_property", "not_one_contiguous_edit"]
    reason: str


def build_descriptors(
    defects: Sequence[Defect],
    regions_by_defect: dict[str, list[Region]],
    sources: dict[str, str],
    client: ModelClient,
    unusable: UnusableAnswerLog | None = None,
    surrounding: RetrievalResult | None = None,
) -> dict[str, DescriptorAnswer]:
    """One answer per defect: a descriptor, a typed decline, or `None`.

    `surrounding` is the M2.2 retrieval for the change. When given, each call is
    also shown the enclosing definitions and call sites its defect's regions fall
    in (`surrounding.py`); the edit is still confined to the named regions.

    `None` means no usable answer — no region to ask about, or a response that
    described no span and named no decline.

    Calls are issued concurrently and the results are recorded in the order the
    defects were given, not in completion order — `concurrency.py` rule 2, which
    is what keeps two runs over the same input byte-identical.

    A defect with no resolved region is not asked about at all. There is nothing
    to offer the call and nothing it could answer, and spending a request to be
    told so would cost one per absence defect on every review.
    """
    asking = [defect for defect in defects if regions_by_defect.get(defect.id)]

    answers = map_calls(
        asking,
        lambda defect: _ask_about(
            defect, regions_by_defect[defect.id], sources, client, surrounding
        ),
    )

    built: dict[str, DescriptorAnswer] = {defect.id: None for defect in defects}
    for defect, (descriptor, unusable_answers) in zip(asking, answers, strict=True):
        built[defect.id] = descriptor
        if unusable is not None:
            unusable.record(unusable_answers)
    return built


def from_mapping(descriptors: dict[str, DescriptorAnswer]):
    """Adapt a prebuilt mapping to the runner's per-defect builder.

    The runner asks for one descriptor at a time so it can be driven by a stub
    in tests, while the real stage issues its calls concurrently and therefore
    has to build them all at once. This is the join between the two, and it is
    the reason the runner never has to know that a model was involved.
    """

    def build(defect: Defect, _regions, _sources, _previous=()) -> DescriptorAnswer:
        return descriptors.get(defect.id)

    return build


class LiveDescriptorBuilder:
    """The runner's descriptor builder, asking the model as each candidate is
    needed rather than all at once beforehand (#334).

    It has to be live: the second candidate's request shows the first one's
    refusal, which only exists once the runner has checked it.

    Calls happen inside the runner's concurrent attempts, so unusable answers
    are held per (defect, candidate) and recorded afterwards in sorted order by
    `record_unusable` — `concurrency.py` rule 2, the same reason
    `build_descriptors` hands them back rather than recording them.
    """

    def __init__(self, client: ModelClient, surrounding: RetrievalResult | None = None):
        self._client = client
        self._surrounding = surrounding
        self._unusable: dict[tuple[str, int], list[UnusableAnswer]] = {}
        self._lock = threading.Lock()

    def __call__(
        self,
        defect: Defect,
        regions: Sequence[Region],
        sources: dict[str, str],
        previous: Sequence[SetAsideCandidate] = (),
    ) -> DescriptorAnswer:
        answer, unusable = _ask_about(
            defect, list(regions), sources, self._client, self._surrounding, previous
        )
        with self._lock:
            self._unusable[(defect.id, len(previous))] = unusable
        return answer

    def record_unusable(self, log: UnusableAnswerLog) -> None:
        for key in sorted(self._unusable):
            log.record(self._unusable[key])


def _ask_about(
    defect: Defect,
    regions: list[Region],
    sources: dict[str, str],
    client: ModelClient,
    surrounding: RetrievalResult | None = None,
    previous: Sequence[SetAsideCandidate] = (),
) -> tuple[DescriptorAnswer, list[UnusableAnswer]]:
    """One call, about `defect` alone.

    `previous` holds the candidates already set aside for this defect. They are
    shown only when there are some, so a defect's first request is exactly what
    it was before #334 and every recording of one still replays.

    **Records nothing.** Calls are issued concurrently, so anything appended to
    shared state here would land in completion order and two runs over the same
    input would differ (`concurrency.py`, rule 2). Unusable answers are handed
    back and recorded by the caller, in defect order.
    """
    offered = [region for region in regions if region.path in sources]
    allowed = {"region_label": [region.label for region in offered] + [""]}
    constrained = constrain(_Descriptor, allowed)

    subject = _subject(defect, offered, sources)
    context = render_contexts(contexts_for(region_spans(offered), surrounding))
    if context:
        subject = f"{subject}\n\n{context}"
    if previous:
        subject = f"{subject}\n\n{_earlier_candidates(previous)}"
    messages = assemble(
        [
            Block(BlockKind.INSTRUCTIONS, _SYSTEM_PROMPT),
            Block(BlockKind.SUBJECT, subject),
        ]
    )
    batch = partition([defect], ONE_DEFECT_PER_CALL, key=lambda d: d.id)[0]
    result = client.complete(
        messages,
        constrained,
        batch.request_partition(),
        parse_as=_Descriptor,
        stage=_STAGE,
    )
    return _descriptor_from(result, offered, sources), scan(result, allowed, _STAGE)


def _descriptor_from(
    result: _Descriptor, regions: Sequence[Region], sources: dict[str, str]
) -> DescriptorAnswer:
    """The answer as an injection, a claim the code is already defective, a
    typed decline, or `None` if it is unusable.

    `code_currently_does` is read first and decides what the edit means.
    "defective" is a finding whatever else the answer says, and its edit is kept
    as the repair. "cannot_tell" is a decline. Only "expected" makes the edit an
    injection, and then a named decline still wins over it: the model has said
    no edit makes this defect true.

    A malformed span, or an empty region with no decline named, is `None` rather
    than raised. The stage's contract to the runner is an answer or nothing, and
    such an answer is one the mechanical checks would have refused a moment
    later anyway — as `not_mutable`, which is where this lands.
    """
    reason = result.reason.strip()
    if result.code_currently_does == "defective":
        return AlreadyDefective(
            reason=reason or "the code already does the defective behaviour; no lines named",
            repair=_span_from(result, regions, sources),
        )
    if result.code_currently_does == "cannot_tell":
        return DescriptorDecline(
            kind=DeclineKind.CANNOT_TELL,
            reason=reason or "could not tell which behaviour the code has; no reason given",
        )
    if result.decline != "none":
        kind = DeclineKind(result.decline)
        return DescriptorDecline(
            kind=kind, reason=reason or f"declined as {kind.value}, with no reason given"
        )
    return _span_from(result, regions, sources)


def _span_from(
    result: _Descriptor, regions: Sequence[Region], sources: dict[str, str]
) -> MutationDescriptor | None:
    """The edit in `result`, or `None` when it names no usable span."""
    label = result.region_label.strip()
    if not label:
        return None
    by_label = {region.label: region for region in regions}
    region = by_label.get(label)
    if region is None:
        return None
    if result.start_line < 1 or result.end_line < result.start_line:
        return None
    # A span running past the end of the file keeps what it does reach; the
    # mechanical checks refuse the span itself.
    source_lines = sources[region.path].splitlines(keepends=True)
    return MutationDescriptor(
        path=region.path,
        start_line=result.start_line,
        end_line=result.end_line,
        replacement=result.replacement,
        region_label=label,
        original="".join(source_lines[result.start_line - 1 : result.end_line]),
    )


def _subject(defect: Defect, regions: Sequence[Region], sources: dict[str, str]) -> str:
    """The defect and the numbered source of each region it named.

    Numbered because the answer is a line span and the model has no other way to
    name one. The numbers are absolute — the file's own — so that the answer
    needs no translation on the way back, and an off-by-one in this rendering
    cannot quietly become an off-by-one in the mutant.
    """
    lines = [
        "## The defect",
        f"id: {defect.id}",
        f"type: {defect.type.value}",
        f"description: {defect.description}",
    ]
    # Each on its own labelled line, so the direction of the edit is read from
    # typed fields rather than inferred from the wording of one sentence.
    if defect.expected_behavior and defect.defective_behavior:
        lines.append(f"EXPECTED: {defect.expected_behavior}")
        lines.append(f"DEFECTIVE: {defect.defective_behavior}")
    lines += ["", "## Regions it implicates"]
    for region in regions:
        lines.append("")
        lines.append(
            f"### [{region.label}] {region.path} lines {region.start_line}-{region.end_line}"
        )
        lines.append(_numbered(sources[region.path], region))
    return "\n".join(lines)


#: What the model is told about each kind of refusal. Fixed sentences, not the
#: recorded reason, for one kind in particular: an edit refused after the tests
#: ran against it was refused on what those tests did, and nothing about what
#: the tests did under an edit may reach a model
#: (`tests/test_edit_results_never_reach_a_prompt.py`). The mechanical checks'
#: own reasons carry nothing from a test run and are shown as they are.
_REFUSED_AFTER_RUN = (
    "it passed the checks on the edit's text but was refused once it was applied; "
    "try a different, smaller edit that changes only the behaviour the defect names"
)
_CHANGED_NOTHING = (
    "it changed nothing: it was identical to the lines it replaced, or differed only "
    "in comments or whitespace. The edit must change what the code does"
)
_UNUSABLE = "the answer named no usable span to replace"


def _earlier_candidates(previous: Sequence[SetAsideCandidate]) -> str:
    """The candidates already set aside for this defect, and why, so the next
    answer is a different edit rather than the same one again."""
    lines = [
        "## Earlier edits for this defect, all refused",
        "",
        (
            "Each edit below was refused for the reason given. Give a different edit "
            "that avoids the problem, or decline if no single contiguous edit makes the "
            "defect true."
        ),
    ]
    for number, candidate in enumerate(previous, start=1):
        lines.append("")
        if candidate.cause is CandidateCause.REFUSED_AFTER_RUN:
            why = _REFUSED_AFTER_RUN
        elif candidate.cause is CandidateCause.CHANGED_NOTHING:
            why = _CHANGED_NOTHING
        elif candidate.cause is CandidateCause.UNUSABLE_ANSWER:
            why = _UNUSABLE
        else:
            why = candidate.reason
        edit = candidate.descriptor
        if edit is None:
            lines.append(f"### Earlier edit {number}: refused because {why}")
            continue
        lines.append(
            f"### Earlier edit {number}: {edit.path} lines {edit.start_line}-{edit.end_line}, "
            f"refused because {why}"
        )
        lines.append("Replacement it gave:")
        lines.append(edit.replacement.rstrip("\n") or "(empty — it deleted the lines)")
    return "\n".join(lines)


def _numbered(source: str, region: Region) -> str:
    width = len(str(region.end_line))
    rendered = []
    for number, text in enumerate(source.splitlines(), start=1):
        if region.start_line <= number <= region.end_line:
            rendered.append(f"{number:>{width}} | {text}")
    return "\n".join(rendered)
