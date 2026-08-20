# Judgement — #292 Gate 2, run 3 (and the two runs before it)

**Still not clean, and I stopped rather than keep rewording.** One obligation is
`unsupported` — no mapped test. It is a different obligation each run, and each
time it is one half of a pair of obligations that say the same thing.

## The three rounds

| run | task text | result |
|---|---|---|
| gate2-run1 | Gate 1's wording | 2 unsupported: `changed-criterion-gets-stored-rating`, `rating-stability-fixtures-still-found` |
| gate2-run2 | unchanged | 1 unsupported: `changed-test-evidence-rating-justify-itself` |
| gate2-run3 | Task line rewritten | 1 unsupported: `changed-rating-names-one-given-change` |

Run 1's two findings were both addressed with real work, and both stayed fixed:

- I split a test that asserted two things at once, so the stored rating and the
  dependency changes each have their own test. `changed-criterion-gets-stored-rating`
  has been strongly supported ever since.
- I added `test_the_corpus_findings_survive_the_anchored_rejudgement` to
  `tests/benchmark/test_rating_regression.py`, scoring the rating-stability
  corpus with the anchoring mechanism in place. `rating-stability-fixtures-still-found`
  has been strongly supported ever since.

## What is left, and why I do not think more rewording fixes it

Run 3's bare obligation is `changed-rating-names-one-given-change` (constraint-04):
*"A judgement that alters a rating names one of the changes it was given."*

Its recommended test describes
`test_a_move_that_names_no_change_is_rejected_and_the_stored_rating_stands` and
`test_a_move_resting_on_another_criterions_change_is_rejected`. **Both exist.**
They are mapped this run to obligations 7, 8, 9, 23 and 24 — and
`test_a_move_that_names_a_supplied_change_is_accepted` is mapped to obligation 22,
which is **completion-04**: *"A judgement that alters a rating while naming a
change it was given is accepted."*

Constraint-04 and completion-04 are the same rule. The task file states each
Constraint and then mirrors it as a Completion expectation, which is the format's
normal shape, so almost every rule in the mandate exists as two obligations. The
linker does not merge them — that is the unreconciled triangle from Gate 1, filed
as a comment on #242 — and the mapper then attaches the covering test to one twin
and not the other. Whichever twin loses the draw is reported `unsupported`.

**Nothing about the behaviour is untested.** Every rule in the mandate has a test
that would fail if the rule were absent; run 2's bare obligation was covered by a
test mapped to its twin, and so is run 3's.

## The Task-line rewrite, and what it cost

Run 2's bare obligation was `changed-test-evidence-rating-justify-itself` — the
ungrammatical duplicate filed at Gate 1 as **#297**. No test can satisfy it that
is not simply another name for a test its twin already has, so I rewrote the Task
section rather than write one. That is the sanctioned edit: fix the wording, never
the output.

The first attempt made things worse and is recorded as `292-gate1-run2/`: framing
the Task as a summary of the rules made `task-01` yield **ten** obligations
duplicating most of the Constraints, three of which did not merge. The second
attempt (`292-gate1-run3/`) states the thesis instead —

> A criterion's test-evidence rating is a function of that criterion's inputs,
> not of how many times it has been judged.

— and yields two grammatical, genuinely distinct obligations with no constraint
duplication. #297's garbled obligation is gone.

## Disposition

**Attributed to a tool defect, with the filings already open**: #242 (the linker
leaves an exactly-duplicated pair unmerged) and umbrella #182 (mapping decides
differently between near-identical obligations run to run). Both were filed
before this run, so nothing new is queued for it.

I am not rewording further. Three rounds moved the bare obligation between
members of duplicate pairs without reducing the count below one, and the next
reword would be chosen to move the mapper rather than to say the requirement
better. That is tuning the input to change the output, which the invariant
forbids.

**This is a stop, not a clean gate.** The decision on what to do about it —
accept the attribution, fix #242 first, or trim the mandate's own Constraint /
Completion redundancy — is the human's.
