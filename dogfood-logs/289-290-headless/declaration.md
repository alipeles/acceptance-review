# Declaration — #289 and #290

## What I implemented

- `RunConfig.build_client` takes an optional `client_class` (default
  `ModelClient`), so a subclass can be built with exactly the parameter set
  `build_client` uses.
- `instability.run_once`, when no client factory is supplied, builds its client
  with `config.build_client(client_class=ObservingClient)` and no longer lists
  the fields itself. That brings in `embedding_model`, `stage_models` and
  `stage_reasoning`, which the copied construction dropped.
- `ObservingClient.complete` takes `*args, **kwargs` and passes them to
  `ModelClient.complete` unchanged, so `stage_controls` and `label` (and any
  later parameter) reach the real client.
- `PerturbationResult` no longer carries one `watched_judgements` /
  `changed_judgements` pair. It carries `axes`, a list of `AxisSensitivity`
  rows, one per `SensitivityAxis` (presence, evidence class, defect verdict).
  `PerturbationResult.sensitivity(axis)` returns that axis's figure, or `None`
  when the axis watched nothing.
- Per-axis populations:
  - presence: the baseline's distinct obligation and open-question texts, plus
    the statements only the perturbed run has (so gained statements are inside
    the population they moved in); changed = distinct subjects of content
    presence differences;
  - evidence class: obligation ids with an evidence class in both runs;
    changed = evidence-class content differences;
  - defect verdict: (defect, test) keys present in both runs; changed = verdict
    content differences.
- Updated the `ObservingClient` docstring, which still cited #149 (verdicts not
  persisted), no longer true since #316.

## What I tested

New tests in `tests/benchmark/test_instability.py`:

- `test_the_default_client_is_configured_as_run_config_builds_it` — compares
  every attribute of the harness's default-built client against
  `RunConfig.build_client()` for the same config.
- `test_the_observing_client_forwards_every_parameter_complete_accepts` — reads
  `ModelClient.complete`'s signature and checks each named parameter arrives.
- `test_the_default_construction_runs_the_pipeline_end_to_end` — no client
  factory, a two-obligation recorded case on archetype 01, provider patched at
  `llm._default_completion_fn` / `_default_embedding_fn`; obligation linking
  runs (embeds and issues `_Verdicts`).
- `test_perturbation_sensitivity_is_per_axis_and_never_exceeds_one` — one
  obligation, four flipped verdicts: the old blended figure was 4.0.
- `test_verdicts_in_only_one_run_are_not_watched`,
  `test_an_axis_with_nothing_watched_reports_no_sensitivity`,
  `test_obligations_gained_under_perturbation_cannot_push_presence_above_one`.

All seven failed before the fix (output in `notes.md`) and pass after. Three
existing tests that pinned the blended single-figure API were moved to the
per-axis API; #290 names the blended figure as the defect.

## What I left out

- `measure_instability`'s default `comparison_client` is a third copy of the
  client construction (no embedding model). The issue names two sites; I left
  the third and noted it under Deferred.
- The committed baseline in `docs/experiments/191-discrimination-partition/`
  uses the old field names. It is a historical record; I did not rewrite it.

## Assumptions

- Obligation presence and open-question presence share one axis, as the issue
  and the task file group them.
- A presence denominator that includes gained statements is the right reading of
  "every reported sensitivity lies between 0 and 1"; the issue's suggestion
  ("as today") would let gained statements push presence above 1.

## Unverified

- I did not run the harness against a live model. The end-to-end test uses a
  patched provider.
- The full suite needed `git fetch --unshallow` and the `corpus/*` tags first;
  on the shallow cloud clone, 24 rating-regression tests fail for missing
  history, unrelated to this change.
