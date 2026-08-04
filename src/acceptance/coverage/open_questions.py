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

from acceptance.coverage.prompt import DiffRef, hunk_labels, render_diff_section, resolve_refs
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.supplied_ids import UnusableAnswerLog, constrain, scan
from acceptance.model_base import PersistableModel
from acceptance.review_state import ChangeSet, Link, OpenQuestion

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
empty."""


class OpenQuestionResolution(PersistableModel):
    """Whether the diff resolves an open question raised at decomposition."""

    question_id: str
    resolved: bool
    rationale: str
    diff_refs: list[DiffRef] = Field(default_factory=list)


class _Judged(StrictResponseModel):
    question_id: str
    resolved: bool
    rationale: str
    diff_refs: list[str]


class _Judgments(StrictResponseModel):
    resolutions: list[_Judged]


def _render_prompt(open_questions: list[OpenQuestion], change_set: ChangeSet) -> str:
    lines = ["## Open questions", ""]
    for question in open_questions:
        lines.append(f"- id={question.id}: {question.question}")
    lines.append("")
    lines.extend(render_diff_section(change_set))
    return "\n".join(lines)


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
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _render_prompt(open_questions, change_set)},
    ]
    allowed = {
        "question_id": [question.id for question in open_questions],
        "diff_refs": list(label_to_ref),
    }
    result = client.complete(
        messages, constrain(_Judgments, allowed), parse_as=_Judgments
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
