# #340, Gate 1, run 2 — the first decomposition, and it inverted the mandate

Run `469fb7a97284a3d6`. 13 requirements, 13 with obligations, no open questions.
First run, so no `--continue`.

## What was wrong, and whose fault it was

My task file opened with a paragraph of background describing how the review
behaves **today**. The decomposer cannot tell background from requirement, and
turned that paragraph into three obligations, one of which states the opposite of
what the task asks for:

- `candidate-defect-test-pairs-are-modeled` — *"Every combination of a plausible
  defect and a candidate test is still put to a model."* An implementation that
  delivers #340 fails this obligation.
- `review-cost-is-mostly-model-calls` — an observation about cost, not a
  requirement.
- `test-would-not-catch-defect` — an observation about answers, not a requirement.

`task-05` repeated the shape from a second background sentence, producing
`run-consumes-only-on-edits-checked` (*"The run is consumed only when edits are
checked"*), again the inverse of what is wanted, plus
`review-declined-to-run-on-that-ground`, a past-tense fact stated as an
obligation.

## Disposition — my wording, not a tool defect

Rewritten for run 3 with every past-tense and present-tense description of
existing behaviour removed, so the Task section says only what must be true when
the work is done. Run 3 dropped `task-01` outright and all three of its
obligations with it, and none of the inverted obligations recurred. That is what
makes this an authoring fault rather than a defect worth filing: the same
decomposer, given forward-looking prose, did not invert anything.

The lesson is the one `CLAUDE.md`'s task-file style section already states, and I
broke it: a narrative Task section says what must be true when the work is done,
not what is true now.
