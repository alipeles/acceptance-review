"""The pipeline actually reaches its defect verdicts through #191's two steps.

Separate from `tests/evidence/test_discrimination.py` deliberately, and for the
reason CLAUDE.md gives: every test in that module calls `judge_discrimination`
directly, and all of them would still pass if `run_review` never called it —
the well-tested-helper-the-pipeline-never-invokes hole that defect injection
keeps finding here. These fail if the wiring is removed.

The second test is the one the split exists for. It adds a test to the repo
between two runs and asserts the enumeration request is *byte-identical*, which
is stronger than asserting the answers matched: an identical request replays
from its transcript, so the model is never asked again and cannot answer
differently. That is what "adding a test leaves the enumerated defects
unchanged" means when it is true by construction rather than by luck.
"""

from __future__ import annotations

import json
import subprocess
import tempfile

from acceptance.change.diff import extract_change_set
from acceptance.llm import Mode, ModelClient, TranscriptStore
from acceptance.pipeline import run_review
from tests.support import _EMPTY_BY_SCHEMA, _completed, _supplied_enum

_TASK = """# Task
Amounts are formatted to two decimal places.

## Constraints
- Amounts are formatted to two decimal places.
"""

_OBLIGATION = {
    "id": "two-decimals",
    "description": "Amounts are formatted to two decimal places",
    "type": "functional",
    "importance": "critical",
    "explicit": True,
    "observable_behavior": "fmt(1) == '1.00'",
    "source_quote": "Amounts are formatted to two decimal places.",
}


def _git(repo, *args) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "money.py").write_text("def fmt(x):\n    return str(x)\n")
    (repo / "test_money.py").write_text(
        "from money import fmt\n\n\ndef test_whole():\n    assert fmt(1) == '1.00'\n"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "money.py").write_text("def fmt(x):\n    return f'{x:.2f}'\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head")
    return repo, base, _git(repo, "rev-parse", "HEAD")


def _client(calls: list) -> ModelClient:
    """Answers every stage off the ids it was supplied, and records each call.

    Deliberately generic: a fixture that hard-coded ids would stop exercising
    the wiring the moment the ids moved, and this module is only ever about
    which calls the pipeline makes.
    """

    def completion_fn(**kwargs):
        from types import SimpleNamespace

        name = kwargs["response_format"]["json_schema"]["name"]
        calls.append((name, kwargs))

        if name == "_Decomposition":
            body = {
                "obligations": [_OBLIGATION],
                "open_questions": [],
                "requirement_dispositions": [],
            }
        elif name == "_Mappings":
            body = {
                "mappings": [
                    {
                        "test_id": test_id,
                        "obligation_ids": _supplied_enum("obligation_ids", **kwargs),
                        "rationale": ".",
                    }
                    for test_id in _supplied_enum("test_id", **kwargs)
                ]
            }
        elif name == "_Enumeration":
            body = {
                "obligations": [
                    {
                        "obligation_id": obligation_id,
                        "defects": [
                            {"description": "truncates instead of padding to two places"},
                            {"description": "formats to three places"},
                        ],
                    }
                    for obligation_id in _supplied_enum("obligation_id", **kwargs)
                ]
            }
        elif name == "_DefectVerdicts":
            body = {
                "verdicts": [
                    {
                        "defect_id": defect_id,
                        "would_be_caught": defect_id.endswith("::d1"),
                        "reason": "the assertion pins both places",
                    }
                    for defect_id in _supplied_enum("defect_id", **kwargs)
                ]
            }
        else:
            body = _EMPTY_BY_SCHEMA[name]

        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps(_completed(body, **kwargs)))
                )
            ],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

    return ModelClient(
        model="x",
        mode=Mode.RECORD,
        store=TranscriptStore(tempfile.mkdtemp()),
        completion_fn=completion_fn,
    )


def _run(repo, base, head, calls):
    return run_review(
        task_text=_TASK,
        change_set=extract_change_set(repo, base, head),
        repo=repo,
        client=_client(calls),
        reviewed_revision=head,
    )


def test_the_pipeline_reaches_its_defect_verdicts_through_the_separated_steps(tmp_path):
    repo, base, head = _repo(tmp_path)
    calls: list = []

    review = _run(repo, base, head, calls)

    made = [name for name, _ in calls]
    assert "_Enumeration" in made, "the pipeline never enumerated any defect"
    assert "_DefectVerdicts" in made, "the pipeline never reached a verdict"
    assert made.index("_Enumeration") < made.index("_DefectVerdicts")

    # And the verdicts actually landed. `partially_supported` is the telling
    # value: the double catches the first defect and not the second, so this
    # class is only reachable if both per-defect verdicts arrived and were told
    # apart. A pipeline that made both calls and discarded the answers would
    # report `unsupported`, and one that collapsed them to a single flag would
    # report `strongly_supported`.
    obligation = next(o for o in review.obligation_map if o.id == "two-decimals")
    assert obligation.evidence_class == "partially_supported"


def test_adding_a_test_leaves_the_obligations_enumeration_request_unchanged(tmp_path):
    repo, base, head = _repo(tmp_path)
    before: list = []
    _run(repo, base, head, before)

    # A second head commit that adds a test — and nothing else.
    (repo / "test_money_extra.py").write_text(
        "from money import fmt\n\n\ndef test_fraction():\n    assert fmt(1.5) == '1.50'\n"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "add a test")
    after: list = []
    _run(repo, base, _git(repo, "rev-parse", "HEAD"), after)

    def enumeration_requests(calls):
        return [kwargs["messages"] for name, kwargs in calls if name == "_Enumeration"]

    assert enumeration_requests(before), "no enumeration call was made to compare"
    assert enumeration_requests(before) == enumeration_requests(after)

    # The run genuinely saw the new test — otherwise the assertion above is
    # satisfied by a pipeline that ignored the second commit entirely.
    mapped = [kwargs for name, kwargs in after if name == "_Mappings"]
    assert any("test_money_extra.py" in json.dumps(kwargs["messages"]) for kwargs in mapped)


def test_the_pipeline_hands_the_verdict_stage_the_real_test_source(tmp_path):
    """`judge_discrimination` takes the sources as an argument, so the helper can
    be perfectly correct while the pipeline passes nothing — the exact hole
    CLAUDE.md says defect injection keeps finding here. `def test_whole(` appears
    only in the file on disk, never in an extracted assertion or an identifier,
    so it can only be present if discovery's source actually made the trip.
    """
    repo, base, head = _repo(tmp_path)
    calls: list = []

    _run(repo, base, head, calls)

    verdicts = [kwargs for name, kwargs in calls if name == "_DefectVerdicts"]
    assert verdicts, "the pipeline never reached a verdict call"
    assert any("def test_whole(" in json.dumps(kwargs["messages"]) for kwargs in verdicts)
