> **Task `M-B1` — Milestone M-B1**  ·  Track: benchmark
> Auto-generated from `Stage-1-Development-Plan.md` § 6. Edit freely.

## Inputs
§11.2 base layer; §10 dataset selection.

## Deliverable
an ingester mapping **SWE-bench Verified** instances (`problem_statement` → obligations input; `patch` → gold implementation; `test_patch` + `FAIL_TO_PASS`/`PASS_TO_PASS` → test-evidence ground truth) into benchmark cases; start with a stratified subset of ~100 across the `difficulty` field, scalable to the full 500.

## Acceptance
≥ 100 Verified cases ingested and scored end-to-end; the FAIL_TO_PASS/PASS_TO_PASS split is preserved as gap-vs-regression labels; per-repo licenses recorded per instance `[human: confirm redistribution posture]`.

---
*Dogfooding note:* when you pick up this issue, copy the Deliverable/Acceptance into a `current-task.md` — that file becomes a real input the checker will one day ingest.
