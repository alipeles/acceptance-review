# Task
Pre-M4 cleanup pass: reconcile the M3.5/M7.6 backlog mirror with the real GitHub issues, and remove duplicated code the M3.1–M3.3 capabilities accumulated before it repeats again in M3.5/M4/M5.

## Constraints
- Reconcile `planning/backlog/` (issues.tsv, milestones.tsv, per-task markdown files) and the plan doc's M3.5 section with the actual GitHub issue numbering (M3.5.5 renumbered from "Advisory presentation" to the docs task; the advisory-presentation task moved to M7.6).
- Extract the duplicated schema-constrained-model-call test double (`_client_returning`/`_client_dispatching`) out of five test files into a shared helper.
- Extract the duplicated `ReviewProvenance`-from-`ModelClient` and "copy case, attach review, attach score" pattern out of the two existing benchmark scoring hooks (M1.4, M3.3) before a third one repeats it.
- Behavior must not change: all existing tests keep passing unmodified in intent, just de-duplicated.

## Completion expectations
- Implementation
- Unit tests (existing suite stays green; no new behavior to test)
