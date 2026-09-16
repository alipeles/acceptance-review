"""Turns one named plausible defect into an actual edit at actual lines.

The only part of the mutation stage that calls a model, and it is deliberately
one call per defect (DR-171 Decision 1). Folding this into defect enumeration
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

**Declining is a real answer.** A defect the smallest-edit question has no good
answer for — one about behavior that is absent, or spread across files — comes
back with an empty region label and a reason. That becomes `not_mutable` with
the reason attached, and the defect goes to the static judge. A stage that
invented an edit rather than declining would produce a mutant that tests nothing
and a survival that means nothing.
"""

from __future__ import annotations

from collections.abc import Sequence

from acceptance.concurrency import map_calls
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.mutation.attempt import MutationDescriptor
from acceptance.mutation.region import Region
from acceptance.partition import partition
from acceptance.request_blocks import Block, BlockKind, assemble
from acceptance.review_state import Defect
from acceptance.supplied_ids import UnusableAnswer, UnusableAnswerLog, constrain, scan

__all__ = ["ONE_DEFECT_PER_CALL", "build_descriptors", "from_mapping"]

_STAGE = "mutation descriptor"

#: One defect per call. The same reasoning as defect enumeration's: a call shown
#: several units and asked about one answers for the others (#317), and a
#: per-defect call keeps the request unit and the defect unit the same thing.
ONE_DEFECT_PER_CALL = 1

_SYSTEM_PROMPT = """You are given ONE named plausible defect and the source of the \
regions it implicates, with line numbers as they are in the file right now.

Produce the SMALLEST edit that would make that defect real.

THE EDIT

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

FIRST, CHECK WHETHER THE DEFECT IS ALREADY TRUE

Read the code before you edit it. The defect describes a way the change could \
fail the requirement — but sometimes the code ALREADY behaves that way. A defect \
saying "the feature is off by default" is already true if the default is off. A \
defect saying "the report never states X" is already true if it never states X.

**You cannot make a true thing truer, and you must not edit toward fixing it.** \
Asked to inject a defect that already holds, the tempting move is to change the \
code so the defect becomes injectable — turning the default on, adding the \
missing line. That is the exact opposite of what is wanted: it repairs the code, \
and the tests that then fail are catching the repair, not the defect.

When the defect already holds, return an EMPTY `region_label` and say so in \
`reason`, beginning with the words "already present". Name the line or lines \
that make it true. This is a valuable answer, not a failure — a defect that is \
present and that the tests do not notice is a finding in itself, and it needs no \
experiment to establish.

DECLINING IS A REAL ANSWER

Some defects cannot be expressed as one contiguous replacement. A defect about \
behavior that is ABSENT has no span to replace when the code genuinely omits it \
— though note that when the code DOES do the right thing, "nothing calls it" is \
injected by deleting the call, which is an ordinary edit. A defect needing \
coordinated edits in several places is not one span either.

When that is the case, return an EMPTY `region_label` and say in `reason` \
exactly why no single edit expresses this defect. Leave `replacement` empty and \
both line numbers 0.

Never invent an edit to avoid declining. A mutant that does not make the named \
defect true tests nothing, and the tests that survive it will be recorded as \
proven weak on evidence that does not exist.

When you DO produce an edit, leave `reason` empty."""


class _Descriptor(StrictResponseModel):
    region_label: str
    start_line: int
    end_line: int
    replacement: str
    reason: str


def build_descriptors(
    defects: Sequence[Defect],
    regions_by_defect: dict[str, list[Region]],
    sources: dict[str, str],
    client: ModelClient,
    unusable: UnusableAnswerLog | None = None,
) -> dict[str, MutationDescriptor | None]:
    """One descriptor per defect, or `None` where the stage declined.

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
        lambda defect: _ask_about(defect, regions_by_defect[defect.id], sources, client),
    )

    built: dict[str, MutationDescriptor | None] = {defect.id: None for defect in defects}
    for defect, (descriptor, unusable_answers) in zip(asking, answers, strict=True):
        built[defect.id] = descriptor
        if unusable is not None:
            unusable.record(unusable_answers)
    return built


def from_mapping(descriptors: dict[str, MutationDescriptor | None]):
    """Adapt a prebuilt mapping to the runner's per-defect builder.

    The runner asks for one descriptor at a time so it can be driven by a stub
    in tests, while the real stage issues its calls concurrently and therefore
    has to build them all at once. This is the join between the two, and it is
    the reason the runner never has to know that a model was involved.
    """

    def build(defect: Defect, _regions, _sources) -> MutationDescriptor | None:
        return descriptors.get(defect.id)

    return build


def _ask_about(
    defect: Defect,
    regions: list[Region],
    sources: dict[str, str],
    client: ModelClient,
) -> tuple[MutationDescriptor | None, list[UnusableAnswer]]:
    """One call, about `defect` alone.

    **Records nothing.** Calls are issued concurrently, so anything appended to
    shared state here would land in completion order and two runs over the same
    input would differ (`concurrency.py`, rule 2). Unusable answers are handed
    back and recorded by the caller, in defect order.
    """
    offered = [region for region in regions if region.path in sources]
    allowed = {"region_label": [region.label for region in offered] + [""]}
    constrained = constrain(_Descriptor, allowed)

    messages = assemble(
        [
            Block(BlockKind.INSTRUCTIONS, _SYSTEM_PROMPT),
            Block(BlockKind.SUBJECT, _subject(defect, offered, sources)),
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
) -> MutationDescriptor | None:
    """The answer as a `MutationDescriptor`, or `None` where it declined.

    A malformed span is treated as a decline rather than raised. The stage's
    contract to the runner is a descriptor or nothing, and an answer whose line
    numbers do not describe a span is one the mechanical checks would have
    refused a moment later anyway — as `not_mutable`, which is where this lands.
    """
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
        defect.description,
        "",
        "## Regions it implicates",
    ]
    for region in regions:
        lines.append("")
        lines.append(
            f"### [{region.label}] {region.path} lines {region.start_line}-{region.end_line}"
        )
        lines.append(_numbered(sources[region.path], region))
    return "\n".join(lines)


def _numbered(source: str, region: Region) -> str:
    width = len(str(region.end_line))
    rendered = []
    for number, text in enumerate(source.splitlines(), start=1):
        if region.start_line <= number <= region.end_line:
            rendered.append(f"{number:>{width}} | {text}")
    return "\n".join(rendered)
