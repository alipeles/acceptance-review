# Task
Make a review's own provenance tell the truth about the determinism controls
that were in force. The harness records which controls a provider actually
honoured, but a review still reports the controls that were *configured*, so on
a provider that discards them the review claims a reproducibility it does not
have. Source provenance from the client that made the calls rather than from
configuration, distinguish a control that held from one the provider ignored and
from one nothing was ever observed about, and stop the store from keeping a
transcript whose response failed validation.

## Constraints
- Building provenance must not pull in the provider stack, because provenance is
  assembled during replay runs that have no provider dependency and no API key.
- A control the provider discarded must never be reported as the value that was
  requested.

## Scope exclusions
- Rendering provenance in the human-readable report is presentation work owned
  by M7.6; this change corrects the persisted review state and the benchmark's
  determinism disclosure that reads it.
- Sampling a provider repeatedly to quantify variance where controls were
  discarded belongs to the benchmark harness (M-B0.4).

## Completion expectations
- Implementation
- A review's provenance reports the determinism controls the provider actually
  honoured, separately from the controls that were requested.
- A control the provider discarded is reported as not in force rather than as
  the requested value, so a run against a provider that rejects a seed does not
  claim that seed.
- A review whose run made no model call at all reports its determinism as
  indeterminate rather than claiming the configured controls held.
- Provenance is built from the client that issued the calls, so one builder
  serves both the CLI pipeline and the benchmark hooks instead of two that can
  disagree.
- A replayed run reports the controls recorded in the transcripts it replayed,
  so replaying a recording made against a provider that discarded a control does
  not report that control as in force.
- A transcript recorded from a response that fails schema validation is not left
  in the store, so a recording session cannot poison the corpus with a response
  the harness itself rejected.
- The default model named by the test doubles is the model the tool actually
  defaults to, so test support does not assert a default that is not real.
- A run started from the command line carries the configured default seed, so
  the fixed-seed half of the determinism strategy is in force on the path users
  actually invoke, with an explicit way to opt out of seeding.
