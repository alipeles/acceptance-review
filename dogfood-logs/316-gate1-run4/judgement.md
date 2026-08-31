# Judgement — #316 Gate 1, run 4

Run `24167c83efda44b4`, continuing `b436ac408cd65b32`. 0 derived, 13 carried, 1
revised, 1 requirement removed; 1 decompose call, $0.0055. No open questions
raised.

**Accepted.** 14 requirements, 13 with obligations, one Completion expectation
deliberately yielding none. Every obligation traces to a sentence I wrote; no
obligation states something the task file does not; no two obligations state the
same thing.

## Findings

**1. The deleted scope exclusion was reported, not silently dropped.** The run
printed `REMOVED exclusion-03: Renaming a rating, or rewording what a rating
means. (1 obligation(s) dropped)`. That is the behaviour #306 exists to give —
worth recording as it working, since the same machinery was inverting replaced
exclusions as recently as #314's Gate 1.

**2. One obligation is typed `human_review` and should not be.**
`no-running-delivered-code-or-tests`, from the scope exclusion "Running the
delivered code or any test", is typed `human_review/explicit`. Nothing about it
needs a human: it is a statement about what the change does not do. This is
#196 (the decomposer types automatable obligations `human_review`, a wrong value
rather than an unstable one), open and known. It matters at Gate 2 rather than
here — CLAUDE.md makes anything marked as needing human review a pause, so this
obligation will stop the next gate for a reason that is a tool defect. Noted, not
re-filed.

**3. One obligation is typed `test_demand` and the call is arguable.**
`recommended-test-names-failing-way`, from constraint-04, is about what a
recommendation must contain rather than about demanding a test be written.
`test_demand` may still be the closest available type. Recorded as an
observation, with no claim that it is wrong; it is not treated as a fourth
instance of the type slip #181 already carries.

**4. Still no open questions, across all four runs.** #303, known and open. The
task file has at least one place where a reasonable reader would ask something —
constraint-07's "the review's measured accuracy" does not say where that is
reported — and nothing was raised.

## Disposition

Gate 1 passed at this run, on `origin/main` tip `11e9bf0`. The decomposition is
one I would defend.
