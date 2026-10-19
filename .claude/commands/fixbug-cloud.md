---
description: Fix one backlog bug in a cloud session, unattended, with the checker run for data rather than as a gate
---

You are fixing one bug from the backlog in a cloud session with nobody watching.
Arguments, in order: `<issue number> <reserved files>`. The reserved files are
the ones other sessions running tonight are editing, comma-separated with no
spaces, or `none`. Example:
`/fixbug-cloud 243 src/acceptance/llm.py,src/acceptance/report.py`

$ARGUMENTS

Nothing here relaxes CLAUDE.md. Its invariants, the evidence discipline and the
sandbox rules all apply. What changes is only that the two dogfood gates do not
stop you: you run the tool, save what it said, and keep going. The human reads
every run's output in one sitting afterwards and records the corrections then.

## Where things are

- You may change whatever the fix needs under `src/`, `tests/` and
  `pyproject.toml`, with two exceptions.

  **Reserved files** (`<reserved files>`): another session is editing these
  right now, and two branches changing one file is a merge conflict for the
  human. Do not touch them. If the fix cannot be made without one, that is a
  BLOCKED outcome (step 4).

  **No-go list**, the same for every run, because a wrong change here is
  expensive or invisible: any prompt text or response schema (editing one
  orphans every recorded transcript for that stage and changes what the tool
  says); `review_state.py` and `review_store.py` (later milestones depend on
  the shape); the shared request-assembly code in `llm.py` that every stage's
  request passes through (a change there moves every stage's request key at
  once), unless the issue is about that code; `CLAUDE.md`, `docs/DEFERRED.md`,
  `session-state/`, `.claude/`. A fix that needs one of these is also BLOCKED.

  Everything else is yours. Keep the diff to what the issue asks for, but do
  not refuse a one-line change in a neighbouring module that the fix plainly
  needs; the point of this run is a landed fix, not a small diff.
- The run directory is `dogfood-logs/<issue>-headless/`. Everything you would
  normally write for a gate goes there. Unlike a normal task, this directory is
  committed on the branch, because the branch is the only thing that comes
  back from a cloud session.

## Setup (do this first, every time)

1. Create the branch: `git switch --no-track -c <issue>-headless`.
2. If `.venv/bin/acceptance` does not exist: `python3 -m venv .venv`, then
   `.venv/bin/pip install -e ".[dev]"`, then `.venv/bin/pip install litellm==1.96.2`
   (that pin works around #278, where an unpinned litellm cannot make a live
   call; drop it once #278 lands).
3. Provider keys arrive as environment variables, not as a `.env` file. If
   `.env` is absent, write one from the environment with
   `.venv/bin/python scripts/env-from-environ.py` (it copies only the
   `*_API_KEY` variables; `.env` is gitignored). Never print a key.
4. Fetch the issue text with the GitHub tool if one is available, otherwise
   `gh api repos/alipeles/acceptance-review/issues/<issue>`, and save the title
   and body as `dogfood-logs/<issue>-headless/issue.md`.

## Steps

1. **Write the task file.** Write `current-task.md` from the issue, ticket
   grade, as CLAUDE.md's Gate 1 describes: a narrative Task section saying
   what must be true when the bug is fixed, Constraints only where the issue
   states one, Scope exclusions for what the issue says to leave alone. The
   regression test that reproduces the defect is itself a deliverable here, so
   name it as one; do not pair any other requirement with "add a test".

   Leave the bug's history out. The issue explains where the defect was seen
   and why it matters; the task file says only what the software must do once
   it is fixed. A sentence that describes the current wrong behaviour, or how
   it was found, is background, and the decomposer has no obligation to derive
   from it (that is #355, where a span yielding nothing aborts the whole
   decomposition, and #212, where background becomes an obligation). The
   reproduction belongs in the regression test, not in the mandate.

   After writing the file, read it once more and delete every clause that
   compares the required behaviour to the current one: "rather than", "instead
   of", "as it does today", "as today", "no longer", "currently", "still". A
   sentence that says only what must be true needs none of them.

   The task file must not mention this run, the backlog, dogfooding, cloud
   sessions or headless work. Copy it to the run directory as well.

2. **Decompose, save, continue.** Run
   `.venv/bin/acceptance decompose --task current-task.md > dogfood-logs/<issue>-headless/decompose.log`
   and confirm the log is non-empty with `wc -c`. Do not wait for anyone to
   review it. Read it once and write into the run directory's `notes.md`,
   under a heading `Decompose`, two things: obligations you believe are
   invented or missing, and each open question with which of the three Gate 1
   cases you think it falls into. Then move on. A wrong question is noted, not
   acted on; that stop exists for an attended session.

   If `decompose` exits with an error instead of a breakdown, that is itself
   data: keep the log, write the error and the sentence it stopped on under
   `Decompose` in `notes.md`, and continue to step 3. Do not reword the task
   file to get past it, and do not stop. A crash here is a known tool defect,
   not a reason the bug cannot be fixed.

3. **Reproduce before fixing.** Write the regression test first, run it, and
   see it fail for the reason the issue describes. Paste the failing output
   into `notes.md` under `Reproduction`. If you cannot make it fail, stop:
   write `dogfood-logs/<issue>-headless/BLOCKED.md` saying what you tried and
   what you saw, commit and push just that directory, and end the session.

4. **Fix it.** If the correct fix needs a change to a reserved file or to
   anything on the no-go list, do not make it. Write `BLOCKED.md` naming the
   file and the change you would make, specific enough to approve or reject,
   commit and push just the run directory, and end the session. Those
   decisions are the human's. Anything else, make the change.

5. **Run the suite and the linters.** `.venv/bin/pytest -q`,
   `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`. All three
   must pass. A test elsewhere that fails because of your change means the fix
   is wrong or wider than the issue; do not edit that test to make it pass
   unless the issue says its old behaviour was the bug.

6. **Write the declaration before you look at the diff.** Write
   `dogfood-logs/<issue>-headless/declaration.md`: what you implemented, what
   you tested, what you left out, what you assumed, what you know is
   unverified. Write it from memory of what you did, not from `git diff`.

7. **Commit the fix.** Stage explicit paths only: the source and test files
   you changed. Never `git add -A`. Never stage
   `current-task.md`, `.acceptance/`, `.env`, `session-state/` or
   `docs/DEFERRED.md`. The subject must not start with `#`; use
   `fix: <what changed> (#<issue>)`.

8. **Run the checker from main, not from this branch.** Most of these bugs are
   edits to the checker itself, and the checker must not review its own fix.
   Make a second checkout of main and run its copy over this branch:

   ```
   git worktree add --no-track /tmp/main-checker origin/main
   python3 -m venv /tmp/main-checker/.venv
   /tmp/main-checker/.venv/bin/pip install -e "/tmp/main-checker[dev]"
   /tmp/main-checker/.venv/bin/pip install litellm==1.96.2
   /tmp/main-checker/.venv/bin/acceptance check --task current-task.md --base origin/main --head HEAD --mode record > dogfood-logs/<issue>-headless/check.log
   ```

   Run that last command from this repo's root, so the revisions resolve here.
   Confirm `check.log` is non-empty with `wc -c`; if it is empty, run it once
   more (CLAUDE.md records this happening before). Write
   `dogfood-logs/<issue>-headless/revisions.txt` with the `origin/main` and
   `HEAD` SHAs. Do not act on anything the check says. It is data for the
   human.

9. **Record what you noticed.** Anything outside this bug's scope, a smell, a
   second defect, a wrong comment, goes in `notes.md` under `Deferred`, in the
   `docs/DEFERRED.md` entry format from CLAUDE.md. Do not fix it and do not
   file it.

10. **Commit the run directory, push, open a draft PR.** Second commit,
    staging only `dogfood-logs/<issue>-headless/`, subject
    `dogfood: headless run for #<issue>`. Then
    `git push -u origin <issue>-headless`.

    Open a **draft** pull request from `<issue>-headless` to `main`, titled
    `fix: <what changed> (#<issue>)`. Its body, in this order: one sentence
    saying what the fix does; the checker's completion verdict and each
    obligation it rated below strongly supported, copied from `check.log`
    (or the one-line error if it crashed); the declaration; and anything
    under `Deferred` in `notes.md`. Use the GitHub tool if one is available,
    otherwise `gh api repos/alipeles/acceptance-review/pulls` with
    `draft: true`. A draft cannot be merged by accident; merging is the
    human's decision and never yours. If the run ended in `BLOCKED.md`, open
    the draft anyway with the block as its body, so every run is reviewed
    from one list.

## What "done" looks like from the outside

Branch `<issue>-headless` on origin with two commits: the fix and its tests, and the run directory holding `issue.md`,
`current-task.md`, `decompose.log`, `notes.md`, `declaration.md`,
`check.log` and `revisions.txt`. Or one commit holding only `BLOCKED.md`. Both
are good outcomes. A fix with no failing-then-passing test in `notes.md` is the
bad outcome, and the human will treat it as unverified.
