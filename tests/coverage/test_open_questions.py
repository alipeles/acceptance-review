"""#113 follow-up: open questions must be judged against the diff, not left
"unresolved" forever regardless of whether the diff actually answers them.

Judgment is a schema-constrained model call; per the replay-first invariant
these tests inject the recorded response via completion_fn — no live calls."""

import tempfile

from acceptance.coverage.open_questions import (
    OpenQuestionResolution,
    apply_open_question_resolutions,
    resolve_open_questions,
)
from acceptance.llm import Mode, ModelClient, TranscriptStore
from acceptance.review_state import ChangeSet, DiffHunk, FileChange, OpenQuestion
from tests.support import client_returning


def _question(question_id: str, text: str) -> OpenQuestion:
    return OpenQuestion(id=question_id, question=text)


def _change_set() -> ChangeSet:
    hunk = DiffHunk(
        header="@@ -1 +1 @@",
        old_start=1,
        old_lines=1,
        new_start=1,
        new_lines=1,
        content="+result = f'-{amount}'",
    )
    return ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(path="pkg.py", status="modified", category="source", hunks=[hunk]),
        ],
    )


def _exploding_client() -> ModelClient:
    def boom(**kwargs):
        raise AssertionError("a model call was issued with no open questions to judge")

    return ModelClient(
        model="x", mode=Mode.RECORD, store=TranscriptStore(tempfile.mkdtemp()), completion_fn=boom
    )


def test_no_open_questions_issues_no_model_call():
    resolutions = resolve_open_questions([], _change_set(), _exploding_client())
    assert resolutions == []


def test_diff_resolves_the_question():
    change_set = _change_set()
    question = _question("q-1", "Minus sign or parentheses for negative amounts?")
    response = {
        "resolutions": [
            {
                "question_id": "q-1",
                "resolved": True,
                "rationale": "The diff formats negatives with a leading minus sign.",
                "diff_refs": ["pkg.py#0"],
                "implemented_behavior": "Negative amounts are formatted with a leading minus sign.",
            }
        ]
    }

    resolutions = resolve_open_questions([question], change_set, client_returning(response))

    assert len(resolutions) == 1
    assert resolutions[0].question_id == "q-1"
    assert resolutions[0].resolved is True
    assert resolutions[0].diff_refs
    assert resolutions[0].diff_refs[0].file == "pkg.py"


def test_diff_does_not_resolve_the_question():
    change_set = _change_set()
    question = _question("q-1", "What should happen on a network timeout?")
    response = {
        "resolutions": [
            {
                "question_id": "q-1",
                "resolved": False,
                "rationale": "The diff never touches network or timeout handling.",
                "diff_refs": [],
                "implemented_behavior": "",
            }
        ]
    }

    resolutions = resolve_open_questions([question], change_set, client_returning(response))

    assert resolutions[0].resolved is False
    assert resolutions[0].diff_refs == []


def test_question_missing_from_the_model_response_stays_open():
    # Uncertainty is first-class -- a question the model silently drops must
    # not vanish, it must still show up as open rather than disappearing.
    change_set = _change_set()
    question = _question("q-1", "Some question the model forgets to answer")

    resolutions = resolve_open_questions(
        [question], change_set, client_returning({"resolutions": []})
    )

    assert len(resolutions) == 1
    assert resolutions[0].resolved is False


def test_unknown_question_id_in_response_is_dropped():
    change_set = _change_set()
    question = _question("q-1", "A real question")
    response = {
        "resolutions": [
            {
                "question_id": "ghost",
                "resolved": True,
                "rationale": "...",
                "diff_refs": [],
                "implemented_behavior": "",
            }
        ]
    }

    resolutions = resolve_open_questions([question], change_set, client_returning(response))

    # The ghost id is dropped, but q-1 still gets its "stays open" fallback.
    assert len(resolutions) == 1
    assert resolutions[0].question_id == "q-1"
    assert resolutions[0].resolved is False


def test_apply_resolutions_writes_the_judgment_onto_the_question():
    question = _question("q-1", "Minus sign or parentheses?")
    resolution = OpenQuestionResolution(
        question_id="q-1",
        resolved=True,
        rationale="Uses a minus sign.",
        diff_refs=[],
    )

    updated = apply_open_question_resolutions([question], [resolution])

    assert updated[0].resolved is True
    assert updated[0].resolution_rationale == "Uses a minus sign."
    # Original is untouched (apply_ returns copies, per the mapping.py/strength.py pattern).
    assert question.resolved is False


def test_apply_resolutions_leaves_unjudged_questions_open():
    question = _question("q-1", "A question with no matching resolution")

    updated = apply_open_question_resolutions([question], [])

    assert updated[0].resolved is False
    assert updated[0].resolution_rationale is None


def test_open_question_resolution_round_trips_through_persistence():
    resolution = OpenQuestionResolution(
        question_id="q-1",
        resolved=True,
        rationale="...",
        diff_refs=[],
    )
    assert OpenQuestionResolution.from_dict(resolution.to_dict()) == resolution
