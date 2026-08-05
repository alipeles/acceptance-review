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


def build_corpus_case(
    case_dir: Path, repo: Path, corpus_root: Path, dest: Path
) -> BenchmarkCase:
    """Materialize a corpus run and assemble its labeled BenchmarkCase."""
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
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    )
