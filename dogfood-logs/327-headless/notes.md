# Notes — #327 headless run

Branch: the session harness assigned `claude/fixbug-cloud-327-ohj6zw` and forbids
pushing elsewhere, so the work is on that branch rather than `327-headless`.

## Decompose

Run `ad407d0971e46703`, 5 requirements, 11 obligations, no open questions.

Invented or redundant, I believe:

- `no-defect-set` ("The change produces no defect set") lost its subject. The
  requirement says a criterion owed no test produces no defect set; as worded the
  obligation reads as if the whole change produces none, which the fix must not
  do. A decomposition defect (a clause split off from the sentence that gives it
  its subject).
- `task-01` splits into four obligations that say one thing:
  `enumerator-only-owed-test-evidence`, `no-test-evidence-criteria-not-enumerated`
  and `no-enumeration-call-for-no-test-evidence` are the same requirement stated
  three ways in my own task file. Linking did not merge them. Part of that is my
  wording (the task paragraph says the rule, then restates its consequence).
- `task-02` likewise: `criteria-decided-from-decomposition-alone` and
  `test-independence-from-existing-tests` are one requirement.

Missing: none that I can see.

Open questions: none raised.

I dropped the issue's third Acceptance item ("note the cost where the figures
render") from the task file. It is about how we report re-recording cost, which
is something we do, not something the software does, and the only candidate
place for it in code (`report.py`) is reserved by another session tonight.

## Reproduction

`tests/defects/test_enumeration.py::test_a_criterion_owed_no_test_is_never_offered_to_the_enumerator`,
run before the fix in `pipeline.py`:

```
>       assert not any(_EXCLUSION_QUOTE in prompt for prompt in enumeration)
E       assert not True
E        +  where True = any(<generator object test_a_criterion_owed_no_test_is_never_offered_to_the_enumerator.<locals>.<genexpr> at 0x7f42118e3920>)

tests/defects/test_enumeration.py:663: AssertionError
=========================== short test summary info ============================
FAILED tests/defects/test_enumeration.py::test_a_criterion_owed_no_test_is_never_offered_to_the_enumerator
1 failed, 27 deselected in 0.55s
```

The control assertion on the line before it (the tested criterion's text is in
some enumeration request) passed, so the failure is the scope exclusion being
sent to the enumerator, which is the defect. After the fix the whole file passes:
`28 passed in 2.28s`.

Full suite after the fix: `24 failed, 1851 passed, 2 xfailed`. The 24 are all in
`tests/benchmark/test_corpus.py` (14) and `tests/benchmark/test_rating_regression.py`
(10), and I verified the same 24 fail on the commit before the fix, with
`UnresolvableRevisionError`: this cloud clone is shallow, and the benchmark
corpus pins commits it does not contain. `ruff check` and `ruff format --check`
both pass on ruff 0.16.2.

## Check

Run by main's checker (`/tmp/main-checker`, at 80511ee) over 80511ee..3abef86.
Verdict: **INCOMPLETE**, on one obligation. My reading of each finding below
the strongly-supported bar, for the human to correct:

- `no-defect-set` ("The change produces no defect set"): code evidence **not
  addressed**. I believe this is the decomposition defect under Deferred: the
  obligation lost its subject, so it demands that the change produce no defect
  set at all. A correctly worded obligation ("a criterion owed no test produces
  no defect set") is what the regression test's last assertion checks.
- `no-enumeration-call-for-no-test-evidence`: test evidence **no plausible
  defect**. It is a restatement of `no-test-evidence-criteria-not-enumerated`,
  which was rated strongly supported by the same test; the duplicate was not
  merged at decomposition.
- `no-test-criteria-absent-from-enumeration-requests` and
  `criterion-owed-tests-appears` (the regression-test deliverables): test
  evidence **indeterminate**, "no way this change could fail the criterion was
  enumerated for it". The named test exists and does both things; I believe
  the enumerator has no way to describe a defect in a test-only deliverable.
  Not investigated further.
- Unrequested change 1 (`in_service`) says `no_tests` "is introduced but never
  used". That is wrong: `no_tests` existed before this change and is read at
  `pipeline.py:605` (`_in_original_order(obligations, needs_tests + no_tests)`).
  The diff moved the two lines; the reviewer appears to have read the move as an
  addition plus a deletion without connecting them.
- Unrequested change 2 (`separable`) is the test's extra assertion that defect
  sets exist only for `daily-rate`. That assertion checks the "produces no
  defect set" half of the requirement, so I believe it is in service of the
  mandate, not separable.

## Deferred

### [2026-10-19] Stale comment above the enumeration call says nothing reads `defect_sets`
- **Kind:** defect
- **Found during:** #327, headless run
- **Where:** src/acceptance/pipeline.py, the comment beginning "Advisory in this milestone"
- **Severity:** nice-to-have
- **What's wrong:** The comment says nothing below reads `defect_sets` and no
  rating depends on it. Since #316 (the cutover that derives the test-evidence
  class from pair verdicts) that is false: `derive_support`, `judge_pairs`, the
  execution tier and `recommend_tests` all read it.
- **Why I didn't act:** outside #327's scope, which is what the call is given.
- **Drafted fix:** delete the "Advisory in this milestone" paragraph; the
  paragraph above it, on why enumeration precedes discovery, stands.
- **Status:** open

### [2026-10-19] The benchmark corpus tests fail in a shallow clone
- **Kind:** defect
- **Found during:** #327, headless run
- **Where:** tests/benchmark/test_corpus.py, tests/benchmark/test_rating_regression.py
- **Severity:** should-fix
- **What's wrong:** In a cloud session's clone (`git rev-parse
  --is-shallow-repository` prints `true`), 24 tests fail with
  `UnresolvableRevisionError`, for example case `163-gate2-run1` naming
  `4d13ba1`. Every headless run therefore reports a red suite that has nothing
  to do with its fix, which trains the reader to ignore red.
- **Why I didn't act:** not this bug; the fix belongs in the session setup or
  the headless skill, not in `src/`.
- **Drafted fix:** add `git fetch --unshallow` (or a fetch deep enough to cover
  the corpus's pinned commits) to the `/fixbug-cloud` setup steps.
- **Status:** open

### [2026-10-19] Decomposition drops the subject of a clause
- **Kind:** filing (child of #181, the decomposition umbrella)
- **Found during:** #327, headless run, `decompose.log`
- **Where:** obligation `no-defect-set`
- **Severity:** should-fix
- **What's wrong:** The task sentence "A criterion whose required evidence
  demands no test is never offered to the enumerator, so it costs no
  enumeration call and produces no defect set" yielded the obligation "The
  change produces no defect set". The subject ("a criterion owed no test") was
  replaced by "the change", which inverts the scope: as written the fix would
  fail it by producing any defect set at all.
- **Why I didn't act:** headless run; filing needs human review.
- **Drafted fix:** file under #181 with the task file and log in
  `dogfood-logs/327-headless/` as the reproduction.
- **Status:** open
