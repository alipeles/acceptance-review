# Judgement — #316 Gate 2, run 1

Run over base `11e9bf0`, head `3e1d3a9`. 1,012 live calls, **$6.87**, 992 of
them pair judgements. Gate 2's clean-or-stop rule is suspended for this task
(CLAUDE.md's block covers #313 through #316), so this is one run and the
findings are triaged rather than iterated to green.

**Not clean.** Verdict INCOMPLETE: one criterion not fully implemented
(`rating-by-coverage-completeness`), two with non-discriminating test evidence
(`remove-older-test-judgement`, `no-plausible-failure-outcome`). Two recommended
tests. No open questions. Everything else strongly supported.

## The two findings that are real, and both are about my task file

**1. `rating-by-coverage-completeness` is partially addressed, and the tool is
right.** constraint-01 still said a criterion no test catches is *nominally*
supported. The human ruled during this session that `nominally_supported` is not
worth keeping and that such a criterion is `unsupported`, and I implemented that
without updating the mandate. The check compared the mandate to the code and
found the disagreement. **Fixed** by rewording constraint-01.

**2. `keep-rating-names/changed-meaning-of-unsupported` — the sharpest thing in
the run.** The enumerated defect reads: *"`unsupported` is redefined to mean that
no candidate test would fail on any enumerated defect, instead of meaning there
is no mapped, obligation-relevant test at all, so the same name now denotes a
different condition."* That is exactly what I did, and constraint-06 said "what
each of them means is unchanged". **Fixed** by dropping that clause; the names
are what the constraint protects, and constraint-01 defines the meanings.

Both are stale wording in `current-task.md`, not defects in the code. Neither
required a code change. Per the suspension, the check was not re-run.

## What the run got right that is worth recording

The enumeration produced 48 defects across 30 criteria, and several are
genuinely on point — `concurrent-call-order-leaks-into-unusable-log` names the
exact hazard the concurrency change had to avoid, and
`report-denominator-rendering-can-diverge-from-state` names the reason the
denominator is stored beside the class rather than recomputed at render time.
Neither was prompted by anything in the task file.

## Findings attributed to known defects, not re-filed

- **`recommended-test-names-failing-way` is `indeterminate` with no mapped
  test**, because nothing was enumerated for it. It is typed `test_demand`, and
  the enumerator declines to enumerate for that type. Known shape; noted.
- **Every unjudged pair is a prefilter exclusion against one test**,
  `tests/test_decision_records.py::test_dr_202_...`, which imports no
  first-party module. The filter is doing its job.
- **An unrequested change flagged `in_service`:** adding `no_plausible_defect`
  to the rating vocabulary. Correct observation — the mandate asks for a
  distinct outcome and does not ask for a new named class. Accepted as in
  service of constraint-03.

## Cost, and what it says

$6.87 against #314's Gate 2 at $4.25, on **fewer** criteria (30 against 37) and
**fewer** defects (48 against 75). The driver is candidate tests: 496 against
166, because this branch deletes six modules and rewrites much of the suite, so
discovery offers three times as many. Pairs judged went 12,450 → 23,808.

Per pair the stage is cheaper, and yesterday's response-shape work is visible in
it: output per pair fell from 43.9 tokens to 29.1, a 34% drop, larger than the
pilot's projected 18%. Prompt per pair rose from 112 to 163 because a call's
fixed cost now amortises over 24 pairs rather than 37.

**Every stage reported 0.0% cached, and that is measured waste, not a quirk of
this run.** The shared prefix is present and large enough — messages 0 and 1 run
~1,544 tokens against OpenAI's 1,024 floor and take 6-7 distinct values across
all pair calls, so the defect-list move landed in #314 works. What defeats it is
that every call sends a unique response schema: 1,762 distinct across 1,762 pair
calls, collapsing to 7 if the `test_id` enum is removed. Filed rather than
fixed — see the queue entry, and the reason is that removing that constraint
risks recall and the response-shape pilot is the instrument that should settle
it.
