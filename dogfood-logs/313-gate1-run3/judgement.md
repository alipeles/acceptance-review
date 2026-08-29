# #313 Gate 1, run 3 — judgement

First `decompose` of #313 after #317 landed. Runs 1 and 2 (2026-08-21) crashed
before producing anything; this one completed. Task file is the run-1 copy with
its Task paragraph cut to one sentence, and the sentence that restated
constraint-01 and constraint-04 moved into Constraints as constraint-02.

Command: `.venv/bin/acceptance decompose --task current-task.md`
Run id: `747d3c974fc7bc91`. 28 requirements, 27 with obligations, 1 deliberate
none. No `--continue`: the crashed runs wrote no ledger entry.

## The crash is gone

`requirement 'task-01' was disposed more than once` did not recur. Under #317
each requirement gets its own call, so the twelve-dispositions-for-one-requirement
shape that aborted runs 1 and 2 is now unrepresentable. 29 calls for 28
requirements — 28 derivations plus one summary step.

The summary step behaved as designed. `task-01` yielded exactly one obligation,
`pre-test-failure-modes`, covering the one property the Constraints do not
state — that the recording happens per criterion before any test is looked at.
No duplicate of a constraint-derived obligation appeared, which is what the old
summary pass produced on every draw.

## Open questions: none

Zero raised. `_summary_line` in `cli.py` prints a "raised a question" count only
when one exists, and no `?` line appears against any requirement. So Gate 1's
three-case triage has nothing to run on.

## Real findings

**1. Two `test_demand` obligations state the opposite of their requirement.**
Both are the #262 family — a restatement that does not preserve entailment —
and specifically the polarity reversal that #262's second recorded instance
already names.

| requirement | text | derived obligation |
|---|---|---|
| `completion-02` | A test fails when the step that records ways of failing **is given a test**. | A test asserts that the step that records ways of failing **is given a test**. |
| `completion-06` | A test fails when a criterion whose text is unchanged **has its set produced again** because a different criterion's text changed. | A test asserts that a criterion whose text is unchanged **has its set produced again** because a different criterion's text changed. |

`completion-03`, `-04` and `-05` have the identical "A test fails when X" shape
and all three inverted correctly. So this is unstable within one run — 5 of 7
right — not a systematic misreading of the form.

It matters here more than usual. `completion-02` is the acceptance criterion for
test-blindness, which is #313's whole mitigation for #252: an enumerator that can
see the tests drifts its denominator toward what is already covered. The derived
obligation demands the behaviour the design forbids.

**2. `constraint-10` loses half its requirement.** "A run continuing an earlier
run reuses every set it is entitled to reuse, **and produces again only the sets
it is not**" yielded only the first half. The lost half is close to the
contrapositive of `constraint-08`, so nothing material is unstated in the mandate
as a whole, but the obligation does not carry what its requirement says.

**3. Two obligation-type slips.** `exclusion-04` ("How the review gathers, judges
or rates test evidence today") is typed `docs_config`; `exclusion-03`, the same
shape, is typed `compatibility`. And `completion-07` has the same "A test fails
when" shape as `completion-02` through `-06` but is typed `regression` and
described as a behaviour rather than a test demand, which is the distinction
`ObligationType.TEST_DEMAND` exists to carry (DR-232). Type is not cosmetic for
#313: the defect checklist the enumerator walks is chosen by obligation type.

## Disposition

Findings 1 and 2 are corrections to make and re-run — findings 1's two
requirements reworded, finding 2's conjunction split into two bullets. That is
run 4. Finding 3 is left alone: obligation typing is a Scope exclusion of this
mandate ("Which criteria the review derives from the mandate, and how it derives
them") and there is no wording of mine that would fix it.
