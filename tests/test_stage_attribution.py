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

That exclusion had a hole, found at #313's Gate 1. `requirement/carry.py`
imports `align_obligations` from the benchmark harness, so its model call was
made *by* a review and *from* a module the scan skips, and landed in the
`unknown` bucket on every continued run whose requirement text moved. The scan
below now follows imports out of `benchmark/` as well, and a wiring test drives
the carry path itself.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import acceptance
from acceptance.change.diff import extract_change_set
from acceptance.cli import main
from acceptance.llm import UNKNOWN_STAGE
from acceptance.pipeline import run_review
from acceptance.report import render_report
from acceptance.usage import render, summarize
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


def _benchmark_imports(path: Path) -> set[str]:
    """Names a review-pipeline module pulls in from `acceptance.benchmark`.

    Such a name is a model call the scan above cannot see: the call site is in
    `benchmark/`, which is excluded, but the spend belongs to the review that
    triggered it.
    """
    tree = ast.parse(path.read_text())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
            "acceptance.benchmark"
        ):
            names.update(alias.asname or alias.name for alias in node.names)
    return names


def test_the_import_scan_still_finds_the_one_crossing_it_polices():
    """Guards the test below from passing vacuously, as its sibling does.

    If `align_obligations` moves into the pipeline the crossing disappears and
    this fails — which is the right outcome, and a visible test edit rather than
    a scan that quietly polices nothing.
    """
    crossings = {
        str(path.relative_to(_SRC)): sorted(_benchmark_imports(path))
        for path in _product_modules()
        if _benchmark_imports(path)
    }

    assert crossings == {"requirement/carry.py": ["align_obligations"]}, (
        f"the set of review-pipeline modules reaching into benchmark/ changed: {crossings}"
    )


def test_no_call_into_benchmark_from_the_pipeline_omits_its_stage():
    """Acceptance: the crossing that produced the `unknown` row cannot recur.

    `benchmark/` is excluded from the scan above because its own spend is not a
    review's. A pipeline module that imports from it inherits the review's
    obligation to attribute, so the call must name a stage here instead.
    """
    offenders = []
    for path in _product_modules():
        imported = _benchmark_imports(path)
        if not imported:
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id not in imported:
                continue
            if not any(keyword.arg == "stage" for keyword in node.keywords):
                offenders.append(f"{path.relative_to(_SRC)}:{node.lineno} {node.func.id}")

    assert not offenders, (
        "these calls run a model on the review's behalf from inside benchmark/, "
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
        assert set(call) == {"stage", "key", "served_from", "model", "usage"}
        assert call["served_from"] in {"provider", "recording"}


# Fragments that would betray the breakdown if it leaked into a persisted review
# or a rendered report. Matched case-insensitively against the whole text.
_COST_MARKERS = (
    "model usage by stage",
    "cost_usd",
    "run_spend",
    "evidence_cost",
    "cached_tokens",
    "served_from",
    "replayed",
)


def _leaks(text: str) -> list[str]:
    lowered = text.lower()
    return [marker for marker in _COST_MARKERS if marker in lowered]


def test_the_breakdown_never_reaches_review_state(tmp_path):
    """Acceptance: cost stays out of the persisted review.

    Not a stylistic boundary — a determinism one. Cost differs between two
    recordings of the same review (a replayed call spends nothing where the run
    that recorded it spent money), so a review carrying it could never be
    byte-identical across runs, and M0.5 would be unsatisfiable.
    """
    repo, base, head = _repo(tmp_path)
    client = client_dispatching(_JUDGMENTS)

    review = run_review(
        task_text=_TASK,
        change_set=extract_change_set(repo, base, head),
        repo=repo,
        client=client,
        reviewed_revision=head,
    )

    # The run really did produce a breakdown, and the markers really do trip on
    # one — otherwise this test asserts the absence of a thing it cannot detect.
    assert client.observed_calls
    assert summarize(client.observed_calls).stages
    assert _leaks(render(summarize(client.observed_calls)))

    leaked = _leaks(review.to_canonical_json())
    assert not leaked, f"the persisted review carries cost accounting: {leaked}"


def test_the_breakdown_never_reaches_the_rendered_report(tmp_path):
    """Acceptance: the §16 report says nothing about what the run cost."""
    repo, base, head = _repo(tmp_path)
    client = client_dispatching(_JUDGMENTS)

    review = run_review(
        task_text=_TASK,
        change_set=extract_change_set(repo, base, head),
        repo=repo,
        client=client,
        reviewed_revision=head,
    )

    assert summarize(client.observed_calls).stages
    assert _leaks(render(summarize(client.observed_calls)))
    leaked = _leaks(render_report(review))
    assert not leaked, f"the rendered report carries cost accounting: {leaked}"


def test_two_runs_whose_calls_cost_different_amounts_still_agree_byte_for_byte(tmp_path):
    """The property the two tests above protect, exercised directly.

    A review that leaked cost would pass an absence check written against the
    wrong spelling and still diverge here. This varies the usage between two
    otherwise identical runs and demands the review state be unchanged.
    """
    repo, base, head = _repo(tmp_path)
    change_set = extract_change_set(repo, base, head)

    def once(usage):
        client = client_dispatching(_JUDGMENTS, usage=usage)
        review = run_review(
            task_text=_TASK,
            change_set=change_set,
            repo=repo,
            client=client,
            reviewed_revision=head,
        )
        return review.to_canonical_json(), render_report(review), client.observed_calls

    cheap_state, cheap_report, cheap_calls = once({"prompt_tokens": 10})
    dear_state, dear_report, dear_calls = once({"prompt_tokens": 9000})

    # The two runs really did consume different amounts. (Tokens, not dollars:
    # `cost_usd` is priced by the provider library from a real response, so a
    # hand-built double cannot set it — and tokens are what it is priced from.)
    def prompt_tokens(calls):
        return sum(stage.prompt_tokens for stage in summarize(calls).stages)

    assert prompt_tokens(cheap_calls) != prompt_tokens(dear_calls)
    assert cheap_state == dear_state
    assert cheap_report == dear_report


def test_the_check_command_prints_the_per_stage_breakdown(
    git_repo, fixture_task_path, capsys, stub_model
):
    """Acceptance: the CLI actually surfaces it, on stderr and not on stdout.

    Both halves matter. A breakdown nobody prints answers nothing; a breakdown
    printed to stdout would put an unreproducible figure into the output the
    dogfood logs capture, which is precisely what keeps two runs byte-identical.
    """
    exit_code = main(
        [
            "check",
            "--task",
            fixture_task_path,
            "--base",
            git_repo["base"],
            "--head",
            git_repo["head"],
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Model usage by stage:" in captured.err
    assert "this run spent $" in captured.err
    assert "the evidence cost $" in captured.err
    assert "Model usage" not in captured.out


def test_the_decompose_command_prints_the_per_stage_breakdown_too(
    fixture_task_path, capsys, stub_model
):
    """Gate 1 spends money as well, so it reports what it spent."""
    exit_code = main(["decompose", "--task", fixture_task_path])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Model usage by stage:" in captured.err
    assert "Model usage" not in captured.out
