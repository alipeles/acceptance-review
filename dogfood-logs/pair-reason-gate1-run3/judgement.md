# Gate 1 judgement — ask for a pair's reason only where the test would fail

Three decompose runs. **Run 3 is the one that passed**; runs 1 and 2 each found a
real problem in `current-task.md` and both problems were mine.

**Directory naming is provisional.** These are `pair-reason-gate1-run{1,2,3}`
rather than `<issue>-gate1-run{1,2,3}` because the issue is drafted and not yet
filed — filing needs human approval at this gate. Rename all three to the issue
number once it exists.

**Runs 1 and 2 have no `current-task.md` beside them, and that is a lapse.** The
task file changed between runs and only run 3's copy was kept. What differed is
recorded exactly below, because it is recoverable from the edits; that is not the
same as having saved it, and the next multi-run gate should snapshot the input
before each run rather than after the last.

## Run 1 — `b96eaab92f1e5ce0`, 24 requirements, 25 calls, $0.1439

Two obligations were wrong, both traceable to weak wording rather than to the
decomposer.

**`no-reason-on-failing-pair` said the opposite of the mandate.** The scope
exclusion read *"Whether a reason is worth keeping on a pair where the test would
fail. It is kept."* and the obligation derived from it was *"The change does not
keep a reason on a pair where the test would fail."* Inverted. The cause is that
the bullet was doing two jobs: excluding a question from scope and answering it.
Every other exclusion in the file is a bare noun phrase, so the decomposer
applied the exclusion template — "the change does not ..." — to the wrong clause.
**Fixed by deleting the bullet**; the reason on failing pairs is already stated
positively by constraint-01, so nothing was lost.

**`pair-selection-stability` collapsed three claims into one.** The constraint
read *"Which pairs the review judges, when it reuses a verdict rather than
producing it again, and when it produces one again, are unchanged"* — three
things in one sentence — and the obligation came back as *"The set of pairs the
review judges stays unchanged when it reuses a verdict instead of producing it
again"*, which conditions the first claim on the second and means something the
mandate does not say. **Fixed by splitting into separate bullets.**

## Run 2 — `c3f1f15b4bdfa46c`, continuing run 1. 25 requirements, 3 calls, $0.0185

`--continue` behaved as CLAUDE.md describes: 22 obligations carried, 2 derived, 1
revised, three calls rather than twenty-five, and the dropped exclusion reported
by name rather than silently vanishing.

One obligation was still wrong. `pair-selection-stability` **carried forward its
run-1 text** — "The set of pairs the review judges stays unchanged when it reuses
a verdict rather than producing it again" — against a constraint that had been
rewritten to say the conditions for reuse are unchanged. The carry preserved a
stale reading. This is the carry mechanism working as designed on a requirement
whose wording changed less than its meaning did, and it is worth knowing: a
reworded constraint does not guarantee a re-derived obligation.

The split had also produced two constraints saying the same thing from opposite
directions — one about reuse, one about producing again — which is the redundant
pair CLAUDE.md warns about. **Fixed by collapsing both into one bullet** about
the conditions for reuse.

## Run 3 — `feb089a9c3e1ef4e`, continuing run 2. 24 requirements, 1 call, $0.0058

**Passed.** 24 requirements, 24 obligations, one per requirement, no invented
obligation and none of the real ones missing. `verdict-reuse-conditions-unchanged`
now states the constraint as written. Confirmed by the human at this gate.

Continue this obligation set with `--continue feb089a9c3e1ef4e`.

## Open questions

**Zero, on all three runs.** That is #303's known behaviour — the decomposer
raising no open questions at all — and is **not** evidence that the mandate was
unambiguous. Nothing was triaged because nothing was raised. Recorded here so the
absence is not later read as a clean bill of health.

## Cost

$0.168 across three runs, of which $0.144 was run 1. The two corrections cost
$0.024 between them because both were continued runs.
