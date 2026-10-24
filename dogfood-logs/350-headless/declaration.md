# Declaration — #350

## What I implemented

In `src/acceptance/report.py::_pair_disposition`, the "put to the model" count
now comes from `_pair_counts`, the same function the defect block already used.
Before, `_pair_disposition` counted only pairs with a static verdict, so a pair
the judge was offered and did not answer (`UnjudgedCause.UNANSWERED`) was left
out of the injection section's count while the defect section counted it.

The per-defect line itself was already rendered for every attempt, including
`not_mutable` and `not_attempted` ones: the early return the issue describes was
removed before this branch (commit `2f774c0`, per the issue). So the remaining
defect was the count being wrong, not the line being missing. The issue's second
Acceptance item ("correct, not merely present") is what this fixes.

## What I tested

- New `tests/test_pair_counts_without_an_attempt.py`: a review built directly
  with one `not_mutable` defect (two answered pairs and one unanswered) and one
  `not_attempted` defect (one answered and one unanswered). It pins the exact
  injection-section line for each (`0 settled, 3 put to the model, 0 dropped,
  0 skipped` and `0, 2, 0, 0`), and that the defect section states the same
  asked count. The two exact-count tests failed before the fix (2 and 1 put to
  the model) and pass after.
- Changed `tests/test_mutation_pipeline_wiring.py::test_the_pair_counts_are_stated_even_when_they_are_all_zero`
  from "0 put to the model" to "1 put to the model". That test runs the real
  pipeline with a declining descriptor (`not_mutable`) whose one pair comes back
  unanswered, so its old assertion pinned exactly the wrong count the issue
  describes.
- Full suite. My first run had 11 failures in `tests/benchmark/test_corpus.py`
  and `tests/benchmark/test_rating_regression.py`, all because this session's
  clone had not fetched the git tag `corpus/163-gate2-run1` (it is on origin).
  The same 11 failed on an unmodified checkout of main. After fetching the
  corpus tags they pass; the final full-suite result is in `notes.md`.
- `ruff check .` and `ruff format --check .` pass (ruff 0.16.2).

## What I left out

- A review where the execution tier did not run at all has no injection section,
  so a defect there has only the defect section's shorter line ("N put to the
  model, M skipped"), with no settled or dropped count. I read the issue as being
  about defects that have an attempt record with no edit, since every defect gets
  an attempt record whenever injection runs (`mutation/runner.py`). Not changed.
- No change to how pairs are routed.

## What I assumed

- That an unanswered pair counts as "put to the judge". `_pair_counts`'s
  docstring already says so ("a pair that came back unanswered still cost the
  call"), and the issue says "all of its pairs put to the judge".

## What I know is unverified

- I did not render a real review from a live run to look at the output; the
  evidence is the two tests above.
