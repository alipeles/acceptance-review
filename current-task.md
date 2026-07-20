## Deliverable
typed schemas for Project, Task source, Mandate interpretation, Builder declaration, Change set, Obligation, Test evidence, Execution evidence, Finding, Review (Benchmark case added in M-B0).

## Acceptance
each schema round-trips to/from persisted form; a Finding cannot be constructed without an evidence tier and at least one link target (invariant enforced by a failing constructor test).
