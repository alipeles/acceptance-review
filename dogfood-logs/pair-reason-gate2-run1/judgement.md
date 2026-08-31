# Gate 2 judgement — ask for a pair's reason only where the test would fail

**Not clean, which is permitted here**: CLAUDE.md suspends the clean-or-stop rule
until #312's sub-issues land. Run once, not iterated. Base `21d5237`, head
`0edfbaa`, run `6e234f89dd0be6a8`, continuing decompose run `feb089a9c3e1ef4e`.

`INCOMPLETE`: 24 of 24 requirements yielded obligations, 24 of 25 fully
implemented, one — `deterministic-recorded-runs` — rated `unclear` on code
evidence. Every obligation is strongly supported on test evidence. No open
questions, nothing flagged as needing non-code evidence or human review, no
recommended tests beyond the criterion above.

**Directory naming is provisional**, as for Gate 1: rename to the issue number
once one exists. The human's call was that this work is part of #314 rather than
a superseding issue, so these may become `314-gate2-run2`.

## The one finding, and it was real

`deterministic-recorded-runs/lenient-unusable-reason-nondeterminism`:

> The new unusable-shape path records different reason text for the same kind of
> bad answer depending on whether the model omitted the reason key or returned an
> empty string, so repeated runs can persist different review-state bytes for the
> same input.

**The stated consequence is wrong and the observation underneath it is right,
and the observation was worth more than the label.**

Wrong: there is no nondeterminism. Two recorded runs over the same input replay
the same transcript and produce the same bytes; what differs between the two
cases the finding names is the model's *answer*, which is an input to this code,
not a run-to-run variation of it. `test_two_runs_over_the_same_input_agree_byte
_for_byte` covers this and passes.

Right, and worse than the finding says: `_ask` rejected a surviving answer
whenever a `reason` key was present **at all**, including `"reason": ""`. Two
consequences.

1. `""` is exactly what this stage emitted on every surviving pair before the
   union, and what a provider honouring the schema only loosely would emit. Every
   surviving pair of such a run would have gone to `unjudged` — about 99 pairs in
   100 on the corpus this was measured against — leaving a review with almost no
   verdicts. Not cosmetic.
2. The rejection sentence said "carrying a reason" about an answer carrying an
   empty string, which is untrue.

It was also stricter than the mandate: `current-task.md` says an answer "that
reports the test would not fail and carries a reason anyway" is not accepted, and
an empty string is not a reason.

**Fixed** — the test is now `elif not judged.fails and reason:`, so only a
non-empty reason is refused — and pinned by
`test_a_surviving_answer_carrying_an_empty_reason_is_still_a_verdict`. A killing
answer with no reason is still refused, deliberately: a killing verdict is what
becomes a coverage claim, and recording one with no traceable basis is worse than
recording the pair as unjudged, where it stays visible.

Two of the other enumerated defects, `preserve-completion-ratings-and-test
-recommendations/reasonless-survives-treated-as-unjudged` and
`.../missing-reason-for-failing-verdicts`, point at the same code from a
different obligation and are addressed by the same fix.

**The fix did not re-arm the gate.** The suspension says a correction made in
response to a finding does not oblige another run. `check` was not re-run. Full
suite green afterwards: 1660 passed, 2 xfailed, against a 1653 baseline taken
before this work.

## What the tool got right that is worth recording

The finding sits under the one obligation the run rated less than fully
implemented, and the code lines it cites are the lines that were wrong. The
review reached a correct observation about `_ask` through an incorrect theory
about determinism. Read as a pointer it was accurate; read as a diagnosis it was
not. That distinction is the useful part for #185, the umbrella for the findings
model and presentation: the defect's *description* asserted a consequence the
enumerator had no basis for, while its `code_refs` were exactly right.

## Advisory pair comparison

The shadow block reports most criteria as `partially_supported — kills 1 of 2
enumerated defects` where the review itself says `strongly_supported`. That is
the expected disagreement this milestone exists to make visible, not a finding:
nothing here moved a rating, and #316 is the issue that flips the review onto the
derived column. `deterministic-recorded-runs` is the one criterion where the two
agree at `strongly_supported`.

## Not re-filed

Nothing. The single finding was a real defect in the work under review and was
fixed, so there is nothing to attribute to a tool defect. The observation about a
defect description asserting an unfounded consequence is noted above and queued
in `docs/DEFERRED.md` rather than filed, since it is one instance and not yet a
pattern.
