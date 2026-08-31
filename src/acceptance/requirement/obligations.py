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

from typing import Literal

from pydantic import Field

from acceptance.concurrency import map_calls
from acceptance.llm import (
    ModelClient,
    SchemaValidationError,
    StrictResponseModel,
    inline_schema_refs,
)
from acceptance.model_base import PersistableModel
from acceptance.partition import partition
from acceptance.request_blocks import Block, BlockKind, assemble
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
from acceptance.requirement.spans import locate_within, normalise, quotable_spans
from acceptance.requirement.summary import (
    SUMMARY_STAGE,
    SpanDecision,
    coverage_reason,
    decide_spans,
)
from acceptance.requirement.task_file import ParsedTaskFile
from acceptance.review_state import (
    DefectSet,
    Disposition,
    Obligation,
    ObligationType,
    OpenQuestion,
    PairVerdict,
    RequiredEvidence,
    RequirementDisposition,
    RequirementMap,
    RequirementRef,
    RequirementSection,
)
from acceptance.source_ref import find_span
from acceptance.supplied_ids import (
    UnusableAnswer,
    UnusableAnswerLog,
    constrain,
    scan,
)

_STAGE = "decompose"

# One requirement per call (#317). Not configurable: it is what makes
# `source_quote` expressible as an enum of the answering requirement's own spans,
# so raising it would not merely cost accuracy — it would remove the guarantee.
# It is still routed through `partition`, so the request carries the descriptor
# and a recording made under batching does not replay as though nothing moved.
ONE_REQUIREMENT_PER_CALL = 1

_SYSTEM_PROMPT = """\
You decompose a software task into discrete, typed acceptance obligations and
the ambiguities that need human judgment.

For each obligation: a short stable `id` slug (kebab-case, unique); a
`description`; a `type` from the fixed set (functional, boundary,
error_handling, invariant, regression, compatibility,
explanation_observability, docs_config, human_review, test_demand — see THE
`test_demand` TYPE below); `importance` (critical
or normal); `explicit` (true if directly stated in the task, false if
reasonably inferred); an `observable_behavior`; and `source_quote`, chosen from
the quotations the schema offers for the requirement you were asked about. They
are that requirement's own text, and they are the only quotations you may give.

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

ACCOUNTING FOR THE ONE REQUIREMENT YOU WERE ASKED ABOUT

You are given the task file's requirements as an identified list, and you are
asked about EXACTLY ONE of them. Return `requirement_disposition` — a single
entry, for that one requirement, including when you find it unremarkable.

Every other requirement is shown so that you can read the mandate as a whole.
Another call answers for each of those, so an obligation about one of them is
not yours to give — and the quotations offered to you are this requirement's
own, so you could not source one if it were.

The disposition is one of:

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

The obligations are carried INSIDE the disposition, so every obligation belongs
to the one requirement you were asked about. Account for it on its own: split it
into several obligations, or decline it with `no_obligation`.

When another requirement states the same thing as this one — commonly one bullet
under Constraints and another under Completion expectations — still give this
requirement its own obligation, written out in full. Two obligations saying
nearly the same thing is the correct output here; a later pass merges them. Do
not decline or narrow this requirement because another one covers it.

A behavior and a demand for a TEST of that behavior are NOT the same thing,
even when the Constraints bullet and the Completion bullet are worded almost
identically. Keep the test framing on the requirement that has it, per THE
`test_demand` TYPE above. The later pass is told these two do not merge, and it
can only see that if you left the framing in."""


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

    **One disposition, not a list of them** (#317). A call is asked about one
    requirement, so "exactly one account of it" is a property of the shape rather
    than a rule the prompt asks for and reconciliation checks afterwards. The
    list form is what let a call answering for three requirements return
    fourteen entries, eleven of them about the Constraints section it had merely
    been shown; a single field makes that answer unsayable, and it also retires
    the repeated-disposition abort that turned one such response into a failed
    review.

    `open_questions` stays flat and referenced by id, deliberately. Two
    requirements really can be blocked by one ambiguity, and the question text
    is about the ambiguity rather than a restatement of either requirement's
    content — so sharing one loses nothing, which is not true of obligations.
    The no-linking rule is about obligations, and it is applied to obligations
    only.
    """

    open_questions: list[_OpenQuestion]
    requirement_disposition: _RequirementDisposition


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
    answer_for: str,
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

    **`answer_for` scopes which requirement this call must answer for; it does
    not scope what the call may read** (#204). The whole registry is the task
    file in its structured form, so every call sees all of it. #178 is a failure
    to reconcile across sections, and a call shown only its own bullet cannot
    notice that a later section settles a term an earlier one leaves open — it
    would trade one silent loss for another.

    Showing a requirement is not asking about it, and the distinction is
    measured rather than assumed: over the recorded corpus, 0 of 68 calls with no
    `task-*` requirement in their ANSWERING set derived an obligation for a
    requirement they had only been shown
    (`docs/experiments/317-over-answering/findings.md` §2).
    """
    lines = [
        "The complete set of requirements in this task file, for context:",
        "",
    ]
    for requirement in registry:
        marker = "ANSWER FOR THIS" if requirement.id == answer_for else "context only"
        lines.append(
            f"[{requirement.id}] ({requirement.section.value}) [{marker}] {requirement.text}"
        )
    lines.extend(
        [
            "",
            "Return one disposition, for this requirement id and no other:",
            "",
            answer_for,
            "",
            (
                "The rest are shown so you can read the mandate as a whole. Do not "
                "dispose of them and do not derive obligations for them; another call "
                "answers for those."
            ),
        ]
    )
    lines.extend(_revision_block(revisions or {}, {answer_for}))
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


def _obligations_from(
    entry: _Yielded,
    requirement: RequirementRef,
    seen_ids: set[str],
    unusable_answers: UnusableAnswerLog | None,
    quote_override: str | None = None,
) -> list[Obligation]:
    """The obligations one `yielded` disposition produced, filed under its own
    requirement and nowhere else.

    **There is no attribution step any more.** The retired `_resolve_attributions`
    existed because a call answered for several requirements and could quote any
    of them, so where an obligation belonged had to be worked out afterwards from
    where its quotation landed — and an obligation quoting a requirement another
    batch owned was re-filed onto it, manufacturing a duplicate of work that
    batch had already done properly. A call now answers for one requirement and
    can only quote that requirement's own spans, so the question is settled by
    construction (`docs/experiments/317-over-answering/findings.md` §9).

    A quotation that is nonetheless not inside the requirement — a provider that
    ignored the enum — is recorded and the obligation kept without a source span.
    Dropping it would lose a requirement, which is the failure this project
    treats as worst; moving it is what has just been retired.

    `quote_override` is set by the caller for an obligation derived from a span
    of the opening summary, where the quotation is the span itself and is taken
    from the mandate rather than from the answer that named it.
    """
    produced: list[Obligation] = []
    for item in _decode_obligations(entry, unusable_answers):
        quote = quote_override if quote_override is not None else item.source_quote
        span = locate_within(requirement, quote)
        if span is None and unusable_answers is not None:
            unusable_answers.record(
                [
                    UnusableAnswer(
                        stage=_STAGE,
                        field="source_quote",
                        returned_id=item.id,
                        reason=(
                            f"quotation is not inside requirement '{requirement.id}', "
                            f"which is the only text this call was offered: {quote!r}"
                        ),
                    )
                ]
            )
        # A narrowing with no reason behind it is discarded. The reason is the
        # only thing that makes "less evidence is owed here" auditable, so an
        # unreasoned narrowing is indistinguishable from the question being
        # skipped — and the safe reading of a skipped question is that every kind
        # of evidence is still owed.
        required = item.required_evidence
        reason = item.required_evidence_reason.strip()
        if required is not RequiredEvidence.CODE_AND_TESTS and not reason:
            required = RequiredEvidence.CODE_AND_TESTS
        if required is RequiredEvidence.CODE_AND_TESTS:
            reason = ""
        produced.append(
            Obligation(
                id=_unique(item.id, seen_ids),
                description=item.description,
                type=item.type,
                importance=_importance(item.importance),
                explicit=item.explicit,
                observable_behavior=item.observable_behavior,
                source_spans=[span] if span is not None else [],
                # Whether an obligation is satisfied by work NOT done is decided
                # from the parse, never from the model's answer — the same move
                # #232 made for TEST_DEMAND and #219 for sibling dispositions,
                # both of which failed while they depended on the model restating
                # a distinction it had already been told. The section is now the
                # answering requirement's own, with no re-filing to reconcile.
                satisfied_by_absence=requirement.section is RequirementSection.EXCLUSION,
                required_evidence=required,
                required_evidence_reason=reason,
            )
        )
    return produced


def decompose_carry_keys(client: ModelClient, registry: list[RequirementRef]) -> dict[str, str]:
    """The key each requirement's derivation would be valid under, this run.

    The response schema here is the UNCONSTRAINED `_Decomposition`, deliberately.
    The real request constrains `requirement_id` and `source_quote` to the one
    requirement being asked about, so the schema inside a request key depends on
    which requirement it is — and a carry key that moved for that reason would
    discard work on a difference that has nothing to do with whether the answer
    is still right.

    The model is the one the requirement's own step runs on, which for the
    opening summary is the summary step's (#317). A requirement whose step moved
    to a different model has an answer produced by a different judge, and that is
    exactly what a carry key exists to notice.
    """
    schema = {
        "name": _Decomposition.__name__,
        "schema": inline_schema_refs(_Decomposition.model_json_schema()),
    }
    return {
        requirement.id: carry_key(
            system_prompt=_SYSTEM_PROMPT,
            response_schema=schema,
            model=client.model_for(_stage_for(requirement)),
            temperature=client.temperature,
            seed=client.seed,
            stage_logic_version=DECOMPOSE_STAGE_LOGIC_VERSION,
            requirement_text=requirement.text,
        )
        for requirement in registry
    }


def _stage_for(requirement: RequirementRef) -> str:
    """Which step accounts for this requirement."""
    return SUMMARY_STAGE if requirement.section is RequirementSection.TASK else _STAGE


def _ask_about(
    client: ModelClient,
    shown: list[RequirementRef],
    requirement: RequirementRef,
    quotes: list[str],
    revisions: dict[str, RequirementDerivation],
    partition_descriptor: dict,
) -> tuple[_Decomposition, list[UnusableAnswer]]:
    """One call, about `requirement` alone, quoting only `quotes`.

    **Records nothing.** Calls are issued concurrently, so anything appended to
    shared state in here would land in completion order and two runs over the
    same input would differ — see `concurrency.py`, rule 2. The unusable answers
    are handed back and recorded by the caller, in requirement order.

    `shown` is the whole registry — the batch scopes what a call answers for, not
    what it may read (#178). `quotes` is the requirement's own span set, and it
    is the constraint that carries the guarantee: an obligation about another
    requirement has no quotation available to it, so it is unsayable rather than
    detected afterwards.
    """
    messages = assemble(
        [
            Block(BlockKind.INSTRUCTIONS, _SYSTEM_PROMPT),
            Block(BlockKind.SUBJECT, _user_prompt(shown, requirement.id, revisions)),
        ]
    )
    # Both id fields are constrained, and `source_quote` is the one that matters.
    # `requirement_id` was already an enum when a call answering for three
    # requirements returned eleven entries about the Constraints section: an enum
    # restricts the LABEL, not what the entry is about. `source_quote` is what
    # says which text an obligation came from, and it was the only unconstrained
    # field (`findings.md` §8).
    allowed = {"requirement_id": [requirement.id], "source_quote": quotes}
    result = client.complete(
        messages,
        constrain(_Decomposition, allowed),
        partition_descriptor,
        parse_as=_Decomposition,
        stage=_STAGE,
    )
    # `requirement_id` only, deliberately. A `source_quote` the call did not
    # offer is reported by `_obligations_from`, which knows whether it landed
    # inside the requirement anyway and says so in words; scanning it here as
    # well would file a second, less informative record — with a whole sentence
    # in the `returned_id` field — for the same event.
    return result, scan(result, {"requirement_id": [requirement.id]}, _STAGE)


def _usable_disposition(
    entry: _RequirementDisposition,
    requirement_id: str,
    unusable_answers: UnusableAnswerLog | None,
) -> _RequirementDisposition | None:
    """The disposition, unless it names a requirement this call was not asked about.

    Unreachable under constrained decoding, where `requirement_id` is a
    single-valued enum. It is kept because the harness deliberately runs against
    providers whose structured-output support differs (`supplied_ids`), and a
    provider that ignored the enum would otherwise have its answer filed under
    the wrong requirement. Returning None leaves the requirement unaccounted for,
    which `_requirement_map` refuses by name.
    """
    if entry.requirement_id == requirement_id:
        return entry
    if unusable_answers is not None:
        unusable_answers.record(
            [
                UnusableAnswer(
                    stage=_STAGE,
                    field="requirement_id",
                    returned_id=entry.requirement_id,
                    reason=(
                        f"disposed a requirement this call was not asked about; it was "
                        f"asked about '{requirement_id}' alone"
                    ),
                )
            ]
        )
    return None


def _record_questions(
    returned: list[_OpenQuestion],
    requirement: RequirementRef,
    source: str,
    seen_ids: set[str],
    into: list[OpenQuestion],
) -> dict[str, str]:
    """Add one call's open questions to the run's list; return its id remapping.

    Called after the obligations of the same response, deliberately: ids are
    uniqued across both, and an obligation and a question minting the same slug
    must resolve the same way they did before this stage issued a call per
    requirement.
    """
    remapped: dict[str, str] = {}
    for item in returned:
        final_id = _unique(item.id, seen_ids)
        remapped.setdefault(item.id, final_id)
        # Inside the requirement first, and only then anywhere in the file. A
        # question quoting its own requirement is the ordinary case; one quoting
        # elsewhere still gets a span so it can be traced, rather than none.
        span = locate_within(requirement, item.source_quote) or find_span(source, item.source_quote)
        into.append(
            OpenQuestion(
                id=final_id,
                question=item.question,
                importance=_importance(item.importance),
                source_spans=[span] if span is not None else [],
            )
        )
    return remapped


def _span_requirement(summary: RequirementRef, decision: SpanDecision) -> RequirementRef:
    """One uncovered span of the summary, as an ordinary requirement of its own.

    `section` is `constraint` because that is what the span now is to the
    decomposer — one short bullet-shaped statement. The point of authoring here
    rather than inside the summary step is to hit the call shape that
    over-answers 0 times in 68 (`findings.md` §2), and the section is what the
    prompt renders. The id keeps the span's provenance visible, and the span
    carries the real offsets into the mandate so the obligation's quotation is
    honest.
    """
    located = locate_within(summary, decision.text)
    return RequirementRef(
        id=f"{summary.id}-span-{decision.index:02d}",
        section=RequirementSection.CONSTRAINT,
        ordinal=decision.index + 1,
        # `decide_spans` has already rejected a span that is not a substring of
        # the summary, so the fallback is unreachable; it is here so the function
        # is total rather than conditionally correct.
        span=located if located is not None else summary.span,
    )


def _already_derived(
    registry: list[RequirementRef],
    derived_ids: dict[str, list[str]],
    obligations: list[Obligation],
    plan: CarryPlan,
) -> list[Obligation]:
    """Every obligation the rest of the mandate produced, in registry order.

    Carried obligations are included alongside freshly derived ones. The summary
    step decides whether the obligations already derived require a property, and
    a continued run in which most requirements were carried would otherwise show
    it a nearly empty list and have it mark real coverage as absent — which
    yields a duplicate obligation for something the mandate already requires.
    """
    by_id = {obligation.id: obligation for obligation in obligations}
    for source in plan.carried.values():
        for obligation in source.obligations:
            by_id[obligation.id] = obligation

    listed: list[Obligation] = []
    for requirement in registry:
        if requirement.section is RequirementSection.TASK:
            continue
        ids = derived_ids.get(requirement.id)
        if ids is None:
            carried = plan.carried.get(requirement.id)
            ids = [obligation.id for obligation in carried.obligations] if carried else []
        listed.extend(by_id[obligation_id] for obligation_id in ids if obligation_id in by_id)
    return listed


def decompose(
    parsed: ParsedTaskFile,
    client: ModelClient,
    unusable_answers: UnusableAnswerLog | None = None,
    prior: LedgerEntry | None = None,
) -> Decomposition:
    """Decompose a parsed task into typed obligations, open questions, and the
    mapping from each identified requirement to what it produced.

    Takes a parsed task file and a client, and nothing else — no `ChangeSet`, no
    repository, no head revision (DR-202 decision 8).

    **One call per requirement** (#317). Batching several requirements into one
    call was already a narrowing of the single-call shape DR-164 measured shedding
    work; a batch of one narrows it the rest of the way, and it is what lets
    `source_quote` be an enum of the answering requirement's own spans. The
    measured cost is +1,506 bytes of schema per call, against the 93 KB a
    per-requirement response field would have cost at a batch of eight.

    **The opening summary is accounted for last, by its own step.** It is the
    parent of every other requirement rather than a peer, so asked about
    directly it answers for the whole mandate: 8 of 35 recorded calls with a
    `task-*` requirement in their answering set derived obligations for
    requirements they had only been shown, against 0 of 68 without one. See
    `requirement/summary.py`.
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
    obligations: list[Obligation] = []
    # Which obligations each requirement produced. Filled in as the calls return,
    # with no later attribution step: a call answers for one requirement and can
    # only quote that requirement's spans, so nothing can arrive needing to be
    # filed somewhere else.
    derived_ids: dict[str, list[str]] = {}
    # Open questions stay flat and referenced by id (see `_Decomposition`), so
    # they still need per-call resolution: each response mints its own ids.
    question_final: dict[str, dict[str, str]] = {}

    # What this run may take from the run it continues. With no prior it plans
    # every requirement as `derived`, and everything below runs exactly as it did
    # before carry-forward existed.
    plan = plan_carry(registry, prior, decompose_carry_keys(client, registry), client)
    to_ask = plan.issues_calls_for
    # The opening summary is deliberately not in this list. It is accounted for
    # below, after every other requirement has produced its obligations, so that
    # the question put about it is "does the rest of the mandate already require
    # this?" rather than "what does this paragraph require?" — the second has no
    # bounded answer.
    asking = [
        requirement
        for requirement in registry
        if requirement.id in to_ask and requirement.section is not RequirementSection.TASK
    ]
    calls_issued = 0

    # `partition` at one item per batch, rather than a bare loop, so the request
    # still carries a partition descriptor and provenance still records what
    # decompose partitioned at. `{"size": 1}` is a true statement about the run
    # and keeps a recording made under batching from replaying as though nothing
    # had moved.
    batches = partition(asking, ONE_REQUIREMENT_PER_CALL, key=lambda requirement: requirement.id)
    # Issued CONCURRENTLY; consumed below in requirement order. The consuming
    # loop stays serial and must: it mints obligation ids against a running
    # `seen_ids` set, so what an id ends up being depends on what came before it.
    # Only the waiting is parallel.
    answers = map_calls(
        batches,
        lambda batch: _ask_about(
            client,
            # The WHOLE registry, never `asking`: the answering set scopes what a
            # call answers for, not what it may read (#178). A call shown only
            # its own bullet could not notice that another section settles a term
            # this one leaves open.
            registry,
            batch.items[0],
            quotable_spans(batch.items[0].text),
            plan.revised,
            batch.request_partition(),
        ),
    )

    for batch, (result, scanned) in zip(batches, answers):
        requirement = batch.items[0]
        calls_issued += 1
        if unusable_answers is not None:
            unusable_answers.record(scanned)
        entry = _usable_disposition(
            result.requirement_disposition, requirement.id, unusable_answers
        )
        if entry is not None:
            dispositions.append(entry)
            if isinstance(entry, _Yielded):
                produced = _obligations_from(entry, requirement, seen_ids, unusable_answers)
                obligations.extend(produced)
                derived_ids.setdefault(requirement.id, []).extend(
                    obligation.id for obligation in produced
                )
        question_final[requirement.id] = _record_questions(
            result.open_questions, requirement, parsed.source, seen_ids, open_questions
        )

    # The summary, last, against everything the rest of the mandate produced.
    accounted: dict[str, RequirementDisposition] = {
        requirement_id: _carried_disposition(requirement_id, source)
        for requirement_id, source in plan.carried.items()
    }
    for summary in registry:
        if summary.section is not RequirementSection.TASK or summary.id not in to_ask:
            continue
        calls_issued += 1
        decisions = decide_spans(
            summary,
            _already_derived(registry, derived_ids, obligations, plan),
            client,
            unusable_answers,
        )
        span_obligations: list[Obligation] = []
        span_question_ids: list[str] = []
        # One call per uncovered span, asked about that span alone and shown the
        # summary for context — the span's pronouns have no antecedent without
        # it. Context only, never in the answering set, which is the
        # measured-safe shape rather than a guess.
        #
        # Issued concurrently, consumed in span order for the same reason the
        # loop above is serial: `seen_ids` mints ids against what came before.
        uncovered = [
            (_span_requirement(summary, d), d) for d in decisions if not d.covered
        ]

        def _ask_span(item, _summary=summary):
            span, decision = item
            return _ask_about(
                client,
                [_summary, span],
                span,
                [normalise(decision.text)],
                {},
                {"size": ONE_REQUIREMENT_PER_CALL},
            )

        span_answers = map_calls(uncovered, _ask_span)
        for (span, decision), (authored, scanned) in zip(uncovered, span_answers):
            calls_issued += 1
            if unusable_answers is not None:
                unusable_answers.record(scanned)
            span_entry = _usable_disposition(
                authored.requirement_disposition, span.id, unusable_answers
            )
            produced_here: list[Obligation] = []
            if isinstance(span_entry, _Yielded):
                # The quotation is the span, set from the mandate rather than
                # taken from the answer that named it: the model repairs a task
                # file's grammar when it quotes, and a repaired quotation stops
                # matching the source it claims to come from.
                produced_here = _obligations_from(
                    span_entry,
                    span,
                    seen_ids,
                    unusable_answers,
                    quote_override=normalise(decision.text),
                )
                span_obligations.extend(produced_here)
            span_questions = _record_questions(
                authored.open_questions, span, parsed.source, seen_ids, open_questions
            )
            questions_here: list[str] = []
            if isinstance(span_entry, _RaisedOpenQuestion):
                questions_here = _resolve(span_entry.ids(), span_questions)
                span_question_ids.extend(questions_here)
            if not produced_here and not questions_here:
                # An uncovered span must yield something. It was reached only
                # because the step before it argued, with a counterexample, that
                # the derived obligations do not require this property — so a
                # step that then declines it has contradicted the one that sent
                # it, and the property would be lost silently.
                raise SchemaValidationError(
                    f"span {decision.index} of requirement '{summary.id}' was found "
                    f"uncovered by the obligations already derived, but the call asked "
                    f"about it alone produced neither an obligation nor an open "
                    f"question: {normalise(decision.text)!r}"
                )
        obligations.extend(span_obligations)
        # The span-by-span account goes on the disposition WHATEVER it is, not
        # only when the summary yielded nothing. A covered span is a requirement
        # this paragraph states and another requirement already carries, and
        # under the shape this replaces that fact was recorded — the paragraph
        # derived its own duplicate and the linking stage merged the two, leaving
        # both requirements naming one obligation. Deriving no duplicate is the
        # improvement; losing the record of why would be a regression hidden
        # inside it.
        account = coverage_reason(decisions)
        if span_obligations:
            accounted[summary.id] = RequirementDisposition(
                requirement_id=summary.id,
                disposition=Disposition.YIELDED,
                obligation_ids=[obligation.id for obligation in span_obligations],
                open_question_ids=span_question_ids,
                reason=account,
            )
        elif span_question_ids:
            accounted[summary.id] = RequirementDisposition(
                requirement_id=summary.id,
                disposition=Disposition.OPEN_QUESTION,
                open_question_ids=span_question_ids,
                reason=account,
            )
        else:
            accounted[summary.id] = RequirementDisposition(
                requirement_id=summary.id,
                disposition=Disposition.NO_OBLIGATION,
                reason=account,
            )

    requirement_map = _requirement_map(
        registry,
        dispositions,
        derived_ids,
        question_final,
        parsed.unclaimed,
        accounted,
    )
    # A revised requirement's disposition is built by the ordinary path, because
    # it WAS asked of the model — so without this it would report itself as
    # `derived` and carry no reason, which is the same thing a genuinely fresh
    # requirement reports. The two are different: one had a predecessor and was
    # re-asked against it, and losing that distinction loses the only record that
    # an identifier could have been reused and was not.
    requirement_map = _stamp_revisions(requirement_map, plan)

    # Always, not only on a carrying run. The summary's obligations are derived
    # last and the summary sits first in the registry, so the list the loops
    # build is no longer document order on any run.
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
    """The obligations and questions of every requirement, in registry order.

    **Nothing is dropped.** An output no disposition names is appended in the
    order it arrived rather than left out: a `yielded` disposition and an open
    question can reach us from the same response, and a question the disposition
    did not name is still a question the reviewer raised. Silently discarding it
    here would be the same silence this stage exists to remove.
    """
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

    ordered_obligations.extend(
        obligation for obligation in obligations if obligation.id not in seen
    )
    ordered_questions.extend(question for question in open_questions if question.id not in seen)
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
    defect_sets: list[DefectSet] | None = None,
    pair_verdicts: list[PairVerdict] | None = None,
) -> LedgerEntry:
    """This run's ledger record, ready to write.

    Two inputs, deliberately. The **derivations** come from `derived`, before
    linking: what a later run carries forward per requirement is what this stage
    derived, and recording the post-merge set would let one run's merge silently
    become the next run's premise (DR-204). The **merge decisions** come from
    `linked`, because that is the stage that made them.

    `defect_sets` is absent on a `decompose` run and present on a `check` (#313),
    and `pair_verdicts` behaves identically (#314). Absent means nothing carries
    forward, which is the conservative direction: a `decompose` enumerated no
    defects and judged no pairs, so there is nothing to lose by saying so.
    """
    return LedgerEntry(
        run_id=run_id,
        parent_run_id=parent_run_id,
        stage_logic_version=DECOMPOSE_STAGE_LOGIC_VERSION,
        task_digest=task_digest,
        calls_issued=derived.calls_issued,
        derivations=list(derived.derivations),
        merge_decisions=list((linked or derived).merge_decisions),
        defect_sets=list(defect_sets or []),
        pair_verdicts=list(pair_verdicts or []),
    )


def _requirement_map(
    registry: list[RequirementRef],
    returned: list[_RequirementDisposition],
    derived_ids: dict[str, list[str]],
    question_final: dict[str, dict[str, str]],
    unread: list,
    accounted: dict[str, RequirementDisposition] | None = None,
) -> RequirementMap:
    """Reconcile the returned dispositions against the registry.

    `accounted` holds the dispositions that arrive already built rather than as a
    model response: the ones carried from a prior run, and the ones the summary
    step settled from its span verdicts. Both are checked against the registry
    here rather than trusted, by the same rules as anything the model returned.

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
    # A carried or summary requirement produced no `_RequirementDisposition`, so
    # no model response accounts for it — and it must still be accounted for,
    # because a registry requirement with no disposition is the malformed-response
    # case this function exists to reject. Checked here rather than trusted: an id
    # supplied for a requirement the registry does not have is caught by the same
    # rule as one the model invented.
    accounted = accounted or {}
    accounted_unknown = sorted(set(accounted) - known)
    if accounted_unknown:
        raise SchemaValidationError(
            f"dispositions supplied for requirement ids not in the registry: "
            f"{', '.join(accounted_unknown)}"
        )
    both = sorted(set(accounted) & set(by_requirement))
    if both:
        raise SchemaValidationError(
            f"requirement(s) both accounted for without a call and disposed by a "
            f"response: {', '.join(both)}"
        )
    missing = [
        requirement.id
        for requirement in registry
        if requirement.id not in by_requirement and requirement.id not in accounted
    ]
    if missing:
        raise SchemaValidationError(
            f"response did not account for {len(missing)} of {len(registry)} "
            f"requirements: {', '.join(missing)}"
        )

    dispositions: list[RequirementDisposition] = []
    for requirement in registry:
        if requirement.id in accounted:
            dispositions.append(accounted[requirement.id])
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


def _unique(candidate: str, seen: set[str]) -> str:
    """Keep ids unique and deterministic across obligations and open questions."""
    unique_id = candidate
    suffix = 2
    while unique_id in seen:
        unique_id = f"{candidate}-{suffix}"
        suffix += 1
    seen.add(unique_id)
    return unique_id
