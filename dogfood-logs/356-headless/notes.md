# Notes — #356 headless run

## Decompose

`decompose.log` (5.2 KB, exit 0), 7 requirements, 18 obligations, no open
questions raised. The run's stderr (usage table, run id) is in
`decompose.stderr`.

Obligations I believe are invented or wrongly derived:

- `one-line-message` (task-03): its text reads "The requirement text fits on one
  line." That is wrong — the requirement is that the *error message* fits on one
  line, not the requirement text. It also duplicates
  `single-line-acceptance-model-error`, which states it correctly.
- `completion-call` (task-04): "A completion call is included in the
  deliverable." A fragment cut from the regression-test sentence; it loses the
  "fails transiently once and then succeeds, records what a first-time success
  records" part that the embedding half kept as two obligations. The completion
  half of the regression test is under-specified as a result.
- `first-attempt-success-equivalence`, `same-transcript-after-transient-failure-and-success`
  and `retry-leaves-no-trace-in-recorded-transcript` (task-02) are one
  behaviour said three ways. The linker said so too: its "Unreconciled linking
  answers" line reports these three as transitively linked with one pair denied,
  so none were merged. Duplicate set left unmerged.
- `transient-failure-definition` is a definition, not a behaviour; acceptable as
  a qualifier on `retry-transient-failures-for-live-provider-calls` but it is
  derived as a standalone invariant.

Missing: nothing I can see. The regression-test deliverable for the completion
call is weakly represented (see `completion-call` above), but present.

Open questions: none raised.

## Reproduction

Regression tests in `tests/test_llm_retry.py`, run against the unfixed code
(branch point 943c176). Every test that exercises a provider failure fails
because the provider's own exception escapes `ModelClient` on the first
attempt: no retry, and no `LLMError`. The CLI test fails because that raw
exception propagates out of `cli.main` (a traceback, not a one-line
`acceptance: model error:`). The one passing test is the control: a non-provider
failure (a `KeyError`) is neither retried nor wrapped, which was already true.

Distinct exception lines in the failure output, for the record:
`ProviderError: Bad Gateway` x4, `Service Unavailable`, `rate limited`,
`timed out`, `bad key`, `ConnectionError: connection reset by peer`,
`TimeoutError: read timed out` — each raised straight from the fake provider.

```
/home/user/acceptance-review/tests/test_llm_retry.py:57: ProviderError
=========================== short test summary info ============================
FAILED tests/test_llm_retry.py::test_a_completion_that_fails_transiently_once_records_a_first_time_success[502]
FAILED tests/test_llm_retry.py::test_a_completion_that_fails_transiently_once_records_a_first_time_success[503]
FAILED tests/test_llm_retry.py::test_a_completion_that_fails_transiently_once_records_a_first_time_success[429]
FAILED tests/test_llm_retry.py::test_a_completion_that_fails_transiently_once_records_a_first_time_success[408]
FAILED tests/test_llm_retry.py::test_a_completion_that_fails_transiently_once_records_a_first_time_success[connection]
FAILED tests/test_llm_retry.py::test_a_completion_that_fails_transiently_once_records_a_first_time_success[timeout]
FAILED tests/test_llm_retry.py::test_an_embedding_that_fails_transiently_once_records_a_first_time_success
FAILED tests/test_llm_retry.py::test_a_retried_call_replays_without_a_provider
FAILED tests/test_llm_retry.py::test_retries_are_bounded_and_back_off - test_...
FAILED tests/test_llm_retry.py::test_a_call_that_keeps_failing_names_stage_model_and_status_on_one_line
FAILED tests/test_llm_retry.py::test_an_embedding_that_keeps_failing_names_its_stage
FAILED tests/test_llm_retry.py::test_a_non_transient_provider_error_is_not_retried_but_is_an_llm_error
FAILED tests/test_llm_retry.py::test_the_cli_reports_a_call_that_keeps_failing_as_one_line
13 failed, 1 passed in 0.78s
```

## Suite and linters

- `ruff check .`: All checks passed (ruff 0.16.2). `ruff format --check .`: 261 files already formatted.
- `tests/test_llm_retry.py`: 14 passed after the fix.
- Full `pytest -q` on this branch at 13ff97a: 1872 passed, 2 failed, 2 xfailed.
  The same full run on origin/main at 943c176: 1856 passed, the **same 2** failed.
  Both are `tests/benchmark/test_corpus.py` cases for `163-gate2-run1`, failing
  because this clone lacked tag `corpus/163-gate2-run1` (see Deferred). After
  fetching the corpus tags, `test_corpus.py` + `test_llm.py` + `test_llm_retry.py`:
  70 passed, and `test_rating_regression.py`: 35 passed. I did not re-run the
  whole suite a third time after the fetch.

## Check

`check.log` (184 KB, exit 0), run with main's checker at 943c176 over
origin/main..13ff97a. Stderr (usage table, run id) is in `check.stderr`.
Verdict: **Task completion: INCOMPLETE**. Not acted on, per the run's rules.

Every obligation is `addressed` in code. Test evidence below
"strongly supported":

- `retry-transient-failures-for-live-provider-calls`, `same-transcript-after-transient-failure-and-success`,
  `embedding-call-transient-failure-then-success`: partially supported. All
  three recommendations ask for the same thing: a transient failure raised as
  an exception that has no `status_code` and is not a builtin
  `ConnectionError`/`TimeoutError`. My reading: this is a real gap in the
  *code*, not only the tests — `_is_transient` falls back to builtin types only,
  so e.g. an `httpx.ReadTimeout` reaching the provider function unwrapped would
  not be retried. Whether that path exists in practice depends on whether
  LiteLLM always wraps such errors in its status-carrying classes (I believe
  it does for completion and embedding, but did not verify for Voyage).
- `transient-failure-definition`: unsupported, no mapped test. Same
  recommendation as above. The parametrised test over 502/503/429/408/
  connection/timeout was not mapped to it; I believe that is a mapping miss,
  since that test exercises exactly the definition.
- `successful-response-only-persistence`: unsupported, no mapped test.
  Recommendation: transient failure, then a response that fails validation;
  assert nothing is persisted. `test_retries_are_bounded_and_back_off` asserts
  an empty store after exhausted retries, but nothing combines a retry with a
  failing validation. Fair recommendation.

No plausible defect enumerated (so no test evidence obtainable) for
`llmerror-message-stage-provider-status`, `completion-call` and
`request-key-ignores-retry-policy`. The first is odd: the message test
asserts stage, model and status, so a defect that drops one of them is
plausible and would be killed.

`one-line-message` (the decomposer's "the requirement text fits on one line")
was judged "not required — a formatting constraint on the requirement text"
and "addressed" in code. The invented obligation from decomposition flowed
through to the verdict as if real.

Unrequested changes: none.

## Deferred

### [2026-10-19] Corpus tags are not fetched by a fresh clone, so 9 rating-regression tests fail
- **Kind:** defect
- **Found during:** #356, headless run
- **Where:** tests/benchmark/test_rating_regression.py; tests/fixtures/rating-regression/163-gate2-run1/case.json
- **Severity:** should-fix
- **What's wrong:** The case pins head `41cd0da`, reachable only through tag
  `corpus/163-gate2-run1`. This cloud clone was shallow and did not have that tag
  even after `git fetch --unshallow` (which fetched the `corpus/167-*` tags but
  not 163). 9 tests failed with `UnresolvableRevisionError` until I ran
  `git fetch origin 'refs/tags/corpus/*:refs/tags/corpus/*'`; then all 35 pass.
- **Why I didn't act:** environment/setup, outside #356.
- **Drafted fix:** have the cloud setup (or `scripts/`) fetch `refs/tags/corpus/*`
  explicitly, or make the error message name the tag to fetch.
- **Status:** open

### [2026-10-19] Decomposer turns "the error message fits on one line" into "the requirement text fits on one line"
- **Kind:** filing (child of #181, the decomposition umbrella)
- **Found during:** #356, headless run, decompose
- **Where:** decompose.log, obligation `one-line-message` from task-03
- **Severity:** should-fix
- **What's wrong:** The obligation's subject was swapped from the error message
  to the requirement text. `check` then rated it "not required" and
  "addressed", so an invented obligation passed silently.
- **Why I didn't act:** decomposition prompt work, on the no-go list.
- **Drafted fix:** file under #181 with `decompose.log` and `check.log` as
  evidence.
- **Status:** open

### [2026-10-19] Transient check misses status-less exceptions that are not builtin ConnectionError/TimeoutError
- **Kind:** decision
- **Found during:** #356, headless run, check
- **Where:** src/acceptance/llm.py `_is_transient`
- **Severity:** nice-to-have
- **What's wrong:** see the Check section. Only matters if LiteLLM lets a raw
  `httpx`/`requests` exception through.
- **Why I didn't act:** the run's rule is not to act on check output.
- **Drafted fix:** also treat `httpx.TransportError`-family and
  `requests.ConnectionError`-family exceptions as transient, by class name or
  by walking `__cause__`, without importing them in replay. Recommendation:
  wait for evidence that such an exception reaches us.
- **Status:** open

### [2026-10-19] Skill's `git worktree add --no-track <dir> origin/main` fails
- **Kind:** defect
- **Found during:** #356, headless run, step 8
- **Where:** fixbug-cloud skill, step 8
- **Severity:** nice-to-have
- **What's wrong:** `--no-track` is only valid with `-b`; git refuses with
  "--[no-]track can only be used if a new branch is created". I used
  `git worktree add --detach /tmp/main-checker2 origin/main` instead.
- **Why I didn't act:** `.claude/` is on the no-go list.
- **Drafted fix:** replace the line with `git worktree add --detach /tmp/main-checker origin/main`.
- **Status:** open
