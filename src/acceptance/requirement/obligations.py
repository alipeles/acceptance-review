"""Obligation decomposition (M1.2/M1.3 and M1.2.r1, §7.3/§9.1).

Converts a parsed task file into discrete, typed obligations plus the material
ambiguities that need user judgment. Decomposition is a semantic judgment, so
it is a schema-constrained model call through the M0.4 harness — recorded for
replay, never a live call in tests.

Each obligation and open question is linked to a `TextSpan` in the task (the
model returns an exact `source_quote` which we locate in the source), so every
output traces back to the requirement text it came from (CLAUDE.md invariant).
Material ambiguities are surfaced as `OpenQuestion`s rather than invented
obligations — uncertainty is a first-class, expected result (M1.3).

**What decomposition returns is a mapping, not a list** (M1.2.r1, DR-202). The
call is asked for one disposition per identified requirement, so a requirement
that produced nothing is a recorded fact rather than an absence. A flat
obligation list made a response covering 20 of 29 requirements exactly as
well-formed as one covering all 29, which is how #195's Gate 1 lost 4 of 15
Completion expectations and 5 of 8 Scope exclusions without the review saying so.

**A response that does not account for the mandate is rejected, not recorded**
(M1.2.r2). Each disposition is one of three shapes, each structurally carrying
what its name claims, and reconciliation raises on anything else: a missing
requirement, a duplicate, an id outside the registry, or a claim naming outputs
the response never produced. `M1.2.r1` recorded those as a fourth disposition
instead, which let a malformed response reach a verdict as a soft finding.

**The decomposer is code-blind** (DR-202 decision 8): it takes a parsed task
file and a client, and never a `ChangeSet`, a repository path or a head
revision. Decomposing the mandate in light of the delivered implementation makes
a missing obligation and a missing implementation correlated errors, which
destroys the one thing the review exists to detect. Pinned by a test.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from pydantic import Field

from acceptance.config import DEFAULT_DECOMPOSE_BATCH_SIZE
from acceptance.llm import (
    ModelClient,
    SchemaValidationError,
    StrictResponseModel,
    inline_schema_refs,
)
from acceptance.model_base import PersistableModel
from acceptance.partition import partition
from acceptance.requirement.carry import CarryPlan, derivation_kind, plan_carry
from acceptance.requirement.ledger import (
    DECOMPOSE_STAGE_LOGIC_VERSION,
    Derivation,
    LedgerEntry,
    MergeDecision,
    RequirementDerivation,
    carry_key,
)
from acceptance.requirement.registry import build_registry
from acceptance.requirement.task_file import ParsedTaskFile
from acceptance.review_state import (
    Disposition,
    Obligation,
    ObligationType,
    OpenQuestion,
    RequiredEvidence,
    RequirementDisposition,
    RequirementMap,
    RequirementRef,
    RequirementSection,
)
from acceptance.source_ref import TextSpan, find_span
from acceptance.supplied_ids import (
    UnusableAnswer,
    UnusableAnswerLog,
    constrain,
    scan,
)

_STAGE = "decompose"

_SYSTEM_PROMPT = """\
You decompose a software task into discrete, typed acceptance obligations and
the ambiguities that need human judgment.

For each obligation: a short stable `id` slug (kebab-case, unique); a
`description`; a `type` from the fixed set (functional, boundary,
error_handling, invariant, regression, compatibility,
explanation_observability, docs_config, human_review, test_demand — see THE
`test_demand` TYPE below); `importance` (critical
or normal); `explicit` (true if directly stated in the task, false if
reasonably inferred); an `observable_behavior`; and `source_quote`, an EXACT
substring of the task text this obligation derives from.

Emit an inferred obligation (explicit=false) only when the inference is
reasonable and low-risk. When a requirement is materially underspecified — you
would have to guess a qualifier, value, or behavior to proceed — do NOT invent
an obligation for it. Instead return an `open_question` with a stable `id`, the
`question` to put to the user, an `importance`, and a `source_quote` for the
ambiguous text.

State every obligation as a POSITIVE invariant — the property the delivered
code must HOLD — never as a prohibition. A requirement phrased as "don't ...",
"never ...", or "leave X unchanged" describes a property to PRESERVE; restate
it as that property:
- "Don't change the existing checkout behavior" -> "Preserve the existing
  checkout behavior."
- "Don't add new dependencies" -> "Keep the dependency set unchanged."
- "Don't slow down the report" -> "Keep the report's runtime within its
  current bound."
A prohibition and the invariant it protects are the same obligation; emit the
positive form, because it states what must be TRUE rather than what must be
absent — an obligation that only says what must be absent can never be shown
addressed by looking at what the diff contains.

THE `test_demand` TYPE

A requirement that asks for a TEST — "a test asserts that X", "add a test
covering X", "X is demonstrated by a test" — yields an obligation typed
`test_demand`. Its `description` states the demand for the test, not X.

    "A test asserts that an embedded comma in the customer name is escaped."
    -> type: test_demand
       description: "A test asserts that an embedded comma in the customer
                     name is escaped."

The demand for the test is the requirement. Code that already escapes the
comma, with nobody having written the test, satisfies "the comma is escaped"
and violates "a test asserts the comma is escaped" — separate pieces of work,
and only the second is what the bullet asked for.

**The type is decided by the requirement text alone, and by nothing else.** Use
`test_demand` when THIS requirement asks for a test. Do not use it because
another bullet elsewhere in the file asks for a test of the same behavior:

    "The export writes a header row naming every column."
    -> type: functional     (a behavior; this bullet demands no test)
    NOT test_demand

Both directions lose a requirement. Typing a test demand as something else
collapses it into the behavior it is about; typing a behavior `test_demand`
collapses the behavior into the test. A Constraints bullet stating a behavior
and a Completion bullet demanding a test of it are two requirements, and they
stay two only if they carry different types.

Every requirement of the same shape gets the same type. If two bullets both
ask for a test and you typed only one `test_demand`, you have drawn a
distinction the task file does not make.

Granularity — isolate distinct computations, keep cohesive behaviors whole:

- Isolate a sub-clause that defines a DISTINCT COMPUTATION or derived value — a
  formula or calculation with its own logic, embedded via "where ...",
  "using ...", "based on ..." — that could be computed wrongly on its own,
  independently of the step that uses it. E.g. "charge for the hours worked at
  the overtime rate, where the overtime rate is 1.5x base pay" is TWO
  obligations: charging for the hours, and the overtime-rate formula (the rate
  can be wrong independently of the multiplication). Do not fold such a
  computation into its host clause.

- Keep as ONE obligation a single cohesive behavior — a parse, a
  lookup/mapping, a formatting or display rule — even when it spans several
  inputs, fields, or cases. "Parse the token into its type and value" is one
  obligation, not a separate 'read the token' and 'classify it'; "render each
  column right-aligned" is one display rule, not one per column.

The test: is the sub-clause a SEPARATE calculation that could be individually
wrong, or one behavior applied across cases? Separate the former; keep the
latter whole. Prefer the smallest set that still isolates every distinct
computation.

ACCOUNTING FOR EVERY REQUIREMENT

You are given the task file's requirements as an identified list. Return
`requirement_dispositions` containing EXACTLY ONE entry for EVERY requirement id
you were given — including the ones you find unremarkable. A requirement you
omit is not treated as unimportant; it is recorded as one you failed to read.

Each disposition is one of:

- `yielded` — the requirement produced one or more obligations. List their ids
  in `obligation_ids`. This is the normal case and should be the large majority.
- `open_question` — the requirement is materially underspecified, so you raised
  a question instead of inventing an obligation. List the question ids in
  `open_question_ids`.
- `no_obligation` — the requirement imposes nothing checkable on the delivered
  change. Give the `reason`. One narrow case, and no other: a section marker
  such as "Implementation" or "Deliverable", standing alone with no requirement
  under it. It is NOT the answer for a requirement that is merely hard to
  phrase, and it is NOT the answer for a scope exclusion — see SCOPE EXCLUSIONS
  below.

REFERENCES YOU CANNOT RESOLVE

A requirement will often cite something you were not given — an issue number, a
ticket, a document, a person, a symbol from a file you cannot see. This is
NORMAL and it does NOT weaken the requirement. **Decompose it from the text you
DO have.** Never dispose of a requirement as `no_obligation` on the grounds that
it points at something outside your view; that is a fact about your inputs, not
about the mandate.

    "The report totals are rounded the way #205 settled."

states a requirement — the totals are rounded some particular way — whether or
not you know what #205 is. The clause "the way #205 settled" is an attribution,
not the content. Read past it and decompose the rest.

The test is whether the sentence constrains the delivered change for a reader
who also cannot resolve the reference. Almost always it does. If the unresolved
reference genuinely leaves you unable to tell WHAT is required — not merely
unable to see the related material — raise an `open_question` instead. Do not
answer with `no_obligation`.

SCOPE EXCLUSIONS

A `## Scope exclusions` section names work this change must NOT do. Every bullet
under it is `yielded`, and produces EXACTLY ONE obligation stating the ABSENCE
of the excluded work:

    "How finely a requirement is split into obligations, which is #117."
    ->  "The change does not alter how finely a requirement is split into
         obligations."

Read that form closely, because a wrong form sits on either side of it.

WRONG — the excluded work restated as work to do:

    NOT -> "Split each requirement at the level of distinct computations."

WRONG — the excluded work asserted as a property to hold:

    NOT -> "Keep the current split granularity."
    NOT -> "Preserve the current split granularity."

Both make the boundary into a requirement OF the change, which is the opposite
of what the bullet says. The right form asserts only that the change did not go
there. Its presence in the diff refutes it; nothing else about the change bears
on it at all.

This is the one place the positive-restatement rule above does not apply,
because the rule inverts here. "Don't change the checkout behavior" names a
PROPERTY, and its positive form — "the checkout behavior is preserved" — says
the same thing. A scope exclusion names WORK, and work has no positive form, so
the only faithful statement of it is the negative one.

`observable_behavior` names the WORK whose presence in the change would REFUTE
the obligation — what a reader looks for in order to find a breach:

    "pagination logic appearing in the diff"
    "compression steps or archive creation in the export path"

NOT a property the change leaves intact:

    NOT -> "the implementation leaves pagination unchanged"
    NOT -> "currency support is preserved"

Those are the positive reframing this section already rejects for `description`,
moved one field along, and it is rejected here too. The words "preserve",
"keep", "maintain" and "unchanged" have no place in either field.

Whether such an obligation needs a TEST is a separate question, answered under
WHICH EVIDENCE AN OBLIGATION REQUIRES below. Most scope exclusions need none —
no test can demonstrate that work was not done. Some do: a bullet excluding
WORK ("we are not also building the export feature") is unevidenceable by test,
while a bullet excluding a change to BEHAVIOR ("this does not alter how
pagination works") names something a regression test asserts directly. Decide it
per bullet; the heading does not settle it.

Every bullet under one `## Scope exclusions` heading is treated the same way as
its siblings — they are the same kind of statement. If one of them reads like it
demands work, re-read it: it is naming the work it excludes.

WHICH EVIDENCE AN OBLIGATION REQUIRES

Set `required_evidence` on every obligation. It has exactly four values, and it
is decided HERE — no later stage revisits it, and nothing downstream will ask
you again:

- `code_and_tests` — the default, and correct for almost everything. The change
  must contain something that addresses the obligation, AND a test must
  demonstrate the behavior.
- `code_only` — the source itself settles it, and no test would add anything.
  A pinned dependency version, a CI action's major version, a configuration
  value, "implement this using pydantic", or work a scope exclusion says was not
  done. A reader confirms these by looking at the change.
- `tests_only` — the obligation asks for a TEST and no source change of its own,
  as in a mandate's "a test asserts that X". The test is the whole of what it
  demands.
- `neither` — the repository cannot settle it at all: runtime behavior under
  load, how something looks, a judgement only a person can make.

Choose `code_and_tests` unless you can say WHY less is required, and put that
why in `required_evidence_reason` — one specific sentence about THIS obligation,
which a reader who disagrees can argue with. Leave the reason empty only for
`code_and_tests`. A narrowing with no reason will be discarded and the
obligation will require both kinds.

Two mistakes to avoid, in opposite directions. Do not answer `code_only` merely
because writing the test looks awkward, or because the behavior is hard to
reach: "no test is owed" is a statement about the KIND of thing the obligation
is, not about the effort of testing it, and a wrong one silently removes the
obligation from the evidence the review checks. And do not answer
`code_and_tests` for something a test genuinely cannot observe, which asks for
evidence that cannot exist.

Use `neither` rarely. It excuses the obligation from everything this review
measures, so a mandate answered that way widely would be reviewed not at all.

Each requirement's obligations are carried INSIDE its own disposition, so every
obligation belongs to exactly one requirement. Account for each requirement on
its own: split it into several obligations, or decline it with `no_obligation`.

When two requirements state the same thing — commonly one bullet under
Constraints and another under Completion expectations — give an obligation to
EACH of them. Two obligations saying nearly the same thing is the correct
output here; a later pass merges them. Write each one out in full under its own
requirement rather than trying to avoid the duplication.

A behavior and a demand for a TEST of that behavior are NOT the same thing,
even when the Constraints bullet and the Completion bullet are worded almost
identically. Give each its own obligation and keep the test framing on the one
that has it, per A REQUIREMENT FOR A TEST above. The later pass is told these
two do not merge, and it can only see that if you left the framing in."""


# Empty arrays are returned explicitly (StrictResponseModel: no defaults).
class _DecomposedObligation(StrictResponseModel):
    id: str
    description: str
    type: ObligationType
    importance: str
    explicit: bool
    observable_behavior: str
    source_quote: str
    # Which kinds of evidence this obligation requires, decided here and nowhere
    # else (#266). A single enum, so "both required and not required" is not a
    # sayable answer; a reason, so narrowing is auditable rather than asserted.
    required_evidence: RequiredEvidence
    required_evidence_reason: str


class _OpenQuestion(StrictResponseModel):
    id: str
    question: str
    importance: str
    source_quote: str


class _Yielded(StrictResponseModel):
    """Obligations were derived, and they belong to this requirement alone.

    The obligations are CARRIED here rather than referenced by id from a flat
    top-level list (#204, DR-204). That is what makes "derivation performs no
    linking" a property of the shape instead of a rule the model is asked to
    follow: there is no id to write twice, so one obligation cannot be named by
    two requirements.

    The previous shape put `obligations` at the top level and had each
    disposition point into it by unconstrained string — which made linking the
    natural encoding for "these two requirements state the same thing", and the
    model used it despite two paragraphs of prompt forbidding it. Measured, not
    assumed: a task file stating one requirement under Constraints and again
    under Completion expectations — the restatement DR-202 itself calls typical
    — linked on every attempt, on subject matter having nothing to do with
    decomposition.

    Rejecting that after the fact left the mandate unaccounted for and aborted
    the review, so an ordinary task file could not be reviewed at all. A rule
    the schema contradicts is not enforceable by asking harder; #217 settled the
    same argument for the empty-`yielded` case.
    """

    requirement_id: str
    disposition: Literal["yielded"]
    # Split rather than `list[...]` with a minimum, because a minimum cannot be
    # expressed on the wire: OpenAI strict mode rejects `minItems`. One required
    # field plus the rest makes "at least one" a property of the SHAPE, so the
    # empty case is unrepresentable in the schema the model is given rather than
    # merely rejected after it answers.
    obligation: _DecomposedObligation
    more_obligations: list[_DecomposedObligation]

    def derived(self) -> list[_DecomposedObligation]:
        """Exactly what the response said, echo and all.

        The decoded list — what the requirement actually yielded — is
        `_decode_obligations`. This stays raw so a test can assert on the
        response as received.
        """
        return [self.obligation, *self.more_obligations]

    def echoes_head(self) -> bool:
        """`more_obligations` opens with a byte-identical copy of `obligation`.

        Model equality compares every field, so this is exact: an entry
        differing in `id`, `type`, `source_quote` or a single character of
        `description` is a second obligation, not an echo.
        """
        return bool(self.more_obligations) and self.more_obligations[0] == self.obligation


class _NoObligation(StrictResponseModel):
    """Deliberately yields none. The reason is the disposition's whole content,
    so the shape has nowhere to put obligations."""

    requirement_id: str
    disposition: Literal["no_obligation"]
    reason: str


class _RaisedOpenQuestion(StrictResponseModel):
    """An open question prevents answering. At least one, structurally."""

    requirement_id: str
    disposition: Literal["open_question"]
    open_question_id: str
    more_open_question_ids: list[str]

    def ids(self) -> list[str]:
        return [self.open_question_id, *self.more_open_question_ids]


# A plain union, deliberately not `Field(discriminator=...)`: pydantic renders
# a tagged union as `oneOf` + `discriminator`, and strict mode accepts neither,
# while `inline_schema_refs` would leave the discriminator mapping pointing at
# `$defs` it had just inlined. A plain union renders `anyOf`, which strict mode
# does accept, and the `Literal` tags still make the match unambiguous.
_RequirementDisposition = _Yielded | _NoObligation | _RaisedOpenQuestion


class _Decomposition(StrictResponseModel):
    """No top-level `obligations` list: every obligation reaches us inside the
    disposition that owns it.

    `open_questions` stays flat and referenced by id, deliberately. Two
    requirements really can be blocked by one ambiguity, and the question text
    is about the ambiguity rather than a restatement of either requirement's
    content — so sharing one loses nothing, which is not true of obligations.
    The no-linking rule is about obligations, and it is applied to obligations
    only.
    """

    open_questions: list[_OpenQuestion]
    requirement_dispositions: list[_RequirementDisposition]


class Decomposition(PersistableModel):
    """The result of decomposing a task: typed obligations, the open questions a
    good reviewer would raise rather than resolve, and the mapping back to the
    requirements each came from."""

    obligations: list[Obligation] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    requirement_map: RequirementMap = Field(default_factory=RequirementMap)
    # What this run settled per requirement, ready for the ledger (#269). Held
    # here rather than written from inside `decompose` so that the stage stays a
    # function of its inputs: the caller owns the run id, the parent pointer and
    # the file, and decomposition owns only what it derived.
    derivations: list[RequirementDerivation] = Field(default_factory=list)
    # Requirements the continued run had and this task file does not. Reported
    # rather than silently dropped — a removal that goes unreported is
    # indistinguishable from a requirement that was never there.
    removed_requirements: list[RequirementDerivation] = Field(default_factory=list)
    calls_issued: int = 0
    # Every "are these the same requirement?" answer this run stands on, carried
    # and freshly asked alike. Populated by `link_duplicate_obligations`, which is
    # a later stage — a bare `decompose` leaves it empty, and that is correct:
    # derivation performs no linking (DR-204).
    merge_decisions: list[MergeDecision] = Field(default_factory=list)


def _user_prompt(
    registry: list[RequirementRef],
    answer_for: set[str],
    revisions: dict[str, RequirementDerivation] | None = None,
) -> str:
    """The identified requirements, as typed fields — all of them, every call.

    Deliberately NOT `parsed.source`. The pipeline runs `parse_task_file`, which
    computes typed spans for the behavior, constraints, scope exclusions and
    completion expectations — and the previous version of this function threw
    all of that away and pasted the raw markdown back for the model to re-derive.
    That is the CLAUDE.md structured-interchange invariant: markdown is an input
    format and a rendering format, never an interchange format.

    It is also what makes the disposition list enforceable. Asking for "one entry
    per requirement" only means something if the code and the model agree on what
    the requirements ARE, and that agreement is this list.

    **The batch scopes which requirements this call must answer for; it does not
    scope what the call may read** (#204). The whole registry is the task file in
    its structured form, so every call sees all of it. #178 is a failure to
    reconcile across sections, and a call shown only its own bullets cannot
    notice that a later section settles a term an earlier one leaves open — it
    would trade one silent loss for another.
    """
    lines = [
        "The complete set of requirements in this task file, for context:",
        "",
    ]
    for requirement in registry:
        marker = "ANSWER FOR THIS" if requirement.id in answer_for else "context only"
        lines.append(
            f"[{requirement.id}] ({requirement.section.value}) [{marker}] {requirement.text}"
        )
    lines.extend(
        [
            "",
            "Return exactly one disposition for each of these requirement ids, and for no others:",
            "",
            ", ".join(sorted(answer_for)),
            "",
            (
                "The rest are shown so you can read the mandate as a whole. Do not "
                "dispose of them and do not derive obligations for them; another call "
                "answers for those."
            ),
        ]
    )
    lines.extend(_revision_block(revisions or {}, answer_for))
    return "\n".join(lines)


def _revision_block(
    revisions: dict[str, RequirementDerivation],
    answer_for: set[str],
) -> list[str]:
    """What a requirement used to say, and what it yielded, for the ones that changed.

    **Appended only when this call is answering for a revised requirement**, so a
    run with nothing to carry produces a prompt byte-identical to the one this
    stage produced before carry-forward existed. That is what makes "a tool change
    that leaves the decompose request unaltered carries every previously derived
    obligation" true rather than aspirational: a fresh decomposition hashes to the
    same request key it always did, and every recorded transcript still replays.

    The model is shown the previous wording and what it produced, and asked to
    justify the difference against a real diff. It is never shown its own prior
    answer for bare approval — the input genuinely changed, so there is something
    to reconcile. Reusing an id is offered, not demanded: an obligation that no
    longer follows from the new text should not keep its identifier just because
    one was available.
    """
    applicable = {
        requirement_id: derivation
        for requirement_id, derivation in sorted(revisions.items())
        if requirement_id in answer_for
    }
    if not applicable:
        return []

    lines = [
        "",
        "PREVIOUSLY DERIVED",
        "",
        (
            "These requirements were worded differently in the run this one "
            "continues, and each already produced the obligations listed under it. "
            "Where an obligation below still follows from the NEW wording, reuse its "
            "id so it keeps its identity across the edit. Where the edit changed what "
            "is required, derive what the new wording says and let the old id go — do "
            "not preserve an obligation the new text no longer supports, and do not "
            "reuse an id for something it did not previously mean."
        ),
    ]
    for requirement_id, derivation in applicable.items():
        lines.extend(
            [
                "",
                f"[{requirement_id}] previously read:",
                f"    {derivation.text.strip()}",
            ]
        )
        if derivation.obligations:
            lines.append("  and produced:")
            for obligation in derivation.obligations:
                lines.append(f"    {obligation.id}: {obligation.description}")
        else:
            lines.append(f"  and produced no obligation ({derivation.disposition.value}).")
    return lines


def _importance(value: str) -> str:
    return "critical" if value == "critical" else "normal"


def _decode_obligations(
    entry: _Yielded,
    unusable_answers: UnusableAnswerLog | None,
) -> list[_DecomposedObligation]:
    """What a `yielded` disposition actually yielded.

    `_Yielded` splits the list into a required `obligation` plus
    `more_obligations` because strict mode rejects `minItems`, and that split is
    the only way to make "at least one" a property of the SHAPE rather than a
    rule the model is asked to follow (#217). The cost is an ambiguity: the two
    fields carry no stated relationship and the prompt never names them, so in
    the ONE-obligation case the model may fill the required slot and then emit
    the same object again as the whole list. That is a defensible reading of
    what it was handed, not a faulty answer — and `_unique` then turns the echo
    into a second obligation with a `-2` suffix (#248).

    Measured over all 1,055 recorded transcripts at the time of writing: four
    duplicate-bearing dispositions, every one of them a byte-identical head
    versus `more_obligations[0]` with exactly one entry in the remainder, and
    zero duplicates anywhere else. Requirements yielding two and three
    obligations in the same response used the split correctly.

    So `more_obligations` is read as THE REST, and an echo at its head is the
    same obligation rather than a second one.

    **Position 0 only, deliberately.** An identical entry further down would be
    the model genuinely restating itself, which is the linking stage's call. A
    guard that dropped repeats anywhere would also destroy the signal that
    something upstream is wrong — and the whole premise here is that suppressing
    a finding is worse than reporting one that turns out to be benign.

    Head+rest is the only structural non-empty encoding available, so no schema
    edit can remove this case; #256 queues a field rename and a prompt sentence
    to make it rarer, and this guard stays load-bearing when that lands.
    """
    if not entry.echoes_head():
        return entry.derived()

    if unusable_answers is not None:
        unusable_answers.record(
            [
                UnusableAnswer(
                    stage=_STAGE,
                    field="more_obligations",
                    returned_id=entry.obligation.id,
                    reason=(
                        "more_obligations[0] repeats the required 'obligation' field "
                        f"exactly, for requirement '{entry.requirement_id}'; read as a "
                        "single-obligation answer. The head/rest encoding of a non-empty "
                        "list does not distinguish the two, so this is the response's "
                        "shape rather than an unusable answer"
                    ),
                )
            ]
        )

    # The head survives, so a requirement that yielded can never be emptied here.
    return [entry.obligation, *entry.more_obligations[1:]]


@dataclass(frozen=True)
class _Attribution:
    """One derived obligation, the requirement that carried it, and the
    requirement its quotation actually lands in.

    Attribution cannot be settled inside the batch loop: an obligation may quote
    a requirement another batch answers for, and whether that requirement was
    disposed `yielded` is not known until every batch has returned.
    """

    attributed_to: str
    owner_id: str | None
    obligation: Obligation


def _resolve_attributions(
    attributions: list[_Attribution],
    dispositions: list[_RequirementDisposition],
    unusable_answers: UnusableAnswerLog | None,
) -> tuple[list[Obligation], dict[str, list[str]]]:
    """File each obligation under the requirement its quotation lands in.

    - The quotation is inside the requirement that carried it — file it there,
      which is every correctly attributed obligation and the overwhelming
      majority.
    - It is inside a different requirement that also yielded — re-file it there,
      content untouched. The duplicate this creates when both requirements
      derived the same obligation is an ordinary two-on-one case the linking
      stage already merges, rather than the cross-requirement contradiction it
      could not reconcile and reported as unreconciled (#244).
    - Otherwise — keep it where it was attributed. See `emptied` below for why
      moving is not always safe.

    **No obligation is ever discarded here.** Losing a requirement is the
    failure this project treats as worst (#202, #214), and a decomposer that
    quotes badly is not evidence that the obligation it derived is unreal. Every
    disagreement between quotation and attribution is instead recorded on the
    `UnusableAnswerLog`, whether it was acted on or not, so a re-filing is
    visible and a discrepancy that could not be acted on does not become silent.
    """
    yielded = {entry.requirement_id for entry in dispositions if isinstance(entry, _Yielded)}

    def _movable(attribution: _Attribution) -> bool:
        owner_id = attribution.owner_id
        if owner_id is None or owner_id == attribution.attributed_to:
            return False
        # Only onto a requirement that also yielded. Filing under one the
        # response deliberately declined would contradict that decline, and
        # `_requirement_map` never reads `derived_ids` for a declined
        # requirement, so the obligation would end up linked to nothing.
        return owner_id in yielded

    carried: dict[str, list[_Attribution]] = {}
    for attribution in attributions:
        carried.setdefault(attribution.attributed_to, []).append(attribution)

    # A requirement whose obligations would ALL move keeps them. Its disposition
    # is an explicit claim that it yielded, and a `_Yielded` requirement left
    # carrying nothing raises out of `_requirement_map` — so moving the last one
    # would turn a mild quoting slip into a failed review. That slip is common,
    # because requirements restate each other: a completion expectation quoting
    # the constraint it demands a test for is the DR-204 shape, and is far more
    # likely than a decomposer that read some other requirement entirely. Where
    # quotation and disposition disagree and the disposition would otherwise be
    # falsified, the disposition is the stronger evidence; the quotation only
    # corroborates it.
    emptied = {
        requirement_id
        for requirement_id, group in carried.items()
        if all(_movable(attribution) for attribution in group)
    }

    obligations: list[Obligation] = []
    derived_ids: dict[str, list[str]] = {}
    discrepancies: list[UnusableAnswer] = []

    for attribution in attributions:
        obligation = attribution.obligation
        filed_under = attribution.attributed_to

        if _movable(attribution) and attribution.attributed_to not in emptied:
            filed_under = attribution.owner_id or filed_under
            discrepancies.append(
                UnusableAnswer(
                    stage=_STAGE,
                    field="source_quote",
                    returned_id=obligation.id,
                    reason=(
                        f"attributed to '{attribution.attributed_to}' but its quotation "
                        f"is inside requirement '{filed_under}'; re-filed there"
                    ),
                )
            )
        elif attribution.owner_id != attribution.attributed_to:
            discrepancies.append(
                UnusableAnswer(
                    stage=_STAGE,
                    field="source_quote",
                    returned_id=obligation.id,
                    reason=(
                        f"attributed to '{attribution.attributed_to}' but its quotation "
                        f"is not inside it; kept there, having nowhere to be re-filed"
                    ),
                )
            )

        obligations.append(obligation)
        derived_ids.setdefault(filed_under, []).append(obligation.id)

    if unusable_answers is not None:
        unusable_answers.record(discrepancies)
    return obligations, derived_ids


def decompose_carry_keys(client: ModelClient, registry: list[RequirementRef]) -> dict[str, str]:
    """The key each requirement's derivation would be valid under, this run.

    The response schema here is the UNCONSTRAINED `_Decomposition`, deliberately.
    The real request constrains `requirement_id` to the batch's ids, so the schema
    inside a request key depends on how the run happened to be partitioned — and a
    carry key that moved when the batch size changed would discard work for a
    reason that has nothing to do with whether the answer is still right.
    """
    schema = {
        "name": _Decomposition.__name__,
        "schema": inline_schema_refs(_Decomposition.model_json_schema()),
    }
    return {
        requirement.id: carry_key(
            system_prompt=_SYSTEM_PROMPT,
            response_schema=schema,
            model=client.model,
            temperature=client.temperature,
            seed=client.seed,
            stage_logic_version=DECOMPOSE_STAGE_LOGIC_VERSION,
            requirement_text=requirement.text,
        )
        for requirement in registry
    }


def decompose(
    parsed: ParsedTaskFile,
    client: ModelClient,
    unusable_answers: UnusableAnswerLog | None = None,
    batch_size: int = DEFAULT_DECOMPOSE_BATCH_SIZE,
    prior: LedgerEntry | None = None,
) -> Decomposition:
    """Decompose a parsed task into typed obligations, open questions, and the
    mapping from each identified requirement to what it produced.

    Takes a parsed task file and a client, and nothing else — no `ChangeSet`, no
    repository, no head revision (DR-202 decision 8).

    The requirements are partitioned across several calls (#204). One call over
    the whole registry sheds work the way DR-164 measured a stage later: an
    observed run over ~36 requirements produced no obligation for 9 of them,
    with a schema-valid response that nothing downstream could question. Every
    call still reads the whole task file; only the answering is split.
    """
    registry = build_registry(parsed)
    # No requirements, no calls. `partition` returns no batches for an empty
    # registry and the loop below simply does not run — spelled out because the
    # previous single-call shape issued one request regardless, asking the model
    # to decompose an empty requirement list. What came back could only be
    # invented, since the prompt carried no task content at all.
    #
    # `tests/fixtures/archetypes/` used to reach here that way: every task.md
    # headed its mandate `# Task: <title>`, which is not the `task` heading the
    # parser recognises, so all thirteen produced an empty registry and were
    # scored anyway. `1c53592` reshaped the corpus and #228 added the guard —
    # `benchmark/case.py::require_nonempty_registry` — so a case that yields no
    # requirements now fails at construction instead of arriving here. Returning
    # nothing over nothing is still the right behaviour for this stage; it is
    # just no longer how the benchmark reaches it.

    seen_ids: set[str] = set()
    open_questions: list[OpenQuestion] = []
    dispositions: list[_RequirementDisposition] = []
    # Every derived obligation with the requirement that carried it and the one
    # its quotation lands in. Resolved into the obligation list and the
    # requirement -> obligation-ids map by `_resolve_attributions` once all the
    # batches are in, because re-filing an obligation onto another requirement
    # depends on how THAT requirement was disposed, which a later batch may
    # still be answering.
    #
    # `_unique` still runs as the obligations are built, because two
    # requirements may independently mint the same slug — but a rename can no
    # longer mis-resolve anyone else's disposition, since nobody else names it.
    attributions: list[_Attribution] = []
    # Open questions stay flat and referenced by id (see `_Decomposition`), so
    # they still need per-batch resolution: each response mints its own ids.
    question_final: dict[str, dict[str, str]] = {}

    # What this run may take from the run it continues. With no prior it plans
    # every requirement as `derived`, and everything below runs exactly as it did
    # before carry-forward existed.
    plan = plan_carry(registry, prior, decompose_carry_keys(client, registry), client)
    to_ask = plan.issues_calls_for
    asking = [requirement for requirement in registry if requirement.id in to_ask]
    calls_issued = 0

    for batch in partition(asking, batch_size, key=lambda requirement: requirement.id):
        batch_ids = [requirement.id for requirement in batch.items]
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                # The registry passed here is the WHOLE one, never `asking`: the
                # batch scopes what a call answers for, not what it may read
                # (#178). A call shown only the requirements that changed could
                # not notice that an untouched section settles a term the
                # changed one leaves open.
                "content": _user_prompt(registry, set(batch_ids), plan.revised),
            },
        ]
        calls_issued += 1
        # Constrained to THIS batch's ids, not the whole registry: a disposition
        # for a requirement another call owns is unrepresentable under
        # constrained decoding, and caught locally otherwise (#163). Obligation
        # and question ids are minted by the same response, so there is nothing
        # to constrain them against; they are reconciled below.
        allowed = {"requirement_id": batch_ids}
        result = client.complete(
            messages,
            constrain(_Decomposition, allowed),
            batch.request_partition(),
            parse_as=_Decomposition,
            stage=_STAGE,
        )
        if unusable_answers is not None:
            unusable_answers.record(scan(result, allowed, _STAGE))

        kept = _batch_dispositions(
            result.requirement_dispositions,
            set(batch_ids),
            {requirement.id for requirement in registry},
            unusable_answers,
        )
        dispositions.extend(kept)

        # Obligations are lifted out of their dispositions in registry order, so
        # the flat list downstream reads in document order and two runs over the
        # same input produce it identically.
        # Whether an obligation is satisfied by work NOT done is decided from
        # the parse, never from the model's answer. The section a requirement
        # was parsed out of is already known here (`RequirementRef.section`), so
        # an obligation derived from `## Scope exclusions` is marked
        # structurally — the same move #232 made for TEST_DEMAND and #219 for
        # sibling dispositions, both of which failed while they depended on the
        # model restating a distinction it had already been told.
        #
        # Which KINDS OF EVIDENCE it requires is a different question and the
        # model does answer it (#266). The two were one field until a scope
        # exclusion excluding a change to BEHAVIOR turned out to want a
        # regression test, which the structural rule could never express. What
        # the heading still settles beyond argument is the absence, and that is
        # all it now settles.
        exclusion_ids = {
            requirement.id
            for requirement in registry
            if requirement.section is RequirementSection.EXCLUSION
        }

        for entry in kept:
            if not isinstance(entry, _Yielded):
                continue
            for item in _decode_obligations(entry, unusable_answers):
                # Which requirement an obligation belongs to is decided by where
                # its quotation lands, not by which disposition carried it. The
                # section that decides `satisfied_by_absence` then comes from
                # the OWNING requirement — an obligation re-attributed into a
                # scope exclusion is satisfied by an absence, exactly as one
                # derived there directly would be (#153).
                span, owner = _locate_quotation(
                    registry, parsed.source, item.source_quote, entry.requirement_id
                )
                section_id = owner.id if owner is not None else entry.requirement_id
                by_absence = section_id in exclusion_ids
                # A narrowing with no reason behind it is discarded. The reason
                # is the only thing that makes "less evidence is owed here"
                # auditable, so an unreasoned narrowing is indistinguishable
                # from the question being skipped — and the safe reading of a
                # skipped question is that every kind of evidence is still owed.
                required = item.required_evidence
                reason = item.required_evidence_reason.strip()
                if required is not RequiredEvidence.CODE_AND_TESTS and not reason:
                    required = RequiredEvidence.CODE_AND_TESTS
                if required is RequiredEvidence.CODE_AND_TESTS:
                    reason = ""
                # Ids are minted here, in the order they always were, so an
                # obligation that was attributed correctly keeps the id it had
                # before this check existed. Only which requirement claims it —
                # settled below, once every disposition is known — can change.
                final_id = _unique(item.id, seen_ids)
                attributions.append(
                    _Attribution(
                        attributed_to=entry.requirement_id,
                        owner_id=owner.id if owner is not None else None,
                        obligation=Obligation(
                            id=final_id,
                            description=item.description,
                            type=item.type,
                            importance=_importance(item.importance),
                            explicit=item.explicit,
                            observable_behavior=item.observable_behavior,
                            source_spans=[span] if span is not None else [],
                            required_evidence=required,
                            required_evidence_reason=reason,
                            satisfied_by_absence=by_absence,
                        ),
                    )
                )

        # After the obligations, deliberately: ids are uniqued across both, and
        # an obligation and a question minting the same slug must resolve the
        # same way they did before this stage was partitioned.
        batch_question_final: dict[str, str] = {}
        for item in result.open_questions:
            final_id = _unique(item.id, seen_ids)
            batch_question_final.setdefault(item.id, final_id)
            open_questions.append(
                OpenQuestion(
                    id=final_id,
                    question=item.question,
                    importance=_importance(item.importance),
                    source_spans=_spans(parsed.source, item.source_quote),
                )
            )
        for requirement_id in batch_ids:
            question_final[requirement_id] = batch_question_final

    obligations, derived_ids = _resolve_attributions(attributions, dispositions, unusable_answers)

    carried_dispositions = {
        requirement_id: _carried_disposition(requirement_id, source)
        for requirement_id, source in plan.carried.items()
    }
    requirement_map = _requirement_map(
        registry,
        dispositions,
        derived_ids,
        question_final,
        parsed.unclaimed,
        carried_dispositions,
    )
    # A revised requirement's disposition is built by the ordinary path, because
    # it WAS asked of the model — so without this it would report itself as
    # `derived` and carry no reason, which is the same thing a genuinely fresh
    # requirement reports. The two are different: one had a predecessor and was
    # re-asked against it, and losing that distinction loses the only record that
    # an identifier could have been reused and was not.
    requirement_map = _stamp_revisions(requirement_map, plan)

    if not plan.is_fresh():
        # Rebuild both flat lists by walking the map, so a carried obligation
        # sits where its requirement sits rather than after everything asked for
        # in this run. Only on a carrying run: with nothing carried, the lists
        # the call loop already built are returned untouched, which keeps a fresh
        # decomposition byte-for-byte what it was before this existed.
        obligations, open_questions = _in_registry_order(
            requirement_map, obligations, open_questions, plan
        )

    return Decomposition(
        obligations=obligations,
        open_questions=open_questions,
        requirement_map=requirement_map,
        derivations=_derivations(registry, requirement_map, plan, obligations, open_questions),
        removed_requirements=list(plan.removed),
        calls_issued=calls_issued,
    )


def _revision_reason(source: RequirementDerivation) -> str:
    """Why a requirement was re-asked: the wording it used to have.

    One definition, used by both the disposition and the ledger record, so the two
    cannot drift into disagreeing about the same event.
    """
    return f"requirement text changed from: {source.text.strip()}"


def _stamp_revisions(requirement_map: RequirementMap, plan: CarryPlan) -> RequirementMap:
    """Mark the dispositions of requirements this run re-asked against a predecessor."""
    if not plan.revised:
        return requirement_map
    stamped = [
        disposition.model_copy(
            update={
                "derivation": Derivation.REVISED.value,
                "carried_from": plan.revised[disposition.requirement_id].digest(),
                "revision_reason": _revision_reason(plan.revised[disposition.requirement_id]),
            }
        )
        if disposition.requirement_id in plan.revised
        else disposition
        for disposition in requirement_map.dispositions
    ]
    return requirement_map.model_copy(update={"dispositions": stamped})


def _carried_disposition(
    requirement_id: str, source: RequirementDerivation
) -> RequirementDisposition:
    """The disposition a carried requirement keeps.

    Rebuilt rather than copied so it is checked by the same validator every other
    disposition passes — a carried `yielded` that names no obligation is as broken
    as a derived one, and this is where that would surface.
    """
    return RequirementDisposition(
        requirement_id=requirement_id,
        disposition=source.disposition,
        obligation_ids=[obligation.id for obligation in source.obligations],
        open_question_ids=[question.id for question in source.open_questions],
        reason=source.reason,
        derivation=Derivation.CARRIED.value,
        carried_from=source.digest(),
    )


def _in_registry_order(
    requirement_map: RequirementMap,
    obligations: list[Obligation],
    open_questions: list[OpenQuestion],
    plan: CarryPlan,
) -> tuple[list[Obligation], list[OpenQuestion]]:
    """The obligations and questions of every requirement, in registry order."""
    by_obligation = {obligation.id: obligation for obligation in obligations}
    by_question = {question.id: question for question in open_questions}
    for source in plan.carried.values():
        for obligation in source.obligations:
            by_obligation[obligation.id] = obligation
        for question in source.open_questions:
            by_question[question.id] = question

    ordered_obligations: list[Obligation] = []
    ordered_questions: list[OpenQuestion] = []
    seen: set[str] = set()
    for disposition in requirement_map.dispositions:
        for obligation_id in disposition.obligation_ids:
            if obligation_id in by_obligation and obligation_id not in seen:
                seen.add(obligation_id)
                ordered_obligations.append(by_obligation[obligation_id])
        for question_id in disposition.open_question_ids:
            if question_id in by_question and question_id not in seen:
                seen.add(question_id)
                ordered_questions.append(by_question[question_id])
    return ordered_obligations, ordered_questions


def _derivations(
    registry: list[RequirementRef],
    requirement_map: RequirementMap,
    plan: CarryPlan,
    obligations: list[Obligation],
    open_questions: list[OpenQuestion],
) -> list[RequirementDerivation]:
    """One ledger record per requirement, in registry order.

    Written for every requirement, not only the ones that changed: the ledger is
    what the NEXT run reads to decide what it may carry, so a requirement this run
    merely carried must still appear, holding the same obligations. A ledger that
    recorded only the derivations would carry work forward exactly once.
    """
    by_obligation = {obligation.id: obligation for obligation in obligations}
    by_question = {question.id: question for question in open_questions}
    records: list[RequirementDerivation] = []
    for requirement in registry:
        disposition = requirement_map.disposition_for(requirement.id)
        if disposition is None:  # pragma: no cover - _requirement_map raises first
            continue
        kind = derivation_kind(plan, requirement.id)
        source = plan.carried.get(requirement.id) or plan.revised.get(requirement.id)
        records.append(
            RequirementDerivation(
                requirement_id=requirement.id,
                text=requirement.text,
                carry_key=plan.keys[requirement.id],
                derivation=kind,
                disposition=disposition.disposition,
                reason=disposition.reason,
                carried_from=source.digest() if source is not None else None,
                revision_reason=(
                    _revision_reason(source)
                    if kind is Derivation.REVISED and source is not None
                    else None
                ),
                obligations=[
                    by_obligation[obligation_id]
                    for obligation_id in disposition.obligation_ids
                    if obligation_id in by_obligation
                ],
                open_questions=[
                    by_question[question_id]
                    for question_id in disposition.open_question_ids
                    if question_id in by_question
                ],
            )
        )
    return records


def build_ledger_entry(
    derived: Decomposition,
    run_id: str,
    parent_run_id: str | None,
    task_digest: str,
    linked: Decomposition | None = None,
) -> LedgerEntry:
    """This run's ledger record, ready to write.

    Two inputs, deliberately. The **derivations** come from `derived`, before
    linking: what a later run carries forward per requirement is what this stage
    derived, and recording the post-merge set would let one run's merge silently
    become the next run's premise (DR-204). The **merge decisions** come from
    `linked`, because that is the stage that made them.
    """
    return LedgerEntry(
        run_id=run_id,
        parent_run_id=parent_run_id,
        stage_logic_version=DECOMPOSE_STAGE_LOGIC_VERSION,
        task_digest=task_digest,
        calls_issued=derived.calls_issued,
        derivations=list(derived.derivations),
        merge_decisions=list((linked or derived).merge_decisions),
    )


def _batch_dispositions(
    returned: list[_RequirementDisposition],
    batch_ids: set[str],
    registry_ids: set[str],
    unusable_answers: UnusableAnswerLog | None,
) -> list[_RequirementDisposition]:
    """One batch's usable dispositions.

    **A batch may only answer for its own requirements.** A disposition naming a
    requirement this call was not given is recorded and dropped rather than
    silently filtered — the requirement belongs to another batch, which answers
    for it, and letting this one through would make the merged result depend on
    which batch returned last.

    There is no no-linking check here, and deliberately none anywhere: since the
    obligations are carried inside the disposition that derived them, one
    obligation cannot be named by two requirements. The rule is a property of
    the shape, not a rejection applied afterwards (DR-204, amended). An earlier
    version validated it post-response and had to drop BOTH claimants, which
    left the mandate unaccounted for and aborted the review — on an ordinary
    task file that merely restated a requirement across two sections.
    """
    rejected: list[UnusableAnswer] = []
    usable: list[_RequirementDisposition] = []
    seen: dict[str, _RequirementDisposition] = {}

    for entry in returned:
        # An EXACT repeat of a disposition already returned in this response is
        # dropped, not rejected. It carries no information the first copy did
        # not, and a response that repeats itself verbatim is a degenerate
        # generation rather than a contradiction — observed once the obligations
        # moved inside the dispositions and responses grew: the model emitted
        # its whole disposition list twice.
        #
        # A duplicate that DIFFERS is still a contradiction and still reaches
        # `_requirement_map`, which refuses it: two different answers for one
        # requirement is exactly the self-contradiction M1.2.r2 exists to catch.
        previous = seen.get(entry.requirement_id)
        if previous is not None and previous == entry:
            continue
        # An id outside the registry ENTIRELY is passed through, not filtered
        # here: it is a malformed response rather than a batch overstepping, and
        # `_requirement_map` already refuses it by name. Filtering it here would
        # convert a loud, specific rejection into a vague "did not account for"
        # about some other requirement.
        if entry.requirement_id in registry_ids and entry.requirement_id not in batch_ids:
            rejected.append(
                UnusableAnswer(
                    stage=_STAGE,
                    field="requirement_id",
                    returned_id=entry.requirement_id,
                    reason="disposed a requirement this call was not asked to answer for",
                )
            )
            continue
        seen.setdefault(entry.requirement_id, entry)
        usable.append(entry)

    if rejected and unusable_answers is not None:
        unusable_answers.record(rejected)
    return usable


def _requirement_map(
    registry: list[RequirementRef],
    returned: list[_RequirementDisposition],
    derived_ids: dict[str, list[str]],
    question_final: dict[str, dict[str, str]],
    unread: list,
    carried: dict[str, RequirementDisposition] | None = None,
) -> RequirementMap:
    """Reconcile the returned dispositions against the registry.

    The registry is derived deterministically from the parse and this loop walks
    it, so **dropping a requirement is not a reachable outcome** — the worst a
    model can do is answer badly. That is why there is no fourth disposition
    here. `M1.2.r1` added one, `UNDISPOSED`, for a requirement the response
    failed to account for, and it turned two kinds of malformed response into a
    soft finding that flowed on to a verdict. A response that does not account
    for the mandate is not a review with a gap in it; it is not a review.

    So every disagreement between the registry and the response raises. What
    survives is a map in which every requirement carries one of decision 3's
    three dispositions, each holding what its name claims.
    """
    by_requirement: dict[str, _RequirementDisposition] = {}
    for entry in returned:
        if entry.requirement_id in by_requirement:
            raise SchemaValidationError(
                f"requirement '{entry.requirement_id}' was disposed more than once"
            )
        by_requirement[entry.requirement_id] = entry

    known = {requirement.id for requirement in registry}
    unknown = sorted(set(by_requirement) - known)
    if unknown:
        raise SchemaValidationError(
            f"response disposed requirement ids not in the registry: {', '.join(unknown)}"
        )
    # A carried requirement was not asked about in this run, so no response
    # accounts for it — and it must still be accounted for, because a registry
    # requirement with no disposition is the malformed-response case this
    # function exists to reject. Carrying is the one way a disposition arrives
    # without a call behind it, and it is checked here rather than trusted: an
    # id carried for a requirement the registry does not have is caught by the
    # same rule as one the model invented.
    carried = carried or {}
    carried_unknown = sorted(set(carried) - known)
    if carried_unknown:
        raise SchemaValidationError(
            f"carried dispositions for requirement ids not in the registry: "
            f"{', '.join(carried_unknown)}"
        )
    both = sorted(set(carried) & set(by_requirement))
    if both:
        raise SchemaValidationError(
            f"requirement(s) both carried and disposed by a response: {', '.join(both)}"
        )
    missing = [
        requirement.id
        for requirement in registry
        if requirement.id not in by_requirement and requirement.id not in carried
    ]
    if missing:
        raise SchemaValidationError(
            f"response did not account for {len(missing)} of {len(registry)} "
            f"requirements: {', '.join(missing)}"
        )

    dispositions: list[RequirementDisposition] = []
    for requirement in registry:
        if requirement.id in carried:
            dispositions.append(carried[requirement.id])
            continue
        entry = by_requirement[requirement.id]

        if isinstance(entry, _NoObligation):
            dispositions.append(
                RequirementDisposition(
                    requirement_id=requirement.id,
                    disposition=Disposition.NO_OBLIGATION,
                    reason=entry.reason,
                )
            )
            continue

        # No reconciliation, and no dangling-reference case to handle: the
        # obligations arrived inside this disposition, so `derived_ids` holds
        # exactly what it carried. `_Yielded` requires at least one
        # structurally, so the empty case is unrepresentable rather than
        # rejected here (#217).
        if isinstance(entry, _Yielded):
            obligation_ids = derived_ids.get(requirement.id, [])
            if not obligation_ids:
                raise SchemaValidationError(
                    f"requirement '{requirement.id}' was disposed 'yielded' but carried "
                    f"no obligation"
                )
            dispositions.append(
                RequirementDisposition(
                    requirement_id=requirement.id,
                    disposition=Disposition.YIELDED,
                    obligation_ids=obligation_ids,
                )
            )
            continue

        open_question_ids = _resolve(entry.ids(), question_final.get(requirement.id, {}))
        if not open_question_ids:
            raise SchemaValidationError(
                f"requirement '{requirement.id}' was disposed 'open_question' naming "
                f"{len(entry.ids())} question id(s), none of which the response produced"
            )
        dispositions.append(
            RequirementDisposition(
                requirement_id=requirement.id,
                disposition=Disposition.OPEN_QUESTION,
                open_question_ids=open_question_ids,
            )
        )

    return RequirementMap(requirements=registry, dispositions=dispositions, unread_source=unread)


def _resolve(ids: list[str], final: dict[str, str]) -> list[str]:
    """Returned output ids mapped to the ids those outputs actually carry,
    de-duplicated, in first-seen order (byte-identical reruns depend on it)."""
    resolved: dict[str, None] = {}
    for value in ids:
        actual = final.get(value)
        if actual is not None:
            resolved.setdefault(actual, None)
    return list(resolved)


def _spans(source: str, quote: str) -> list:
    span = find_span(source, quote)
    return [span] if span is not None else []


def _locate_quotation(
    registry: list[RequirementRef],
    source: str,
    quote: str,
    attributed_to: str,
) -> tuple[TextSpan | None, RequirementRef | None]:
    """Locate `quote` and name the requirement it lands in.

    The attribution check the prompt cannot make. `_user_prompt` shows every call
    the whole registry and asks it not to derive obligations for the requirements
    another call owns; nothing enforced that, and the quote was resolved against
    `parsed.source` — the whole file — so an obligation filed under one
    requirement while quoting another's text produced a valid span and was
    accepted. Misattribution was undetectable by construction (#244).

    **The requirement it was attributed to is searched first, and that is
    load-bearing, not an optimisation.** `find_span` returns the FIRST occurrence
    in the file, and requirements restate each other constantly — a completion
    expectation is usually a rephrasing of the constraint it demands a test for.
    Resolving globally would let an earlier identical string steal a quotation
    from the requirement it truly belongs to, turning correct attribution into a
    spurious re-filing. Searching the attributed requirement first means an
    obligation is only ever re-filed when its quotation does not appear in its
    own requirement at all.
    """
    if not quote:
        return None, None

    # Whitespace-insensitive, and that is load-bearing rather than lenient. Task
    # prose is hard-wrapped and bullets usually are not, so the SAME sentence
    # appears as "...naming every\ncolumn." in one requirement and "...naming
    # every column." in another. An exact-substring test then reports the quote
    # as belonging to whichever one happens not to be wrapped, and re-files a
    # correctly attributed obligation on the strength of a line break. Observed
    # on `tests/prompts/test_linking_prompt.py`'s corpus, where it moved the
    # Task prose's obligation onto the constraint that restates it — deleting
    # the cross-section duplicate that corpus exists to exercise.
    words = quote.split()
    if not words:
        return None, None
    pattern = re.compile(r"\s+".join(re.escape(word) for word in words))

    def _within(requirement: RequirementRef) -> TextSpan | None:
        found = pattern.search(requirement.span.text)
        if found is None:
            return None
        start = requirement.span.start + found.start()
        return TextSpan(
            text=requirement.span.text[found.start() : found.end()],
            start=start,
            end=start + (found.end() - found.start()),
        )

    by_id = {requirement.id: requirement for requirement in registry}
    attributed = by_id.get(attributed_to)
    if attributed is not None:
        span = _within(attributed)
        if span is not None:
            return span, attributed

    for requirement in registry:
        span = _within(requirement)
        if span is not None:
            return span, requirement

    # Inside no requirement. The span is still reported when the quote exists
    # somewhere in the file, so a rejected obligation can be traced back to the
    # text that produced it.
    return find_span(source, quote), None


def _unique(candidate: str, seen: set[str]) -> str:
    """Keep ids unique and deterministic across obligations and open questions."""
    unique_id = candidate
    suffix = 2
    while unique_id in seen:
        unique_id = f"{candidate}-{suffix}"
        suffix += 1
    seen.add(unique_id)
    return unique_id
