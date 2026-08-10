# Judgement — #232/#219/#230 bundle, Gate 1, run 4

Pointer sentence removed. 21 requirements, 20 with obligations. **No open
questions.** This is the task file implementation proceeds against.

## The task file is now as good as I can make it

Task prose yields two obligations, both genuine restatements of the two
distinctions. `constraints-state-both` is gone. No obligation inverts a
requirement. Every remaining defect below is the tool's, and all of them are in
this bundle's scope.

## New and the sharpest finding yet: #232 is unstable *within a single run*

Five Completion expectations, one sentence shape ("A test asserts that …"), two
different treatments in the same call:

| | derived obligation | framing |
|---|---|---|
| `completion-02` | "**Produce a test that asserts** an acceptance criterion demanding a test yields an obligation whose demand is the test itself." | **kept** |
| `completion-03` | "**Produce a test that asserts** an obligation demanding a behaviour and an obligation demanding a test of that behaviour are not recognised as stating the same requirement." | **kept** |
| `completion-04` | "Preserve the rule that sibling bullets worded alike … receive the same disposition." | dropped, merged into `constraint-04` |
| `completion-05` | "Produce a reason for no-obligation dispositions that states no property …" | dropped, merged into `constraint-05` |
| `completion-06` | "Preserve byte-identical review state across two runs …" | dropped, merged into `constraint-07` |

#232 as filed says the framing is dropped, and that it is unstable **across task
files**. It is unstable **within one call over one section**, 2 kept / 3 dropped,
and the three dropped are exactly the three that then merged with their Constraint
twin. The run-1 measurement was 0 kept / 5 dropped on nearly the same text.

This tightens what the fix must achieve and what its test must assert: not "the
framing is usually kept" but that it is kept for every sentence of the shape.
Worth adding to #232's acceptance — same-run consistency, not only cross-file.

Note also that run 2's contradicted linking clique has resolved here, so the three
merges reappeared. Confirms run 2's judgement: the absence of merges there was
suppression, not discrimination.

## Unchanged — #219 / #230

Four of six scope exclusions still yield obligations to do the excluded work:

```
[exclusion-03] Which open questions are raised, and what they cite, which is #206.
    -> open-questions-and-citations  [human_review/explicit]
       Raise open questions when the task text is materially underspecified, and
       include what each question cites.

[exclusion-04] How finely a single requirement is split into obligations, which is #117.
    -> requirement-splitting-granularity  [functional/explicit]
       Split a single requirement into obligations at the level of distinct
       computations or behaviors, keeping cohesive behaviors whole.

[exclusion-05] Whether obligation identifiers are stable across task-file edits, which is #231.
    -> stable-obligation-identifiers  [invariant/explicit]
       Keep obligation identifiers stable across edits to the task file.

[exclusion-06] Measuring how accurate decomposition is, which is #211.
    -> decomposition-accuracy-measurement  [human_review/explicit]
       Measure how accurate the decomposition is.
```

`exclusion-01` and `-02` are correct, typed `compatibility`.

**Typing of the two correct exclusions, across four runs on byte-identical bullet
text:** `human_review` → `invariant` → `compatibility` → `compatibility`. Four
runs, three types. Attributable to #231 (any task-file edit re-derives every
requirement), so not evidence of instability on unchanged input — but it is the
mechanism by which #230's inconsistency reaches a reader.

## Gate 1 disposition

**Not clean, and cannot be** — every defect remaining is one of #232, #219 or
#230, which is what this task fixes. Recorded against those issues; comments filed
on #230 and #212. Proceeding on the human's explicit go-ahead, with Gate 2 as the
gate that must come back clean.
