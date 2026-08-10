"""Rating-stability corpus -> benchmark cases (#190).

`tests/fixtures/rating-stability/` records six dogfood runs of `acceptance
check`: the task file each was given, the report it produced, and — the
expensive part — a `judgement.md` saying which findings were real gaps and
which were tool defects. Until those judgements are assertions, every
candidate fix to the evidence-judgement stage is accepted by eyeball, and
DR-180's load-bearing criterion (`strongly supported` is not issued on
evidence that does not earn it) has no scoreboard.

## Why these cases are not archetypes

`fixtures.py` materializes an archetype by copying a hand-built `base/` and
`head/` tree into a fresh two-commit repo. Nothing is copied here. The corpus
runs judged **real commits in this repository**, and `revisions.txt` names
them, so a case supplies the input the run actually had rather than a
reconstruction of it. That is strictly higher fidelity: the instability the
corpus documents happened over *these* diffs, and a synthetic stand-in would
be evidence that it can happen, not that it did.

The trade is that a case depends on this repository's history. A revision that
stops resolving fails its case by name (`UnresolvableRevisionError`) rather
than skipping quietly — a regression suite that silently shrinks is worse than
one that breaks.

**The `corpus/*` tags are load-bearing. Do not delete them.** Every head
revision here was squash-merged, so none is reachable from `main` — the tags are
the only thing keeping those objects alive, and a fresh clone gets them only
because the tags exist. CI must also check out with `fetch-depth: 0`; the default
shallow clone has none of this history. Both facts were discovered the direct
way, by CI failing on a clone that lacked what a working copy happened to have.

## Why a worktree

`evidence/discovery.py` scans the **filesystem** for `test_*.py`, not the git
revision. Pointing a case at the live repository would therefore discover
today's tests against a years-old diff — tests that did not exist when the run
was made, and none of the ones later deleted. So each case is analysed in a
detached worktree at its head revision. A worktree shares the object store, so
it is cheap and both revisions stay resolvable inside it.

## What is deliberately not here

No model transcript is recorded or committed. A transcript embeds the full
request, so recording against these revisions would place this repository's own
diffs and task text into `tests/fixtures/` — exactly what the corpus README
says was avoided when it stored rendered reports instead. The judgement a case
is scored under is supplied by a stub in the test, which is also why the suite
scores the deterministic reduce in `evidence/strength.py` and the wiring around
it rather than the judgement prompt.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from acceptance.benchmark.case import (
    BenchmarkCase,
    BenchmarkCaseInputs,
    BenchmarkCaseSource,
    GroundTruthLabels,
    require_nonempty_registry,
)
from acceptance.model_base import PersistableModel


class UnresolvableRevisionError(RuntimeError):
    """A case names a revision this repository no longer has.

    Raised rather than skipped: these cases are pinned to real history, so a
    rewritten or pruned commit silently removing a case would let the suite
    shrink without anyone noticing.
    """


class CorpusCaseMeta(PersistableModel):
    """A corpus run reduced to what a case needs, plus its provenance.

    `corpus_run` points at the directory under `tests/fixtures/rating-stability/`
    the case is derived from, and `judgement` records which reading of that run's
    `judgement.md` is ground truth — load-bearing for runs 3 and 5, whose
    judgements were rewritten and which preserve both the original and the
    corrected reading.
    """

    corpus_run: str
    base_revision: str
    head_revision: str
    judgement: str
    summary: str


@dataclass(frozen=True)
class MaterializedCorpusRun:
    worktree: Path
    base_sha: str
    head_sha: str
    meta: CorpusCaseMeta


def load_corpus_meta(case_dir: Path) -> CorpusCaseMeta:
    return CorpusCaseMeta.from_dict(json.loads((case_dir / "case.json").read_text()))


def load_labels(case_dir: Path) -> GroundTruthLabels:
    return GroundTruthLabels.from_dict(json.loads((case_dir / "labels.json").read_text()))


def corpus_task_text(corpus_root: Path, meta: CorpusCaseMeta) -> str:
    """The exact task file the run was given, read from the corpus itself.

    Read rather than copied: the corpus is the evidence record, and a second
    copy under the case directory could drift from it.
    """
    return (corpus_root / meta.corpus_run / "current-task.md").read_text()


def resolve_case_revisions(case_dir: Path, repo: Path) -> tuple[str, str]:
    """This case's (base, head) as full SHAs, without materializing anything.

    Separate from materialization so the whole suite's pinning can be checked
    cheaply — one `rev-parse` per revision rather than a worktree per case.
    """
    meta = load_corpus_meta(case_dir)
    return (
        _resolve(repo, meta.base_revision, meta.corpus_run),
        _resolve(repo, meta.head_revision, meta.corpus_run),
    )


def materialize_corpus_run(case_dir: Path, repo: Path, dest: Path) -> MaterializedCorpusRun:
    """Check out this case's head revision into a detached worktree of `repo`."""
    meta = load_corpus_meta(case_dir)
    base, head = resolve_case_revisions(case_dir, repo)

    dest.parent.mkdir(parents=True, exist_ok=True)
    _git(repo, "worktree", "add", "--detach", "--quiet", str(dest), head)

    return MaterializedCorpusRun(worktree=dest, base_sha=base, head_sha=head, meta=meta)


def remove_corpus_worktree(repo: Path, dest: Path) -> None:
    """Drop a materialized worktree and its registration in `repo`.

    Registration lives in the main repository's `.git`, so deleting the
    directory alone leaves an entry behind; `--force` because the review under
    test may have left the tree dirty.
    """
    subprocess.run(
        ["git", "worktree", "remove", "--force", str(dest)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    _git(repo, "worktree", "prune")


def build_corpus_case(case_dir: Path, repo: Path, corpus_root: Path, dest: Path) -> BenchmarkCase:
    """Materialize a corpus run and assemble its labeled BenchmarkCase."""
    # Checked before materializing a worktree, for the reason
    # `build_benchmark_case` gives. These runs are `check` runs rather than
    # `decompose` runs, but an unreadable task file costs them more, not less:
    # the whole pipeline downstream of decomposition would run over no
    # obligations and report that it found nothing wrong.
    require_nonempty_registry(
        case_dir.name, corpus_task_text(corpus_root, load_corpus_meta(case_dir))
    )

    run = materialize_corpus_run(case_dir, repo, dest)
    return BenchmarkCase(
        case_id=case_dir.name,
        # These are recorded runs of this tool over real work, which is what
        # `agent_run` names; they are not hand-built archetypes.
        source=BenchmarkCaseSource(kind="agent_run", identifier=run.meta.corpus_run),
        inputs=BenchmarkCaseInputs(
            repo=str(run.worktree),
            task_text=corpus_task_text(corpus_root, run.meta),
            base_revision=run.base_sha,
            head_revision=run.head_sha,
        ),
        ground_truth=load_labels(case_dir),
    )


class MissingRunInputError(RuntimeError):
    """A decompose case names a run whose task file is not there.

    The decompose analogue of `UnresolvableRevisionError`, and raised for the
    same reason: a case that quietly skips itself lets the suite shrink without
    anyone noticing. `decompose` takes only a task file, so that file is the
    whole input — losing it is losing the case.
    """


class DecomposeCaseMeta(PersistableModel):
    """A decompose run reduced to what a case needs, plus its provenance.

    `run_dir` is repo-relative rather than a name under a fixed root, because
    these runs do not all live in one place: seven are corpus runs under
    `tests/fixtures/decompose-stability/`, and the eighth is this task's own
    Gate 1 run under `dogfood-logs/`. Putting the eighth into the corpus
    directory would have meant modifying the corpus, which is what the case set
    exists to measure against.

    `judgement` records which reading of that run's `judgement.md` is ground
    truth — load-bearing for runs 4 and 6, whose judgements were made wrong and
    which preserve both the original and the corrected reading.

    There are no revisions. `decompose` takes a task file and nothing else, so
    unlike the rating-stability cases there is no diff to pin and nothing to
    materialize.
    """

    run: str
    run_dir: str
    judgement: str
    summary: str


def load_decompose_meta(case_dir: Path) -> DecomposeCaseMeta:
    return DecomposeCaseMeta.from_dict(json.loads((case_dir / "case.json").read_text()))


def decompose_task_text(repo: Path, meta: DecomposeCaseMeta) -> str:
    """The exact task file the run was given, read from the run's own directory.

    Read rather than copied, for the reason `corpus_task_text` gives: the run
    directory is the evidence record, and a second copy under the case directory
    could drift from it.
    """
    path = repo / meta.run_dir / "current-task.md"
    if not path.is_file():
        raise MissingRunInputError(
            f"case {meta.run!r} names {meta.run_dir!r}, which has no "
            f"current-task.md. That file is the entire input to `decompose`, so "
            f"the case fails here rather than skipping itself and shrinking the "
            f"suite silently."
        )
    return path.read_text()


def build_decompose_case(case_dir: Path, repo: Path) -> BenchmarkCase:
    """Assemble a labeled BenchmarkCase for one decompose run."""
    meta = load_decompose_meta(case_dir)
    task_text = decompose_task_text(repo, meta)
    # `decompose` is the only stage these cases exercise, so an empty registry
    # here means the case measures nothing at all: no batch is issued, no model
    # call is made, and decomposition_accuracy reports 0.0 against ground truth
    # the input never had a chance to produce.
    require_nonempty_registry(case_dir.name, task_text)

    return BenchmarkCase(
        case_id=case_dir.name,
        source=BenchmarkCaseSource(kind="agent_run", identifier=meta.run),
        inputs=BenchmarkCaseInputs(
            # No repo tree and no diff are read: the decompose hook parses
            # task_text and stops. `repo` is carried so a case that is later
            # extended to a full review has somewhere to start.
            repo=str(repo),
            task_text=task_text,
            # Empty rather than a plausible-looking SHA. These runs recorded no
            # revision — `decompose` does not take one — and a fabricated value
            # would be an invented input in a case set whose whole argument is
            # that its inputs are real.
            base_revision="",
            head_revision="",
        ),
        ground_truth=load_labels(case_dir),
    )


def _resolve(repo: Path, revision: str, corpus_run: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{revision}^{{commit}}"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise UnresolvableRevisionError(
            f"case {corpus_run!r} names revision {revision!r}, which this "
            f"repository no longer resolves. The corpus cases are pinned to real "
            f"history; a rewritten or pruned commit breaks them by design rather "
            f"than shrinking the suite silently."
        )
    return result.stdout.strip()


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)
