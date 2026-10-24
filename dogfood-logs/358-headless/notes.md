# Notes — #358 headless run

Branch: the session was assigned `claude/benchmark-instability-358-c1xz56`, and
the harness forbids pushing to any other branch, so this run uses that branch
instead of `358-headless`.

## Decompose

Run `869524bf1aee2422`, 5 requirements, no open questions.

Invented or doubtful obligations:
- `not-prefiltered` — "The requirement is not prefiltered." Garbled: it splits the
  tail of the regression-test sentence into a separate obligation about "the
  requirement", which is not a thing that can be prefiltered. It duplicates
  `non-python-file-content-test-judged`. I believe this is a decomposition defect
  (splitting one clause into two, and losing the subject).
- `python-module-limited-proof` — derived from my explanatory sentence ("Its
  proof follows imports, fixtures and Python names, so it holds only for defects
  that live in Python modules"). That sentence is background; my wording invited
  it. Not a tool defect.
- `no-exclusion-for-non-python-implicated-files` and
  `all-pairs-sent-to-judge-for-defect` say the same thing twice. My sentence
  said it twice (with a colon), so this is my wording, not the tool.

Missing: none that I can see.

Open questions: none raised.

## Reproduction

Before the fix, the two new tests in `tests/defects/test_reachability.py`
failed with the reason string the issue quotes:

```
FAILED tests/defects/test_reachability.py::test_judges_a_test_that_reads_a_non_python_implicated_file
E   Left contains one more item: UnjudgedPair(defect_id='d-hard-coded-thirty', test_id='test_findings.py::test_findings_figure', cause=<UnjudgedCause.P...no fixture, and it references no name defined in FINDINGS.md — no path to the defect exists", rank=None, covered_by=[])

FAILED tests/defects/test_reachability.py::test_judges_when_any_implicated_file_is_not_python
E   Left contains one more item: UnjudgedPair(defect_id='d-hard-coded-thirty', test_id='test_arithmetic.py::test_unrelated', cause=<UnjudgedCause.PREFI...and it references no name defined in billing.py, config.toml — no path to the defect exists", rank=None, covered_by=[])

2 failed, 8 passed in 0.30s
```

After the fix: all 10 tests in that file pass. Full suite: 1867 passed,
11 failed, 2 xfailed. Ruff check and ruff format --check both clean (ruff 0.16.2).

The 11 failures are all corpus case `163-gate2-run1`: its revision `41cd0da` and
tag `corpus/163-gate2-run1` are not on origin (checked after
`git fetch --unshallow` and fetching all branches). I verified the same 11 fail
on a clean checkout of `origin/main` at 80511ee
(`11 failed, 51 passed` over `test_rating_regression.py` + `test_corpus.py`).

## Check

Run `c69a1f9f6d3082e3`, from a checkout of main at 80511ee over this branch.
Verdict: INCOMPLETE. Not acted on, per the run's rules.

- `preserve-existing-prefilter-rules-for-python-only-defects` — unsupported, 0 of
  1. The injected change that survived made the suffix check skip any path
  containing `/`. I believe that change does not break this obligation (it makes
  the filter exclude *more*, not less), so the defect is misfiled under the
  wrong obligation. But it shows a real gap in my tests: both new tests use
  root-level paths (`FINDINGS.md`, `config.toml`), and the issue's real case is
  `docs/experiments/rank-prefilter/FINDINGS.md`. No test pins a non-Python file
  in a subdirectory, so that mutant survives. A one-line test change would close
  it.
- `non-python-file-content-test-judged` — indeterminate, no defect enumerated,
  no mapped test. I believe the mapping missed
  `test_judges_a_test_that_reads_a_non_python_implicated_file`, which is that
  test word for word.
- `not-prefiltered` and `python-module-limited-proof` came from the decompose
  issues noted above.
- All six "killed" results are NOT COUNTED because edit verification is off.
- Unrequested change 2 calls the mixed-file test `separable`. I believe the
  mandate's "When any of a defect's implicated files is not a Python module"
  covers it, so this is a misreading.

## Deferred

### [2026-10-20] Corpus case 163-gate2-run1 names a revision and tag origin does not have
- **Kind:** defect
- **Found during:** #358, headless run
- **Where:** tests/benchmark/test_corpus.py, tests/benchmark/test_rating_regression.py (corpus case `163-gate2-run1`)
- **Severity:** should-fix
- **What's wrong:** A fresh clone, even fully unshallowed, cannot resolve revision `41cd0da` and has no tag `corpus/163-gate2-run1`, so 11 tests fail on main. Either the tag was never pushed or the commit was rewritten.
- **Why I didn't act:** out of scope for #358, and the fix is pushing a tag from a machine that still has the commit.
- **Drafted fix:** from a clone that has `41cd0da`, `git tag corpus/163-gate2-run1 41cd0da && git push origin corpus/163-gate2-run1`. If no clone has it, the case needs re-pinning, which is a human call.
- **Status:** open

### [2026-10-20] Decomposer split a sentence's tail into a subject-less obligation
- **Kind:** filing (child of #181, the decomposition umbrella)
- **Found during:** #358, headless run, decompose
- **Where:** `dogfood-logs/358-headless/decompose.log`, obligation `not-prefiltered`
- **Severity:** nice-to-have
- **What's wrong:** "...paired with a defect implicating that file, is judged and not prefiltered" yielded both a correct obligation and `not-prefiltered` — "The requirement is not prefiltered", which names the wrong subject and duplicates the first.
- **Why I didn't act:** decomposition prompts are on the no-go list for this run.
- **Drafted fix:** file under #181 with this log as evidence; likely the same family as other duplicate-obligation defects there.
- **Status:** open
