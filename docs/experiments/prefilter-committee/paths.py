"""Where this experiment's external inputs live, and how to name them.

**These scripts were written and run somewhere else.** They came into the repo
carrying absolute paths into a container — `/root/exp`, `/root/head314` — that
exist nowhere here, so as committed they could not run and the numbers in
`FINDINGS.md` could not be checked. Nothing about the computation changed when
they were cleaned up; only where the inputs are named.

Three inputs are needed and none of them are, or should be, in the repo. Two are
worktrees at specific revisions and one is a review's own JSON, which embeds the
full requests sent to the model — the thing `.acceptance/` is gitignored to keep
out. Each is named by an environment variable, and a script that needs one it
was not given stops with a sentence saying which:

    ACCEPTANCE_HEAD316   worktree at 3e1d3a9, #316's Gate 2 head, carrying a
                         `.coverage` file from one instrumented run of the suite
                         at that revision (about 5m15s to produce)
    ACCEPTANCE_REVIEW316 that run's review JSON — defects with code_refs, the
                         change set, and 23,808 pair verdicts
    ACCEPTANCE_HEAD314   worktree at #314's Gate 2 head, likewise carrying a
                         `.coverage` file

Results are written beside the scripts rather than to the run directory, so a
re-run updates the committed record in place.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PAIR_PREFILTER = REPO / "docs" / "experiments" / "pair-prefilter"


def on_path() -> None:
    """Make `pair-prefilter`'s modules importable.

    That experiment holds the corpus loader, the locality voter, the embedding
    client and the scorer, and this one is a fourth voter bolted onto them
    rather than a reimplementation. Importing rather than copying is what keeps
    the two sets of figures comparable.
    """
    if str(PAIR_PREFILTER) not in sys.path:
        sys.path.insert(0, str(PAIR_PREFILTER))


def _required(name: str, what: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is not set; point it at {what}. See paths.py.")
    path = Path(value)
    if not path.exists():
        raise SystemExit(f"{name}={value} does not exist; it should be {what}.")
    return path


def head316() -> Path:
    return _required("ACCEPTANCE_HEAD316", "a worktree at 3e1d3a9 holding a .coverage file")


def review316() -> Path:
    return _required("ACCEPTANCE_REVIEW316", "the #316 Gate 2 review JSON")


def head314() -> Path:
    return _required("ACCEPTANCE_HEAD314", "a worktree at #314's Gate 2 head with .coverage")


def result(name: str) -> Path:
    """Where a script writes its findings: beside the script, not in the run dir."""
    return HERE / name
