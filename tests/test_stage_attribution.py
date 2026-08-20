"""Every review-pipeline model call names the stage that issued it (#264).

Per-stage cost accounting is only as good as its worst-attributed call: one
call site that omits `stage=` puts its spend in a bucket called "unknown", and
the question the feature exists to answer — *which stage is expensive* — goes
back to being unanswerable for exactly the stage nobody thought about.

Two tests, and they fail for different reasons on purpose. The scan is a
tripwire on **new** call sites, which is the failure mode that will actually
happen: someone adds a stage six months from now and the aggregate quietly
grows an `unknown` row. The wiring test proves the attribution survives a real
`run_review`, which the scan cannot — a call site can pass `stage=` to a client
that never records it.

`benchmark/` is deliberately out of scope: it is not part of a review run
(CLAUDE.md, repo layout), and its spend must not land in a review's footer.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import acceptance
from acceptance.change.diff import extract_change_set
from acceptance.llm import UNKNOWN_STAGE
from acceptance.pipeline import run_review
from tests.support import client_dispatching

_SRC = Path(acceptance.__file__).parent

# The harness is a separate program that happens to share the client.
_EXCLUDED = ("benchmark",)

# Both are model calls that cost money, so both are attributed.
_ATTRIBUTED_METHODS = ("complete", "embed")


def _product_modules() -> list[Path]:
    return [
        path
        for path in sorted(_SRC.rglob("*.py"))
        if not any(part in _EXCLUDED for part in path.relative_to(_SRC).parts)
    ]


def _model_calls(path: Path) -> list[tuple[int, ast.Call]]:
    """Calls to `<something>.complete(...)` / `.embed(...)` in one module.

    `super().complete(...)` is skipped: an override forwarding to its parent is
    not an originating call site and has no stage of its own to name.
    """
    tree = ast.parse(path.read_text())
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in _ATTRIBUTED_METHODS:
            continue
        receiver = node.func.value
        if isinstance(receiver, ast.Call) and getattr(receiver.func, "id", None) == "super":
            continue
        found.append((node.lineno, node))
    return found


def test_the_scan_finds_the_call_sites_it_is_meant_to_police():
    """Guards the test below from passing vacuously.

    An AST scan that matches nothing asserts nothing, and would keep passing
    through a rename of `complete` or a move of the package — reporting green
    while policing an empty set.
    """
    located = {
        str(path.relative_to(_SRC)): [line for line, _ in _model_calls(path)]
        for path in _product_modules()
        if _model_calls(path)
    }

    assert len(located) >= 8, f"scan found only {len(located)} modules with model calls: {located}"
    # A representative site from each end of the pipeline, named so that a move
    # is a visible test edit rather than a silent loss of coverage.
    assert "requirement/obligations.py" in located
    assert "coverage/declaration_comparison.py" in located


def test_no_review_pipeline_call_site_omits_its_stage():
    """Acceptance: a new `complete()` call site without `stage=` fails here."""
    offenders = [
        f"{path.relative_to(_SRC)}:{line}"
        for path in _product_modules()
        for line, call in _model_calls(path)
        if not any(keyword.arg == "stage" for keyword in call.keywords)
    ]

    assert not offenders, (
        "these review-pipeline model calls do not name the stage that issued them, "
        f"so their cost would aggregate as {UNKNOWN_STAGE!r}: {offenders}"
    )


_TASK = (
    "# Task\nThe formatter handles negative amounts.\n\n"
    "## Constraints\n- Negative amounts are formatted\n"
)

_JUDGMENTS = {
    "_Decomposition": {
        "obligations": [
            {
                "id": "formats-negatives",
                "description": "Negative amounts are formatted",
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
    (repo / "money.py").write_text("def fmt(x):\n    return f'{round(x, 2)}'\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head")
    return repo, base, _git(repo, "rev-parse", "HEAD")


def test_a_real_review_run_attributes_every_call_it_made(tmp_path):
    """The wiring, not the helper: a full `run_review` leaves no call unattributed.

    This is the test the scan cannot be: `complete()` could accept `stage=` and
    drop it on the floor, and every call site would still read correctly.
    """
    repo, base, head = _repo(tmp_path)
    client = client_dispatching(_JUDGMENTS)

    run_review(
        task_text=_TASK,
        change_set=extract_change_set(repo, base, head),
        repo=repo,
        client=client,
        reviewed_revision=head,
    )

    observed = client.observed_calls
    assert observed, "the pipeline ran but the client observed no calls at all"
    unattributed = [call for call in observed if call["stage"] == UNKNOWN_STAGE]
    assert not unattributed, f"{len(unattributed)} call(s) reported no stage: {unattributed}"
    # And each observation carries the four fields the aggregate needs.
    for call in observed:
        assert set(call) == {"stage", "key", "served_from", "usage"}
        assert call["served_from"] in {"provider", "recording"}
