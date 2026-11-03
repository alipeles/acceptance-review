# 437 decompose run 1 — judgement

Data for #440 (evaluating the decomposition redesign on real mandates), per the
M11 block in `CLAUDE.md`. Not a gate.

**Input:** `mandate.md`, the body of #437 exactly as filed on GitHub (without the
owner's later comment). Run on branch `437-synthesis` (claims and synthesis,
uncommitted), 2026-11-02, live, `anthropic/claude-sonnet-5-5`, $0.0450.

**Output:** 12 claims, 5 units set aside as background, 14 synthesized
obligations. The per-requirement path finds no requirement, because the body has
no `# Task` heading.

**Judgement:**

- Every Acceptance bullet and every paragraph sentence that asks for something
  is cited. Nothing missing that I can see.
- Restatements not merged: `obligation-cites-claims` and
  `validation-rejects-uncited` overlap (both cite claim-10), and
  `downstream-consume-synthesized` and `remove-per-line-path` share claim-14.
  Each pair says slightly different things, so this is borderline rather than
  wrong.
- Mistyped: `regression-fixtures` is a test that is itself the deliverable and
  should be `test_deliverable`, not `requested_behavior`. Pruning (#438) or a
  prompt change should catch this; noted for #440.
- `obligation-type-field` repeats the issue's wording "in the existing type
  field", which DR-437 found to be wrong (the field held a different list). The
  tool faithfully reports what the mandate says; the mandate was wrong.
- `re-record-once` is about the work process, not the delivered software. It is
  the kind of item pruning should drop.
