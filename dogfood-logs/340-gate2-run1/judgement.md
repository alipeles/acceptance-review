# #340, Gate 2, run 1 — not clean, and the issue's headline target is unreachable

Run `d175a70ee540e9e0`, continuing Gate 1's `e0c0ad243a8456ef`. base `f74a016`,
head `4ad8290`. **INCOMPLETE**: six criteria partially supported, six recommended
tests, 22 pairs unanswered, ten `separable` mentions. Spent $2.8942 live.

## The measurement, which is the real finding

Routing worked exactly as designed and saved about a tenth of the pair stage, not
the four fifths #340's Acceptance asks for.

| | pairs | calls | cost |
|---|---|---|---|
| put to the model | 14,228 | 408 | $2.8768 |
| dropped as not worth asking | 1,526 | — | — |
| settled by the run | 0 | — | — |

15,754 pairs were formed and 1,526 were dropped, so the stage issued about 90% of
the calls it would have issued unrouted. #340 asks for under 20%.

**Correction.** My first reading of this called the cause structural and said
more than half the defects "name no editable region". That is wrong, and I
withdraw it. The 37 `not_mutable` attempts are edits the model *did* produce and
the mechanical checks *refused*. The cause is the edit builder, which is fixable.

Only an attempt that is observed and killed can drop anything, and of 68:

| outcome | count | drops anything? | why |
|---|---|---|---|
| `not_mutable` | 37 | no | the edit failed a mechanical check — see below |
| `survived` | 18 | no | rule 3: an edit nothing failed under shows nothing |
| `killed` | 12 | yes | |
| `already_present` | 1 | no | |

The 37 refusals, by check:

| count | share | refused because |
|---|---|---|
| 23 | 62% | the replacement was **identical to the code it replaced** — the model returned the original |
| 9 | 24% | the mutated file **did not parse** |
| 3 | 8% | the edit exceeded the 12-line bound |
| 2 | 5% | a breadth refusal, and one malformed answer |

So 86% of the lost defects are a model that either changed nothing or produced
invalid Python. #334 (sample several candidate edits and take the first that
passes the gates) and #338 (a headless coding-agent injector) are the filed work
that addresses exactly this.

**A second loss: 76 of about 232 candidate tests never ran against any edit.**
71 of them "failed against the code as delivered", 4 passed in the project but not
in an unmodified copy, and 1 exceeded its time budget. The full suite passes 1672
tests locally, so these are failing in the sandboxed copy rather than being
broken. Their pairs can never be dropped, because the run holds no observation
about them. Within the 10 defects where routing fully applied it dropped 154 of
each defect's ~232 pairs; the ~76 it could not drop are these.

**Where routing did apply it worked.** 10 defects dropped 152–154 pairs each.
Two more dropped nothing because rule 6 fired — their judged pairs yielded no
kill, so the run had shown nothing usable and the pairs went to the model after
all, which is the rule working.

#340's Why section estimated the saving from "268 kills in 23,808 pairs", the
share of *pairs* that survive. The saving is bounded instead by the share of
*defects* that produce a kill — a defect with no kill holds nothing back. That
part of my first reading stands.

**The large saving needs #335, not this issue.** With edit verification on, a
verified attempt settles its defect and `remaining_defect_sets` drops the whole
defect from the judge — and that applies to a *survival* as much as to a kill,
because `verdicts_from` emits a verdict for every test the mutant ran against.
On this review the 12 killed and 18 survived attempts hold 30 of 68 defects; with
verification working and the edit builder fixed, most pairs would leave that way.
Routing alone can only ever drop the non-killing tests of defects that were
killed.

The unrouted control run has not been done. It would cost about another $3 and
its result is predictable from the numbers above, so it is not worth running until
the design question below is settled.

## Findings, and what I did with each

Every one of the six is *behaviour present, test absent* — the thing this tool
exists to catch. Two were also genuine report defects.

1. **`dropped-pair-drop-reason-recorded`** and
   **`dropped-pair-not-demonstration-of-test-failure`** — the reason is in the
   report 1,526 times and says "this is not evidence that the test fails to catch
   the defect", but **no test asserted the rendered report contains it**. Fair.
   Added `test_the_report_says_a_dropped_pair_is_not_evidence`.
2. **`injection-attempt-basis`** — same shape. Added
   `test_the_report_names_the_defect_whose_edit_the_decision_rests_on`.
3. **`report-says-how-many-pairs-run-decided`** — **a real defect.**
   `_pair_disposition` returned `[]` when all three counts were zero, so a
   `not_mutable` defect got no line at all, and the report was silent about it
   rather than saying zero. Removed the early return; added
   `test_the_pair_counts_are_stated_even_when_they_are_all_zero`.
4. **`red-test-does-not-identify-defect`** — fair. Added
   `test_a_kill_is_never_read_as_naming_the_defect`, which pins that the red
   test's own pair is still judged and its verdict comes from the model.
5. **`inject-edit-for-each-plausible-defect`** — the finding is about the
   pre-existing injection stage, not this change. The criterion exists because my
   task file's opening sentence describes behaviour the review already has (run
   5's judgement records that choice). It is a true observation — 37 of 68 defects
   got no edit — and it belongs to #45's area, not this one.

## A defect I found myself, and fixed

**The report became 83% one block.** The unjudged-pair listing was 636 KB of a
768 KB report: 1,526 dropped pairs at one pair line and one identical reason line
each, burying every finding among them. `_pair_block` was written when unjudged
pairs were rare; routing made it the document. Now counted per defect, with the
reason stated once. Pinned by
`test_the_dropped_pairs_are_counted_not_listed_one_by_one`.

## A consequence I did not anticipate: the suite is four times slower

The full test suite went from 448s to 1858s — 7.5 minutes to 31. `route_pairs`
defaults to on, so `decide_execution` now says yes in every test that constructs a
plain `ExecutionSettings()`, and each of those reviews copies the project, runs a
baseline and runs the candidate tests against an edit. Nothing is wrong; the tier
is doing what it was told. But it is now doing it on every CI run, and the cost
lands on everyone.

`1672 passed, 1 skipped, 2 xfailed`, ruff check and format clean, so this is a
time cost rather than a correctness one. Queued as a decision rather than fixed
here: the obvious answer is for the tests that do not care about execution to pass
`route_pairs=False`, which is a change across many files and is not this task's
area.

## Not yet dispositioned

- **22 unanswered pairs.** Not investigated. #331, the filed defect where every
  unjudged pair in a run named one test and a rerun judged them all, is the
  likely shape but I have not checked.
- **Ten `separable` mentions.** Not read.
- **One set-aside candidate test**: "the test passes in the project but not in an
  unmodified copy of it… In the copy it was: failed". That is the control run
  protecting against a false kill, working. Which test, and why it fails in a
  copy, is not investigated.

## The gate is not re-armed

The fixes above change the diff, so `check` must be run again and come back clean
before this can move. That is another ~$3 and the design question — whether a 10%
saving is worth shipping — should be answered first.
