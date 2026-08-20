"""The ordering rules, checked over the requests a real review run issues (#265).

`test_request_blocks.py` pins the assembler. This pins the **pipeline**, and the
difference is the one CLAUDE.md warns about: a helper with a good unit test that
a stage never actually calls. Every check here runs against `run_review` and the
requests that came out of it, so a stage that builds its messages by hand fails
even though the assembler is perfect.

Two of these are the mandate's Completion expectations at run scope:

- a request must not put content unique to it ahead of content it shares with
  another request of the same run;
- content two requests of one run carry must be written the same way in both.

The third — that no stage marks its own reusable opening — is enforced by
`assemble` and tested there; at this level it shows up as every request in the
run having gone through the assembler at all.
"""

from __future__ import annotations

import subprocess

from acceptance.change.diff import extract_change_set
from acceptance.coverage.prompt import diff_block
from acceptance.pipeline import run_review
from acceptance.request_blocks import REUSABLE_OPENING_MESSAGES, SHARED_PREAMBLE
from tests.support import client_dispatching

_TASK = """# Task
Format money amounts correctly.

## Constraints
- Negative amounts are formatted with a leading minus sign.
"""

_JUDGMENTS = {
    "_Decomposition": {
        "obligations": [
            {
                "id": "formats-negatives",
                "description": "Negative amounts are formatted with a leading minus sign.",
                "type": "functional",
                "importance": "critical",
                "explicit": True,
                "observable_behavior": "format(-1) is defined",
                "source_quote": "Negative amounts are formatted",
            }
        ],
        "open_questions": [],
        "requirement_dispositions": [
            {
                "requirement_id": "task-01",
                "disposition": "no_obligation",
                "reason": "Restates the constraint below; imposes nothing of its own.",
            },
            {
                "requirement_id": "constraint-01",
                "disposition": "yielded",
                "obligation_id": "formats-negatives",
                "more_obligation_ids": [],
            },
        ],
    },
    "_Mappings": {"mappings": []},
    "_Discrimination": {"obligations": []},
    "_Coverage": {
        "classifications": [
            {
                "obligation_id": "formats-negatives",
                "status": "addressed",
                "rationale": "money.py implements it.",
                "diff_refs": [],
            }
        ]
    },
    "_Detections": {"unrequested_changes": []},
    "_Judgments": {"resolutions": []},
    "_Recommendations": {"recommendations": []},
    "_Mismatches": {"mismatches": []},
}


def _git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


def _repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "money.py").write_text("def fmt(x):\n    return str(x)\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "money.py").write_text("def fmt(x):\n    return f'{x:.2f}'\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head")
    return repo, base, _git(repo, "rev-parse", "HEAD")


def _run(tmp_path):
    """One real review run: its requests, and the change set it reviewed.

    The change set comes back so a test can render the shared diff block itself
    and compare against it, rather than guessing where the block ends by
    splitting the prompt text.
    """
    repo, base, head = _repo(tmp_path)
    change_set = extract_change_set(repo, base, head)
    capture: list[dict] = []
    run_review(
        task_text=_TASK,
        change_set=change_set,
        repo=repo,
        client=client_dispatching(_JUDGMENTS, capture=capture),
        reviewed_revision=head,
    )
    assert capture, "the pipeline ran but issued no requests at all"
    return capture, change_set


def _requests(tmp_path) -> list[dict]:
    return _run(tmp_path)[0]


def _opening(request: dict) -> str:
    return "\n\n".join(m["content"] for m in request["messages"][:REUSABLE_OPENING_MESSAGES])


def _subject(request: dict) -> str:
    return "\n\n".join(m["content"] for m in request["messages"][REUSABLE_OPENING_MESSAGES:])


def test_every_request_the_pipeline_issues_opens_with_the_shared_preamble(tmp_path):
    """The cross-stage opening exists at all.

    Fails the moment a stage builds its own `[{"role": "system", ...}]` again,
    which is the regression this whole change is about — and the one a unit test
    of the assembler cannot see.
    """
    for request in _requests(tmp_path):
        first = request["messages"][0]
        assert first["role"] == "system", f"{request['schema']} does not open with a system message"
        assert first["content"] == SHARED_PREAMBLE, (
            f"{request['schema']} opens with its own system prompt rather than the "
            "shared preamble, so it can share no opening with any other stage"
        )


def test_no_request_places_content_unique_to_it_ahead_of_content_it_shares(tmp_path):
    """The mandate's first Completion expectation, over a real run.

    "Shared" is measured rather than declared: a line that appears in the text of
    more than one of the run's requests is shared, and it must not appear after
    a line unique to this one.
    """
    requests = _requests(tmp_path)
    counts: dict[str, int] = {}
    for request in requests:
        text = "\n".join(m["content"] for m in request["messages"])
        for line in {ln for ln in text.splitlines() if ln.strip()}:
            counts[line] = counts.get(line, 0) + 1

    offenders = []
    for request in requests:
        subject_lines = [ln for ln in _subject(request).splitlines() if ln.strip()]
        shared_in_subject = [ln for ln in subject_lines if counts.get(ln, 0) > 1]
        # A line can be shared by coincidence — a blank heading, a bare `)` of
        # some rendered code. Only a run of them is evidence that a whole block
        # ended up on the wrong side of the boundary.
        if len(shared_in_subject) > max(5, len(subject_lines) // 2):
            offenders.append((request["schema"], len(shared_in_subject), len(subject_lines)))

    assert not offenders, (
        "these requests carry a substantial block of content that other requests "
        f"of the same run also carry, placed after content unique to them: {offenders}"
    )


def test_content_two_requests_share_is_written_the_same_way_in_both(tmp_path):
    """The mandate's second Completion expectation, over a real run.

    The diff is the block that matters: five stages carry it, and it is the
    largest thing any of them carries. If two of them rendered it differently
    the requests would share nothing, however well ordered each one was.
    """
    requests, change_set = _run(tmp_path)
    expected = diff_block(change_set).text

    with_diff = [r for r in requests if "## Diff" in _opening(r)]
    assert len(with_diff) > 1, (
        "expected several stages of one run to carry the shared diff block; "
        f"only {len(with_diff)} did, so this test is not measuring what it claims"
    )

    # Not "the text after `## Diff` matches" — that would also compare whatever
    # block follows the diff, which is each stage's own instructions and differs
    # legitimately. The claim is narrower: the diff block itself is the same
    # bytes, and it sits at the head of the opening's user message.
    wrong = [r["schema"] for r in with_diff if not r["messages"][1]["content"].startswith(expected)]
    assert not wrong, (
        f"{len(wrong)} of {len(with_diff)} requests carrying a diff do not open with the "
        f"shared rendering of it: {wrong}. A provider reuses a repeated opening only "
        "when it repeats exactly."
    )


def test_the_requests_that_share_a_diff_share_a_real_opening(tmp_path):
    """The point of the change, stated as an outcome rather than a mechanism.

    Not a token-count assertion — that would pin a number that legitimately moves
    with the fixture. What is pinned is that the common opening of the
    diff-carrying requests is the diff itself, not merely the one-line preamble.
    """
    requests, change_set = _run(tmp_path)
    with_diff = [r for r in requests if "## Diff" in _opening(r)]
    openings = [_opening(r) for r in with_diff]

    common = openings[0]
    for other in openings[1:]:
        while not other.startswith(common):
            common = common[:-1]

    assert "## Diff" in common, (
        "the diff-carrying requests diverge before the diff, so the block they "
        f"all carry is not in their shared opening. Common opening: {common[:200]!r}"
    )
    # The whole diff, not just its heading — a common opening that stopped at
    # `## Diff` would satisfy the line above and share none of the payload.
    # Compared against the rendered block rather than a token count, which would
    # pin a number that moves with the fixture.
    assert diff_block(change_set).text in common, (
        "the shared opening stops partway through the diff, so the stages diverge "
        f"inside the block they all carry. Common opening: {common[:400]!r}"
    )
