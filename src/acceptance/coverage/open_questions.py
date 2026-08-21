"""Open-question resolution against the diff (#113, §7.3/§9.3).

An `OpenQuestion` surfaced at decomposition time is a material ambiguity a
reviewer would need answered before judging the obligations it bears on. It
must not sit "unresolved" forever on every re-run: when the diff itself makes
the answer clear, that has to be noted and recorded in the review state, not
left as something only a human conversation happens to have concluded and the
tool immediately forgets — CLAUDE.md's "structured, persisted review-state,
not an unstructured model transcript" invariant applies here exactly as it
does to findings.

A semantic judgment (does this diff resolve this ambiguity), so a
schema-constrained model call through the M0.4 harness — recorded for replay,
never a live call in tests. Shape mirrors mapping.py/strength.py: a judgment
type referencing `OpenQuestion` by id, plus an `apply_` function that writes
the verdict back onto copies of the entity — not embedding `OpenQuestion`
directly, which would need `review_state.py` to import back from here.
"""

from __future__ import annotations

from pydantic import Field

from acceptance.coverage.prompt import DiffRef, diff_block, hunk_labels, resolve_refs
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.model_base import PersistableModel
from acceptance.request_blocks import Block, BlockKind, assemble
from acceptance.review_state import (
    ChangeSet,
    Link,
    Obligation,
    ObligationType,
    OpenQuestion,
)
from acceptance.supplied_ids import UnusableAnswerLog, constrain, scan

_STAGE = "open-question judgment"

_SYSTEM_PROMPT = """\
You judge whether a code diff resolves an OPEN QUESTION raised about a task —
a material ambiguity a reviewer would otherwise need answered before judging
whether the requested behavior was actually delivered.

For each open question, decide:
- resolved: the diff itself makes the answer clear — e.g. it implements one
  of the possible interpretations unambiguously, or the question no longer
  applies given what was actually built.
- NOT resolved: the diff is silent on the question, or the code could still
  reasonably be read either way.

Only mark a question resolved when the diff ITSELF makes the answer clear —
not by assumption, convention, or what would be reasonable; if you have to
guess which reading the diff intends, it is not resolved. When resolved, cite
`diff_refs` (labels like `path#0`) for the hunks that answer it, and a short
`rationale` explaining what the diff shows. When not resolved, still return a
short `rationale` (why the diff doesn't settle it) and leave `diff_refs`
empty.

When resolved, also return `implemented_behavior`: ONE sentence stating the
behavior the change committed to, written as a requirement about the software
— not as a comment about the diff or about this review.

    good: "Retries use exponential backoff."
    bad:  "The diff implements retries with exponential backoff, so the
           question of which strategy was intended is settled."

The difference matters: this sentence becomes an obligation that later stages
match tests against, so it must describe the behavior a test could exercise.
Write it in the present tense, about the system, with no reference to the
question, the diff, or the fact that it was resolved. When NOT resolved, return
an empty string for it."""


class OpenQuestionResolution(PersistableModel):
    """Whether the diff resolves an open question raised at decomposition."""

    question_id: str
    resolved: bool
    rationale: str
    diff_refs: list[DiffRef] = Field(default_factory=list)
    # The behavior the change committed to, as a requirement-shaped sentence
    # (#214). Empty unless resolved. This is the one thing code cannot write
    # for itself: `rationale` explains what the diff SHOWS, which reads as
    # commentary on the review, and an obligation built from it would be
    # matched against tests as commentary.
    implemented_behavior: str = ""


class _Judged(StrictResponseModel):
    question_id: str
    resolved: bool
    rationale: str
    diff_refs: list[str]
    implemented_behavior: str


class _Judgments(StrictResponseModel):
    resolutions: list[_Judged]


def _subject_block(open_questions: list[OpenQuestion]) -> Block:
    """The questions this call is about. The diff they are asked against is a
    separate, shared block that `assemble` places ahead of this one."""
    lines = ["## Open questions", ""]
    for question in open_questions:
        lines.append(f"- id={question.id}: {question.question}")
    return Block(BlockKind.SUBJECT, "\n".join(lines))


def resolve_open_questions(
    open_questions: list[OpenQuestion],
    change_set: ChangeSet,
    client: ModelClient,
    unusable: UnusableAnswerLog | None = None,
) -> list[OpenQuestionResolution]:
    """Judge each open question against the diff: resolved (with citation) or
    still open. No open questions -> no model call."""
    if not open_questions:
        return []

    label_to_ref = hunk_labels(change_set)
    messages = assemble(
        [
            diff_block(change_set),
            Block(BlockKind.INSTRUCTIONS, _SYSTEM_PROMPT),
            _subject_block(open_questions),
        ]
    )
    allowed = {
        "question_id": [question.id for question in open_questions],
        "diff_refs": list(label_to_ref),
    }
    result = client.complete(
        messages, constrain(_Judgments, allowed), parse_as=_Judgments, stage=_STAGE
    )
    if unusable is not None:
        unusable.record(scan(result, allowed, _STAGE))

    valid_ids = {q.id for q in open_questions}
    judged_ids: set[str] = set()
    resolutions = []
    for judged in result.resolutions:
        if judged.question_id not in valid_ids:
            continue  # model referenced an unknown question id -- ignore
        judged_ids.add(judged.question_id)
        resolutions.append(
            OpenQuestionResolution(
                question_id=judged.question_id,
                resolved=judged.resolved,
                rationale=judged.rationale,
                diff_refs=resolve_refs(judged.diff_refs, label_to_ref),
                implemented_behavior=(
                    judged.implemented_behavior.strip() if judged.resolved else ""
                ),
            )
        )
    # A question the model didn't return a judgment for stays open rather
    # than silently vanishing from the output (uncertainty is first-class).
    for question in open_questions:
        if question.id not in judged_ids:
            resolutions.append(
                OpenQuestionResolution(
                    question_id=question.id,
                    resolved=False,
                    rationale="No judgment was returned for this question.",
                )
            )
    return resolutions


def apply_open_question_resolutions(
    open_questions: list[OpenQuestion], resolutions: list[OpenQuestionResolution]
) -> list[OpenQuestion]:
    """Return copies of `open_questions` with the resolution judgment written
    back on — so a resolved question stays resolved on every later render/
    persist, instead of the tool re-asking (and the answer only ever having
    existed in a conversation)."""
    by_id = {r.question_id: r for r in resolutions}
    updated = []
    for question in open_questions:
        resolution = by_id.get(question.id)
        if resolution is None:
            updated.append(question)
            continue
        updated.append(
            question.model_copy(
                update={
                    "resolved": resolution.resolved,
                    "resolution_rationale": resolution.rationale,
                    "resolution_refs": [
                        Link(kind="code", ref=f"{ref.file}#{ref.hunk_header}")
                        for ref in resolution.diff_refs
                    ],
                }
            )
        )
    return updated


def derived_obligation_id(question_id: str) -> str:
    """The id of the obligation derived from a resolved question (#214).

    A pure function of the question's id, computed here rather than minted by
    the model, for two reasons that happen to point the same way. This task
    requires byte-identical review state across two runs over identical input,
    which a per-response id cannot give (#231). And #180's design re-judges an
    obligation only when its own inputs changed, so an id that moved between
    runs would present as one obligation vanishing and another appearing — it
    would never carry forward, and would silently re-judge while looking stable.

    Single-sourced because mandate coverage joins requirements to their derived
    obligations through it; a second spelling anywhere would silently under-count
    coverage.
    """
    return f"{question_id}-as-implemented"


def derive_obligations(
    open_questions: list[OpenQuestion], resolutions: list[OpenQuestionResolution]
) -> list[Obligation]:
    """Turn each resolved open question into the obligation it implies (#214).

    An ambiguity the builder settled by implementing one reading is a behavior
    they committed to, and it must not ship untested. Before this, a resolved
    question produced nothing: it left `resolved=True` and a rationale, reached
    none of `derive_verdict`'s inputs, and so an implementation choice nobody
    had tested could not lower the verdict. That is the same silence #214 is
    about, wearing a different label.

    The obligation is **addressed by construction**. Resolution had to cite the
    hunks that answer the question, so the code is already located and it is a
    category error to ask the coverage stage whether it exists. It therefore
    rides ONE axis — is the chosen behavior tested — and reaches the verdict
    through the ordinary weak-evidence path rather than through any new rule.

    Everything except the behavior sentence is fixed here rather than inferred:
    `explicit=False` because the obligation is not stated in the mandate (which
    is exactly what that field means), and `functional` because a settled
    implementation choice is a behavior. `importance` is carried from the
    question rather than defaulted — it is recorded data about the ambiguity,
    not a guess.

    A resolution with no citation yields nothing. The prompt forbids resolving
    without one, so such an answer is an assertion rather than a finding, and
    building an obligation on it would manufacture a test demand out of a claim
    the review could not substantiate.
    """
    by_id = {question.id: question for question in open_questions}
    derived: list[Obligation] = []
    for resolution in resolutions:
        question = by_id.get(resolution.question_id)
        if question is None or not resolution.resolved:
            continue
        behavior = resolution.implemented_behavior.strip()
        if not behavior or not resolution.diff_refs:
            continue
        derived.append(
            Obligation(
                id=derived_obligation_id(question.id),
                description=behavior,
                type=ObligationType.FUNCTIONAL,
                importance=question.importance,
                explicit=False,
                observable_behavior=behavior,
                # Links back to the task text that was ambiguous, so the derived
                # obligation satisfies typed-and-linked like any other.
                source_spans=list(question.source_spans),
                coverage_status="addressed",
                coverage_refs=[f"{ref.file}#{ref.hunk_header}" for ref in resolution.diff_refs],
            )
        )
    return derived
