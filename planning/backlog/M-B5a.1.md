> **Task `M-B5a.1` — Milestone M-B5a**  ·  Track: benchmark
> Auto-generated from `Stage-1-Development-Plan.md` § 6. Edit freely.

## Inputs
§13.5 #1–9.

## Deliverable
nine minimal Git fixture repos, each a real task file + base/head diff + tests reproducing the archetype (missed obligation, qualifier missed, superficial test, non-discriminating input, circular expected result, mocked-out behavior, declaration mismatch, unrequested change, revision cycle).

## Acceptance
each fixture builds; `git diff base head` is non-empty; pytest runs (pass/fail as the archetype intends).

---
*Dogfooding note:* when you pick up this issue, copy the Deliverable/Acceptance into a `current-task.md` — that file becomes a real input the checker will one day ingest.
