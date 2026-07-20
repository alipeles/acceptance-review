> **Task `M-B0.1` — Milestone M-B0**  ·  Track: benchmark
> Auto-generated from `Stage-1-Development-Plan.md` § 6. Edit freely.

## Inputs
§15 Benchmark case, §11.1 metrics.

## Deliverable
a case type carrying source (dataset/PR/mutant/agent/archetype), inputs, ground-truth labels (gaps, decomposition, mappings, evidence classes), and slots for reviewer output + score.

## Acceptance
a case serializes/deserializes; a case missing ground-truth labels fails validation.

---
*Dogfooding note:* when you pick up this issue, copy the Deliverable/Acceptance into a `current-task.md` — that file becomes a real input the checker will one day ingest.
