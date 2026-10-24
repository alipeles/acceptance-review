# Notes — #289 and #290, one headless run

Both issues touch only `src/acceptance/benchmark/instability.py`, so they are
fixed together on one branch with one task file.

State of main when this run started: #289's third instance (the
`ObligationDiscrimination` filter that could never match) is already gone —
#316, which retired the discrimination stage, made `snapshot_review` read pair
verdicts off the `Review`. The first two instances (the `run_once` client built
field by field, and the positional `ObservingClient.complete`) were still
present, as was #290's blended sensitivity.

## Decompose

Run `28c4e53176371af0`, 6 requirements, 16 obligations, no open questions, no
crash.

Invented, I believe:

- `runs-review-several-times`, `perturbed-input-run`,
  `judgement-movement-reporting` come from the Task section's first paragraph,
  which only describes what the harness already is. It was meant as context.
  This is the background-becomes-an-obligation pattern (#212, where background
  text turns into obligations). Arguably my wording's fault: the paragraph is
  phrased as a present-tense statement of behaviour.
- `regression-test-part-of-deliverable` is a restatement of the two test
  obligations beside it, not a separate requirement.

Duplicates, I believe: `watch-client-complete-signature` and
`pass-complete-args-through-unchanged` overlap (the second contains the first).

Missing: none that I can see.

Open questions: none raised.

## Reproduction

The seven new tests in `tests/benchmark/test_instability.py`, run against the
unfixed code (only the `SensitivityAxis` enum added so the file imports):

```
E       AssertionError: assert {'model': 'm'...record'>, ...} == {'model': 'm'...record'>, ...}
E       TypeError: ObservingClient.complete() got an unexpected keyword argument 'stage_controls'
E           acceptance.llm.LLMError: this client has no embedding model configured, so it cannot embed; pass embedding_model to ModelClient (RunConfig.embedding_model supplies it for a normal run)
E                   AttributeError: 'PerturbationResult' object has no attribute 'axes'
E                   AttributeError: 'PerturbationResult' object has no attribute 'axes'
E       TypeError: PerturbationResult.sensitivity() takes 1 positional argument but 2 were given
E                   AttributeError: 'PerturbationResult' object has no attribute 'axes'
FAILED tests/benchmark/test_instability.py::test_the_default_client_is_configured_as_run_config_builds_it
FAILED tests/benchmark/test_instability.py::test_the_observing_client_forwards_every_parameter_complete_accepts
FAILED tests/benchmark/test_instability.py::test_the_default_construction_runs_the_pipeline_end_to_end
FAILED tests/benchmark/test_instability.py::test_perturbation_sensitivity_is_per_axis_and_never_exceeds_one
FAILED tests/benchmark/test_instability.py::test_verdicts_in_only_one_run_are_not_watched
FAILED tests/benchmark/test_instability.py::test_an_axis_with_nothing_watched_reports_no_sensitivity
FAILED tests/benchmark/test_instability.py::test_obligations_gained_under_perturbation_cannot_push_presence_above_one
7 failed, 42 deselected in 0.96s
```

The first three are #289's two symptoms exactly as the issue records them (the
`LLMError` at linking and the `stage_controls` `TypeError`). The last four fail
on the missing per-axis API, so to show #290's actual defect I also ran the
old `_perturbation_result` over the same pair the first per-axis test uses (one
obligation, four flipped defect verdicts):

```
watched 1 changed 4
blended sensitivity 4.0
```

After the fix: `tests/benchmark/test_instability.py` 49 passed; full suite
1883 passed, 2 xfailed; `ruff check .` clean; `ruff format --check .` clean.

## Check

Run `2f00d3a9e708c75c`, main's checker over `origin/main..HEAD`. Verdict
**INCOMPLETE**. Not acted on; recorded for the human.

- `watch-client-complete-signature` — unsupported, no mapped test. I believe
  `test_the_observing_client_forwards_every_parameter_complete_accepts`
  demonstrates it (it calls the client with every parameter of
  `ModelClient.complete` and fails with `TypeError` on the old code). It was
  mapped to the sibling obligation `pass-complete-args-through-unchanged` only.
  Possibly a mapping defect (#182, test discovery and mapping) over duplicate
  obligations.
- `regression-test-part-of-deliverable`,
  `default-client-construction-small-recorded-case`,
  `client-parameter-forwarding-regression-test` — indeterminate, "no way this
  change could fail the criterion was enumerated". All three are test-demand
  obligations whose deliverable is the test itself.
- Five unrequested changes, all `in_service` (the `client_class` parameter, the
  `PerturbationResult` reshaping, the presence counting rule, the
  `*args/**kwargs` signature, the docstring).

## Deferred

### [2026-10-19] measure_instability's default comparison client is a third copy of the client construction
- **Kind:** defect
- **Found during:** #289, headless run
- **Where:** src/acceptance/benchmark/instability.py, `measure_instability`
  (`comparison_client = comparison_client or ModelClient(model=..., mode=..., store=...)`)
- **Severity:** should-fix
- **What's wrong:** it builds a `ModelClient` from three fields and drops
  `embedding_model`, `temperature`, `seed`, `stage_models` and
  `stage_reasoning`. The same shape #289 reports at `run_once`. Today the
  comparison calls (`align_obligations`, `classify_unmatched`) do not embed, so
  nothing crashes yet.
- **Why I didn't act:** #289 names two sites; switching this one to
  `RunConfig(...).build_client()` would change the comparison calls' seed and
  temperature, and so their request keys, which is a decision about the
  instrument, not a bug fix.
- **Drafted fix:** `RunConfig(model=models[0], mode=Mode.RECORD).build_client()`,
  after confirming the `RunConfig` default seed and temperature are what the
  comparison should run at. File as a child of #186 (the benchmark umbrella).
- **Status:** open

### [2026-10-19] Full suite fails on a shallow clone with no corpus tags
- **Kind:** defect
- **Found during:** #289, headless run
- **Where:** tests/benchmark/test_rating_regression.py; the cloud session's clone
- **Severity:** nice-to-have
- **What's wrong:** the cloud clone is shallow and lacks `refs/tags/corpus/*`,
  so 24 rating-regression tests fail with `UnresolvableRevisionError` until
  `git fetch --unshallow origin` and
  `git fetch origin 'refs/tags/corpus/*:refs/tags/corpus/*'` are run. By
  design per the error text, but it costs every headless run a confusing red
  suite.
- **Why I didn't act:** environment setup, outside both issues.
- **Drafted fix:** add both fetches to the `/fixbug-cloud` setup steps (or the
  cloud session's setup script).
- **Status:** open

### [2026-10-19] The committed #191 baseline uses the retired blended sensitivity fields
- **Kind:** decision
- **Found during:** #290, headless run
- **Where:** docs/experiments/191-discrimination-partition/baseline-instability.json
- **Severity:** should-fix
- **What's wrong:** it records `watched_judgements: 21, changed_judgements: 1`
  as one blended figure. #290 already says it cannot be compared with a later
  measurement; after this fix the report shape differs too.
- **Why I didn't act:** it is a historical measurement, and whether #191 needs
  a re-taken baseline is #191's call.
- **Drafted fix:** none; re-take the baseline when #191 resumes.
- **Status:** open
