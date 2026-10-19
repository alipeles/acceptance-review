# Notes — #355, where a span the two summary steps disagree on aborted the whole decomposition

## Decompose

`decompose.log` is the required run, on the unfixed code. It crashed with the
very defect this issue is about:

> span 1 of requirement 'task-01' was found uncovered by the obligations
> already derived, but the call asked about it alone produced neither an
> obligation nor an open question: 'the follow-up call asked about that span
> alone returns neither an obligation nor an open question'

The span it stopped on is the condition clause of the task's first sentence.
It describes when the behaviour applies, not a property of its own, so I
believe the follow-up call was right and the coverage step was wrong.

Because that left no breakdown to judge, I also ran `decompose` with this
branch's fixed code over the same task file, saved as
`decompose-with-fix.log` (run `825b5b20c70641d2`). That is extra; it is not the
checker reviewing its own fix, only the decomposer. Judgement of that
breakdown:

Obligations I believe are wrong or redundant:

- `two-steps-disagreed` and `quote-the-span` are pieces of
  `record-open-question-for-step-disagreement` split out again. Duplicates.
- `quote-the-span` says "The requirement quotes the span"; the mandate says
  the open question quotes it. Misworded. Its type `docs_config` is also wrong.
- `record-open-question-for-step-disagreement` typed `human_review`; I believe
  it is functional.

Missing: none that I can see.

Open questions:

- `oq-01` ("should it complete … or should it stop?"): **wrong question**. The
  task file says in its first sentence that the decomposition completes.
- `task-01-span-01-disagreement`: the question this fix produces, on the
  condition clause above. **Implementation detail / fair**: it is the tool
  doing what the fix says, and the answer is "no, the clause has no property
  of its own". No task-file change.

## Reproduction

New test `test_an_uncovered_span_that_yields_nothing_becomes_an_open_question`
in `tests/requirement/test_summary_pass.py`, run before the fix:

```
>                   raise SchemaValidationError(
                        f"span {decision.index} of requirement '{summary.id}' was found "
                        f"uncovered by the obligations already derived, but the call asked "
                        f"about it alone produced neither an obligation nor an open "
                        f"question: {normalise(decision.text)!r}"
                    )
E                   acceptance.llm.SchemaValidationError: span 1 of requirement 'task-01' was found uncovered by the obligations already derived, but the call asked about it alone produced neither an obligation nor an open question: 'The export runs nightly.'

src/acceptance/requirement/obligations.py:1161: SchemaValidationError
=========================== short test summary info ============================
FAILED tests/requirement/test_summary_pass.py::test_an_uncovered_span_that_yields_nothing_becomes_an_open_question
1 failed, 12 deselected in 0.38s
```

After the fix, `tests/requirement/test_summary_pass.py`: 13 passed.

The test replaced `test_an_uncovered_span_that_yields_nothing_stops_the_run`,
which asserted the abort. The issue says that abort is the bug, so this is the
one case where editing an existing test is allowed.

## Suite and linters

- `ruff check .`: all checks passed (ruff 0.16.2).
- `ruff format --check .`: 260 files already formatted.
- `pytest -q`: first run 24 failed, 1834 passed, 2 xfailed. All 24 were in
  `tests/benchmark/test_corpus.py` and `tests/benchmark/test_rating_regression.py`
  and came from the cloud clone being shallow. After
  `git fetch --unshallow` and fetching all branches and tags, 11 still fail,
  all because the tag `corpus/163-gate2-run1` is not on origin. I verified the
  same 11 fail on an untouched checkout of `origin/main` (991e780), so they are
  not caused by this change.

## Check

`check.log` is the main-branch checker run over this branch. It crashed with
the same error as `decompose.log`, because main's checker still has the
defect. It holds no review. Nothing to act on.

## Deferred

### [2026-10-19] The summary's coverage reason says "yielded" for a span that ended as an open question
- **Kind:** defect
- **Found during:** #355, headless run
- **Where:** src/acceptance/requirement/obligations.py, `coverage_reason(decisions)` in the summary loop
- **Severity:** nice-to-have
- **What's wrong:** the reason on the summary's disposition is built from the coverage step's verdicts alone, so an uncovered span reads "… not already required, so it yielded" even when its own call produced only an open question (seen in the new test: disposition `open_question`, reason ending "so it yielded"). It was already so for a span whose call raised a question itself.
- **Why I didn't act:** out of scope for #355; the text lives in `requirement/summary.py`.
- **Drafted fix:** pass the per-span outcome (obligation ids, question ids) into `coverage_reason` and word the uncovered case as "… not already required; yielded X" or "… raised open question Y".
- **Status:** open

### [2026-10-19] Tag corpus/163-gate2-run1 is missing on origin, so 11 benchmark tests fail on every fresh clone
- **Kind:** defect
- **Found during:** #355, headless run
- **Where:** tests/benchmark/test_corpus.py, tests/benchmark/test_rating_regression.py; the tag on origin
- **Severity:** should-fix
- **What's wrong:** case `163-gate2-run1` names revision `41cd0da`, which no ref on origin reaches. `test_corpus.py` itself reports "corpus/163-gate2-run1 is missing; 163-gate2-run1 will not survive a clone". Fails on main too.
- **Why I didn't act:** pushing a tag is outward-facing and the commit is not in this clone.
- **Drafted fix:** from a machine that still has `41cd0da`, `git tag corpus/163-gate2-run1 41cd0da` and push the tag. Parent umbrella #186 (benchmark).
- **Status:** open

### [2026-10-19] A cloud clone is shallow, which breaks 13 more benchmark tests
- **Kind:** defect
- **Found during:** #355, headless run
- **Where:** the `/fixbug-cloud` setup steps
- **Severity:** nice-to-have
- **What's wrong:** the session's clone is shallow and has no corpus tags, so the suite reports 24 failures until history and tags are fetched.
- **Why I didn't act:** `.claude/` is on the no-go list.
- **Drafted fix:** add `git fetch --unshallow origin` and `git fetch origin '+refs/tags/*:refs/tags/*'` to the skill's Setup.
- **Status:** open

### [2026-10-19] The fixbug-cloud worktree command fails as written
- **Kind:** defect
- **Found during:** #355, headless run
- **Where:** `/fixbug-cloud` step 8
- **Severity:** nice-to-have
- **What's wrong:** `git worktree add --no-track /tmp/main-checker origin/main` fails with "--[no-]track can only be used if a new branch is created". I used `git worktree add --detach /tmp/main-checker2 origin/main` (a second path because removing the half-made first one was denied).
- **Why I didn't act:** `.claude/` is on the no-go list.
- **Drafted fix:** replace `--no-track` with `--detach` in step 8.
- **Status:** open
