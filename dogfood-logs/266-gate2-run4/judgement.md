# Judgement — #266 Gate 2, run 4

`check --task current-task.md --base 265bfac --head 521a42a`. First run after
the restructure: which evidence an obligation requires is decided once, at
decomposition.

## NOT CLEAN — 21 of 45 partially supported

Verdict `INCOMPLETE`. The composition is entirely different from run 3's, and
the difference is the finding.

| | run 3 | run 4 |
|---|---|---|
| obligations | 34 | 45 |
| unmapped (`no mapped test`) | 9 | **0** |
| unsupported | 2 | **0** |
| partially supported | 3 | **21** |
| strongly supported | 24 | 19 |
| test evidence not required | — | 5 |
| code evidence not required | — | 17 |

## What the restructure fixed

**Zero unmapped obligations.** Every obligation that requires test evidence has
mapped tests. The twin-split that took down runs 1–3 does not appear at all.

**The refusal mechanism is gone and nothing regressed.** No contradiction is
representable, because there is one field with one value.

**The new axis renders as designed**, with reasons that are specific rather than
boilerplate:

```
code evidence: not required — The requirement itself asks for a test
  assertion, so the test is the whole obligation.
test evidence: not required — This scope exclusion is satisfied by the absence
  of work in the change, which is directly checkable from the source.
```

Five scope exclusions took `code_only`; seventeen "a test asserts that ..."
requirements took `tests_only`. Both judgements are correct, and the second is a
case the old structural rule could not express at all.

## What it broke — the mapper now over-maps

Mapped tests per obligation: **min 2, max 21, mean 5.0**, with 14 obligations
carrying five or more. Reading them, many are only loosely related:

> **1. A test asserts that the kinds of evidence a criterion requires reach the
> persisted review state.**
> - `test_llm.py::test_record_mode_validates_and_persists_a_transcript`
> - `test_report.py::test_report_renders_each_obligation_with_both_axes_numbered`
> - `test_unevidenceable_obligations.py::test_it_survives_persistence`

Only the third is on point. This is the direct cost of the mapping-prompt fix —
*"return EVERY id its assertions are aimed at, not the single best one"* — which
solved the twin-split by trading precision for recall, and the trade went too
far. With five loosely-mapped tests under an obligation, the discrimination judge
finds defects they do not catch, and the rating lands on `partially supported`.

That accounts for the shape of the result: **21 partially, 0 unsupported, 0
unmapped**. Nothing is missing evidence; a lot of things have evidence that does
not discriminate, because much of it was never about them.

Attributed to the tool, and specifically to a change made on this branch. Queued
as a comment on #245, which is where the prompt fix belongs.

## The tautology experiment — the tool does not catch it

`constraint-03` was kept deliberately, on the human's instruction, to see how the
tool handles a requirement that is true by construction: *"A criterion cannot
record that test evidence is both required and not required."* Once constraint-02
says the value is one of four, this cannot be violated.

The tool rated it `partially supported` and prescribed a test:

> **detects:** The implementation stores a single value but derives it from two
> redundant internal flags that happen to agree on the fixture.

It does not recognise the obligation as unfalsifiable. It invents an
implementation that could fail — redundant internal flags — and prescribes a test
against that. The invented implementation is not the one under review.

This is a genuinely useful result and worth its own issue: an obligation true by
construction should be recognised, not answered with a test for a hypothetical
defect in code that does not exist.

## Unrequested changes — all three `in_service`, all three fair

The pipeline filtering, the report's two new "not required" lines, and the
verdict's handling of `neither`. Each is a real consequence of the mandate rather
than something it asked for directly, and `in_service` is the right disposition.

## Disposition

**Gate 2 fails, for the fourth time, and in a new way each time.** The working
agreement's rule about failing twice applies: the next move is a different
approach, not another turn of the same handle. Stopping here to report.
