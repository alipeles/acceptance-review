# Notes — #350 headless run

## Decompose

Run `50763f82a579811a`, 14 obligations from 4 requirements, no open questions.

Invented or redundant obligations, as I read it:

- `pair-judgement-defect-counts` and `report-covers-unattempted-defects` are fair,
  but the second is a restatement of the first restricted to a sub-case.
- `pair-counts-correct` ("correct, not merely present") is a framing sentence with
  no content of its own; the two obligations after it carry what "correct" means.
- `no-edit-built-for-it` turns a premise ("no edit was built for it") into an
  invariant. It is background for why the counts are what they are, and the
  obligation it would yield (settled = 0) is already in
  `all-pairs-counted-as-put-to-judge`'s neighbourhood.
- task-03 was split five ways (`render-review-with-two-defects`,
  `judge-pairs-for-both-defects`, `pairs-went-to-judge`,
  `pin-exact-counts-report-states`, `regression-test-pins-exact-counts`). That is
  one deliverable, a regression test; four of the five are fragments of its
  description, and three of them are near-duplicates of each other.
- `routing-unchanged` is a fair reading of the scope exclusion.

Missing: none that I can see.

Open questions: none raised.

## What I found before writing the test

The issue says a `not_mutable` or `not_attempted` defect gets no pair-count
line. On this branch's base (`80511ee`) that is no longer true: `_mutation_block`
in `src/acceptance/report.py` calls `_pair_disposition` for every attempt, and
the runner records an attempt for every defect. The line is present. What is
still wrong is the number in it, which is the issue's second Acceptance item
("correct, not merely present").

I saw this through the real pipeline first (the `_DECLINING` fixture in
`tests/test_mutation_pipeline_wiring.py`, a `not_mutable` defect with one pair
the judge left unanswered). The same report said two different things about
one defect:

```
Ways the change could fail a criterion ...
    [other] equal-payments/wrong-payment-amount
      pairs: 1 put to the model, 0 skipped once the defect was covered
...
Defects injected, and which tests caught them:
  [not_mutable] equal-payments/wrong-payment-amount
    pairs: 0 settled by the run, 0 put to the model, 0 dropped as not worth asking, 0 skipped once the defect was covered
```

`_pair_counts` (the defect section) counts unanswered pairs as asked;
`_pair_disposition` (the injection section) counted only pairs with a verdict.

## Reproduction

`tests/test_pair_counts_without_an_attempt.py`, before the fix:

```
E         At index 0 diff: 'pairs: 0 settled by the run, 2 put to the model, 0 dropped as not worth asking, 0 skipped once the defect was covered' != 'pairs: 0 settled by the run, 3 put to the model, 0 dropped as not worth asking, 0 skipped once the defect was covered'
tests/test_pair_counts_without_an_attempt.py:113: AssertionError
...
E         At index 0 diff: 'pairs: 0 settled by the run, 1 put to the model, 0 dropped as not worth asking, 0 skipped once the defect was covered' != 'pairs: 0 settled by the run, 2 put to the model, 0 dropped as not worth asking, 0 skipped once the defect was covered'
tests/test_pair_counts_without_an_attempt.py:121: AssertionError
FAILED tests/test_pair_counts_without_an_attempt.py::test_a_not_mutable_defect_counts_every_pair_as_put_to_the_judge
FAILED tests/test_pair_counts_without_an_attempt.py::test_a_not_attempted_defect_counts_every_pair_as_put_to_the_judge
2 failed, 1 passed in 0.15s
```

The third test (the defect section's count) passed before the fix, as expected:
that section was already right. After the fix: `3 passed in 0.15s`.

`tests/test_mutation_pipeline_wiring.py::test_the_pair_counts_are_stated_even_when_they_are_all_zero`
asserted the wrong "0 put to the model" and failed after the fix; I changed it
to "1 put to the model", because that old count is the defect the issue
describes.

## Suite and linters

After the fix and after fetching the corpus tags: `.venv/bin/pytest -q` →
`1879 passed, 2 xfailed in 397.79s`. `ruff check .` → `All checks passed!`.
`ruff format --check .` → `262 files already formatted`. ruff 0.16.2.

The checker was run from a detached checkout of main at
`/tmp/main-checker-350`, not `/tmp/main-checker`: a first attempt at that path
failed on `--no-track` (which `git worktree add` only accepts with a new
branch) and left a stray `.venv` there that I was not allowed to delete.

## Check

`check.log` (46,017 bytes), run from main's copy of the checker. The first
attempt was stopped by this session's 10-minute command limit and left a
zero-byte log; the second ran to completion. Verdict: `INCOMPLETE`, because
`render-review-with-two-defects` (the regression test renders a review holding
one `not_mutable` and one `not_attempted` defect) is only partially supported,
kills 1 of 2 enumerated defects. Its recommended test describes inputs the new
test already has (a `not_mutable` defect with three pairs, a `not_attempted`
one with two, different totals), and the only test mapped to it is an unrelated
wiring test, not `tests/test_pair_counts_without_an_attempt.py`. I believe this
is a mapping miss rather than missing evidence, but I did not act on it, as
instructed. Four obligations got "no plausible defect" and one regression-test
obligation was "indeterminate". Two unrequested changes were raised, both
`in_service`, and both are the fix itself.

## Deferred

### [2026-10-19] Test suite fails in a fresh clone that has not fetched corpus tags
- **Kind:** defect
- **Found during:** #350, headless run
- **Where:** tests/benchmark/test_corpus.py, tests/benchmark/test_rating_regression.py
- **Severity:** nice-to-have
- **What's wrong:** In this cloud session's clone, 11 benchmark tests failed
  with `UnresolvableRevisionError` for case `163-gate2-run1`, on main as well as
  on this branch. The tag `corpus/163-gate2-run1` is on origin, but neither the
  initial clone nor `git fetch --unshallow` brought it in; `git fetch origin
  'refs/tags/corpus/*:refs/tags/corpus/*'` did, and then all 62 tests passed.
  This may be the same cause as the "local pytest collects fewer tests than CI"
  investigation CLAUDE.md exempts from the gates.
- **Why I didn't act:** out of scope for #350; it is a clone setup issue.
- **Drafted fix:** add the explicit tag fetch to the cloud setup steps (the
  `fixbug-cloud` skill's Setup), or have the corpus error message name the
  fetch command.
- **Status:** open

### [2026-10-19] Defect section's pair line has no settled count
- **Kind:** decision
- **Found during:** #350, headless run
- **Where:** src/acceptance/report.py, `_defect_block`
- **Severity:** nice-to-have
- **What's wrong:** The defect section says "N put to the model, M skipped" and
  the injection section says "settled, put to the model, dropped, skipped". When
  the execution tier did not run there is no injection section, so a defect's
  settled and dropped counts are never stated (they are zero). Two lines for one
  fact, with different fields.
- **Why I didn't act:** the issue is about defects that have an injection record
  with no edit; merging the two lines changes every report's text.
- **Drafted fix:** recommend rendering one four-count line, in the defect
  section only, and dropping it from the injection section. Alternative
  rejected: adding "0 settled" to the defect line, which keeps two lines that
  can drift apart again.
- **Status:** open

### [2026-10-19] Wiring test name says "all zero" but its counts are not
- **Kind:** defect
- **Found during:** #350, headless run
- **Where:** tests/test_mutation_pipeline_wiring.py, `test_the_pair_counts_are_stated_even_when_they_are_all_zero`
- **Severity:** nice-to-have
- **What's wrong:** After this fix the test asserts "1 put to the model", so the
  name no longer describes it. I did not rename it, to keep the diff small.
- **Drafted fix:** rename to `test_the_pair_counts_are_stated_for_a_defect_no_edit_was_built_for`.
- **Status:** open
