# Judgement — #248 Gate 1, run 2 (NOT DEFENDED)

Command: `.venv/bin/acceptance decompose --task current-task.md --mode record`
Run at `4332228`. Task file rewritten after run 1, once transcript evidence showed
the defect was a schema-induced echo rather than a content duplicate.

**This breakdown was rejected and the task file rewritten again for run 3.**
Kept because it holds the single worst finding of the three runs.

## Finding 1 — `task-01` was given another requirement's obligation, and lost its own

```
[task-01] A requirement that yields one obligation is not read as yielding two.
    -> preserve-decomposition-accuracy-measurement  [compatibility/explicit]   (also serves exclusion-06)
       The change does not alter measuring how accurate decomposition is.
```

The mandate's **headline requirement** is represented by a preservation invariant
about benchmark accuracy measurement — the content of `exclusion-06`, which has
nothing in common with it. `task-01`'s own obligation was never produced.

This is **#223** verbatim: *"A requirement is dispositioned `yielded` onto an
obligation that does not state it, and its own obligation is never produced."*
Attributed to that tool defect; comment queued in `docs/DEFERRED.md`.

Note the direction. #242 is a spurious link **blocking** a merge so nothing
merges. This is a spurious link that **completed** a merge and destroyed the
surviving content — the same defective similarity judgement failing the other
way, which is worth recording as evidence that the two are one underlying
problem.

**Not attributable to task-file wording.** The two texts share no subject,
no vocabulary and no purpose. No rewrite of the headline would have prevented it,
and run 3 confirms it: the headline changed only slightly and the defect vanished,
which makes it an instability, not a response to better input.

## Finding 2 — over-splitting into near-identical obligations (my wording)

`constraint-01` yielded **three** obligations and `constraint-02` yielded **two**,
each set restating one requirement in slightly different words:

```
[constraint-01] -> first-and-remainder-deduplication
                -> head-repeat-counts-as-one
                -> repeat-head-counts-as-one
[constraint-02] -> exact-field-equality-repeat
                -> exact-field-equality-for-repeat
```

**This one is mine.** Run 2's `constraint-01` was a compound sentence carrying two
statements joined by "so" — the obligations are a fair reading of it. Same for
`constraint-02`. Fixed by splitting them into single-statement constraints for
run 3, which yielded exactly one obligation per requirement. This is the
sanctioned rewrite of weak wording, and the tie-break applies: the response made
me regret the phrasing.

## Finding 3 — unreconciled linking cluster, five obligations

Same #242 shape as run 1, enlarged by finding 2's redundant sets. Downstream of
my wording, so not separately queued; run 1's instance is the one cited on #242.

## Verdict

Gate 1 **not** passed on this run. Task file rewritten, re-run as run 3.
