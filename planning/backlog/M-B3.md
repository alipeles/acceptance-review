> **Task `M-B3` — Milestone M-B1**  ·  Track: benchmark
> Auto-generated from `Stage-1-Development-Plan.md` § 6. Edit freely.

## Inputs
§11.2, §8.2 concept; §10.

## Deliverable
inject a mutant into real code with a real passing test; surviving mutant → ground-truth "weak evidence" label. Built on **BugsInPy**, whose per-bug reproducible checkout + `test`/`coverage`/`mutation` commands give real code, a real relevant test, and a ready mutation harness; SWE-bench `PASS_TO_PASS` tests are a secondary source. Uses mutation offline for *labeling*, independent of the product's execution tier.

## Acceptance
generated weak-evidence labels reproduce on re-run; a killed mutant is not mislabeled as weak.

---
*Dogfooding note:* when you pick up this issue, copy the Deliverable/Acceptance into a `current-task.md` — that file becomes a real input the checker will one day ingest.
