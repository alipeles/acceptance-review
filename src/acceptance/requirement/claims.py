"""Claims: verbatim, line-anchored spans of the mandate (#436).

`docs/decomposition-redesign.md` §2 (Claim) and §5 steps 1 and 2. The mandate is
split into units by the code, one per sentence of every block the parser
produces, and one model call decides for each unit whether it feeds claim
construction or is background. Every unit that is not background becomes a
claim, word for word. No model call writes a claim.

**Every block is split, whatever heading it sits under.** The parser files text
it cannot place — a bullet list under `## Task` (#373), a section under a heading
it does not know — as `unclaimed`, and the requirement registry gives that text
no id. Claims are built from all of it, `## Context` included: the heading is
shown to the model as a hint and is never the decision. That is what ends
#373's loss without teaching the parser more headings.

**An undecided unit feeds claims.** A unit the answer leaves out, or decides more
than once, is treated as `feeds` and recorded as an unusable answer. Building a
claim from background costs a pruned obligation later; dropping a requirement
here costs everything (§5 step 1).

Determinism: units and claims are a function of the mandate text and the
decisions, assembled in document order, so the same mandate replayed against the
same recording yields byte-identical claims.
"""

from __future__ import annotations

from typing import Literal

from markdown_it import MarkdownIt

from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.request_blocks import Block, BlockKind, assemble
from acceptance.requirement.spans import normalise, sentence_spans
from acceptance.requirement.task_file import ParsedTaskFile
from acceptance.review_state import Claim, ClaimSet, MandateUnit, UnitDecision
from acceptance.supplied_ids import UnusableAnswer, UnusableAnswerLog, constrain, scan

__all__ = ["UNIT_STAGE", "build_claims", "split_units"]

UNIT_STAGE = "unit classification"

_SYSTEM_PROMPT = """\
You are reading a change mandate: the task a software change was asked to
deliver. It has been split into units, one sentence or block each, and each unit
is given with its id and the heading it sits under.

For each unit, decide one thing: does it state, or might it state, something the
delivered change must do, must be, or must not touch?

- `feeds`: it does. Requests, constraints, conditions on how the work is done,
  scope exclusions, acceptance criteria, and anything that could be read as one.
- `background`: it states nothing the delivered change must satisfy. It describes
  how things are today, why the change is wanted, history, alternatives that were
  considered and rejected, or references for the reader.
- `unsure`: you cannot tell. Answer `unsure` rather than guess `background`;
  a unit marked background is never read again.

The heading is a hint, not the answer. Text under a heading such as "Context"
or "Background" can still state a requirement, and text under "Task" can still
describe how things are today.

Decide every unit exactly once, by its id. Write the reason first, in one
sentence, then the decision.
"""


class _UnitAnswer(StrictResponseModel):
    """One unit's decision. The reason comes first so the decision follows it."""

    unit_id: str
    reason: str
    decision: Literal["feeds", "background", "unsure"]


class _UnitDecisions(StrictResponseModel):
    decisions: list[_UnitAnswer]


def split_units(parsed: ParsedTaskFile) -> list[MandateUnit]:
    """Every sentence of every block the parser produced, in document order.

    Returned undecided — `decision` is `feeds` and `decided` False — so that a
    unit nothing has ruled on reads as one that feeds claims.
    """
    blocks = sorted(
        [
            *parsed.behavior,
            *parsed.constraints,
            *parsed.scope_exclusions,
            *parsed.completion_expectations,
            *parsed.context,
            *parsed.unclaimed,
        ],
        key=lambda span: (span.start, span.end),
    )
    pieces = [piece for block in blocks for piece in sentence_spans(block)]
    headings = _headings(parsed.source)
    width = max(2, len(str(len(pieces))))
    return [
        MandateUnit(
            id=f"unit-{ordinal:0{width}d}",
            heading=_heading_before(headings, _line_of(parsed.source, piece.start)),
            line=_line_of(parsed.source, piece.start),
            span=piece,
            decision=UnitDecision.FEEDS,
            decided=False,
        )
        for ordinal, piece in enumerate(pieces, start=1)
    ]


def build_claims(
    parsed: ParsedTaskFile,
    client: ModelClient,
    unusable_answers: UnusableAnswerLog | None = None,
) -> ClaimSet:
    """Decide each unit of the mandate, and build a claim from every one that feeds.

    One call for the whole mandate, so each unit is judged with the rest in
    view. A mandate with no units makes no call.
    """
    units = split_units(parsed)
    if not units:
        return ClaimSet()

    unit_ids = [unit.id for unit in units]
    messages = assemble(
        [
            Block(BlockKind.INSTRUCTIONS, _SYSTEM_PROMPT),
            Block(BlockKind.SUBJECT, _user_prompt(units)),
        ]
    )
    allowed = {"unit_id": unit_ids}
    result = client.complete(
        messages,
        constrain(_UnitDecisions, allowed),
        parse_as=_UnitDecisions,
        stage=UNIT_STAGE,
    )
    if unusable_answers is not None:
        unusable_answers.record(scan(result, allowed, UNIT_STAGE))

    decided = _apply(units, result, unusable_answers)
    claims = [
        Claim(
            id="claim-" + unit.id.removeprefix("unit-"),
            unit_id=unit.id,
            line=unit.line,
            span=unit.span,
        )
        for unit in decided
        if unit.feeds
    ]
    return ClaimSet(units=decided, claims=claims)


def _apply(
    units: list[MandateUnit],
    result: _UnitDecisions,
    unusable_answers: UnusableAnswerLog | None,
) -> list[MandateUnit]:
    """Each unit with the answer's decision about it, in document order.

    A unit decided exactly once takes that decision. A unit decided several
    times takes `background` only if every answer said so, since one answer
    saying otherwise is enough doubt to keep it. A unit not decided at all
    feeds. Both are recorded as unusable answers.
    """
    answers: dict[str, list[_UnitAnswer]] = {}
    for answer in result.decisions:
        answers.setdefault(answer.unit_id, []).append(answer)

    problems: list[UnusableAnswer] = []
    out: list[MandateUnit] = []
    for unit in units:
        given = answers.get(unit.id, [])
        if len(given) == 1:
            out.append(
                unit.model_copy(
                    update={
                        "decision": UnitDecision(given[0].decision),
                        "reason": given[0].reason,
                        "decided": True,
                    }
                )
            )
            continue
        if not given:
            problems.append(
                UnusableAnswer(
                    stage=UNIT_STAGE,
                    field="decisions",
                    returned_id=unit.id,
                    reason="the answer did not decide this unit, so it feeds claims",
                )
            )
            out.append(unit)
            continue
        background = all(answer.decision == "background" for answer in given)
        problems.append(
            UnusableAnswer(
                stage=UNIT_STAGE,
                field="decisions",
                returned_id=unit.id,
                reason=(
                    f"the answer decided this unit {len(given)} times; "
                    + (
                        "every answer said background, so it is background"
                        if background
                        else "not every answer said background, so it feeds claims"
                    )
                ),
            )
        )
        out.append(
            unit.model_copy(
                update={
                    "decision": UnitDecision.BACKGROUND if background else UnitDecision.FEEDS,
                    "reason": " / ".join(answer.reason for answer in given),
                    "decided": False,
                }
            )
        )
    if unusable_answers is not None:
        unusable_answers.record(problems)
    return out


def _user_prompt(units: list[MandateUnit]) -> str:
    """One line per unit: id, heading, text. Typed fields, not the mandate's markdown."""
    lines = ["The mandate's units, in order:", ""]
    for unit in units:
        heading = unit.heading if unit.heading is not None else "(no heading)"
        lines.append(f"[{unit.id}] under: {heading}")
        lines.append(f"    {normalise(unit.span.text)}")
    return "\n".join(lines)


def _headings(source: str) -> list[tuple[int, str]]:
    """(0-based line, text) of every heading, in document order."""
    tokens = MarkdownIt().parse(source)
    found: list[tuple[int, str]] = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.map is not None:
            inline = tokens[index + 1] if index + 1 < len(tokens) else None
            text = inline.content.strip() if inline is not None and inline.type == "inline" else ""
            found.append((token.map[0], text))
    return found


def _heading_before(headings: list[tuple[int, str]], line: int) -> str | None:
    """The nearest heading above 1-based `line`, or None if there is none."""
    nearest: str | None = None
    for heading_line, text in headings:
        if heading_line + 1 < line:
            nearest = text
        else:
            break
    return nearest


def _line_of(source: str, offset: int) -> int:
    """The 1-based line `offset` falls on."""
    return source.count("\n", 0, offset) + 1
