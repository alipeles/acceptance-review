# Instability harness: build its client from the run configuration, and report perturbation sensitivity per axis

## Task

The judgement-instability harness in `src/acceptance/benchmark/instability.py`
runs a review several times, and once over a perturbed input, and reports how
far its judgements move.

When the harness builds its own model client (no client factory supplied), that
client must be configured exactly as `RunConfig.build_client()` would configure
it for the same run configuration, including the embedding model, per-stage
models and per-stage reasoning settings. The client the harness uses to watch a
run must accept every argument `ModelClient.complete` accepts and pass each one
through unchanged, so that a parameter added to `ModelClient` later reaches the
pipeline without any edit to the harness.

The perturbation result must state a sensitivity for each judgement axis
separately: obligation and open-question presence, evidence class, and defect
verdict. Each axis's sensitivity is the number of judgements on that axis that
moved, divided by the number of judgements on that axis that were watched, so
every reported sensitivity lies between 0 and 1. For the defect-verdict axis,
the watched judgements are the (defect, test) verdicts present in both the
baseline and the perturbed run. An axis with nothing watched reports no
sensitivity, not zero. No single sensitivity blended across axes is reported.

A regression test is part of the deliverable: one that runs the harness through
its default client construction over a small recorded case and fails if the
pipeline's client gains a parameter the harness does not pass on.

## Scope exclusions

- No change to any prompt or response schema.
- No change to how the pipeline itself builds or calls its client.
