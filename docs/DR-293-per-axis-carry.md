# DR-293: the two review axes carry separately, and only one of them carries

**Issue:** #293. **Status:** decided and implemented.
**Supersedes the reasoning in:** `rerun.py::stale_obligation_ids` (deleted) and
`rerun.py::merge_carried_forward` (deleted).
**Related:** #292 (`DR-292`), #291, #286, #269 (`DR-269`), #305.

## What was decided

1. A criterion's **test-evidence rating** is carried when its requirement text,
   its mapped test set, and the **contents** of those tests are all unchanged.
   Comparison is per test, never per file.
2. A criterion's **implementation coverage** is re-derived on every run. It has
   no staleness rule at all.
3. The single predicate that used to answer both questions is deleted, along with
   the wholesale carry built on it.

## Why the file-level rule had to go

`stale_obligation_ids` marked an obligation stale when the change touched any
file it cited. Its own docstring defended the coarseness: over-invalidating costs
a re-derivation, under-invalidating reports a stale judgement as current, so it
leaned toward re-deriving.

That trade assumed re-deriving is merely expensive. It is not.

- #269's Gate 2: one commit adding nine tests and changing no source collapsed
  *strongly supported* from 37 obligations to 4.
- #291's Gate 2: nine lines appended to `tests/test_carry.py` dropped
  `reuse-decision-reaches-answer-through-shared-rule` and
  `reuse-refusal-carries-reason` a tier each. Both criteria's own mapped tests
  were byte-identical; only the file had moved.

Appending a test to a module leaves every existing test in it byte-identical.
That is the distinction the file-level rule could not draw, and drawing it is the
whole of this issue.

The damage is worse than noise in a metric. Every fix made in response to a Gate 2
finding edits a test file, which re-triggers the cascade on every criterion mapped
to that file — #291's Gate 2 went from 5 non-discriminating obligations to 8
*because* the correction was applied. A gate that degrades when you act on it is
unreachable by iteration, not merely unreached.

## Why coverage re-derives instead of getting its own comparison

The mandate required the file-level rule to be removed **and** the two axes to be
decided separately, while its scope exclusions forbade *narrowing* any stage other
than test-evidence judgement. Deleting the predicate leaves coverage with no rule;
the natural replacement — comparing the contents of the cited implementation spans
— is strictly narrower than the file-level rule, so it was excluded.

Re-deriving everything satisfies all three at once, and it is nearly free:
`classify_coverage` is a **single batched call** over the whole obligation set
(`coverage/classify.py`), so trimming its input shortens one prompt and never
removes a call. The same argument #293's issue makes about mapping.

Decided by the human at #293's Gate 1, 2026-08-20, with the explicit note that a
content-level rule for coverage is the better end state and is wanted **as a
defence against instability rather than as a cost saving** — the opposite motive
from this half. Filed as **#305**, under #185.

The asymmetry is worth stating plainly, because it is the part a reader will
otherwise trip over: the two axes are not treated alike, and that is deliberate
rather than an oversight. Re-deriving a coverage verdict is currently believed to
be cheaper *and* less harmful than re-deriving a rating; #305 exists because that
belief is untested, not because it is settled.

## The consequence #292's docstring argued against

`merge_carried_forward` took a prior judgement **wholesale** — coverage status,
evidence class, citations, tier — and its docstring argued explicitly against
doing it field by field, on the grounds that splicing a prior evidence class onto
fresh citations produces a judgement no run ever actually made.

That argument was correct **for a design where an obligation carries or does not,
as a unit**. Once the axes are decided separately, an obligation is routinely
fresh on coverage and carried on evidence, so the all-or-nothing form is no longer
available. The objection is answered rather than ignored:

- The carried rating is written back as an `EvidenceStrength` through the same
  write-back every judged rating uses, so no obligation is assembled from two
  runs' fields by hand.
- Its `test_links` are **this** run's mapped tests, which is not a compromise: the
  criterion only carried because its mapped set and those tests' contents are
  byte-identical to what the stored rating was made about, so the two lists have
  the same members.
- `achieved_evidence_tier` stays `static`, which still describes how the rating
  was reached.

## Two disclosures that changed meaning

**`Obligation.carried_forward_from`** used to mean *"this obligation's whole
judgement is from an older head"*. It now means *"this obligation's test-evidence
rating is from an older head"*. Implementation coverage is always this run's. The
field was kept rather than dropped because it is the only thing telling a reader
which part of a review was actually re-examined, and a rating nobody asked about
would otherwise read as fresh.

**Carried findings are gone; carried recommendations are not.** Findings here are
coverage findings, and coverage is now re-derived for every obligation, so no gap
can be dropped by not looking — the guarantee `carried_findings` existed for is
now structural. Recommendations still need carrying, on the *evidence* axis: a
criterion keeping its rating is not asked about, so `recommend_tests` cannot
prescribe for it, and without the carry the instruction for a still-open gap would
vanish on the very run that decided the gap had not moved.

## Why the digests are stored

`Obligation.test_evidence` holds pytest node ids. The source those ids named
during the previous run is gone by the time the next one asks, so a stored rating
cannot be compared against anything unless the previous run wrote down what it
saw. Hence two new fields: `mapped_test_digests` (per test) and
`evidence_carry_key` (the hash the carry compares), the second computed **from**
the first so they cannot disagree.

Both default to empty. A review stored before #293 therefore carries nothing and
everything is re-derived — the conservative direction, and the same direction a
missing digest takes inside `build_anchors`, where an uncomparable test names no
change and leaves the criterion unanchored rather than frozen.

## What the key deliberately excludes

`rating_carry_key` hashes the **unconstrained** `_Discrimination` schema and the
**unanchored** system prompt. The real request constrains `obligation_id` to the
criteria in the batch and appends the anchor instructions whenever any criterion
is anchored — so a key built from the real request would move whenever a
*neighbouring* criterion changed. Discarding a rating for that reason is precisely
the churn the mechanism exists to remove. Same choice, and the same reasoning, as
`DR-269-carry-key-excludes-registry-context.md`.

## How this makes #292 bite

`DR-292` built the rejection of a re-judgement that moves a rating without naming
a change it rests on, and noted that its anchors were file-level and temporary.
At #291's Gate 2 **nothing was rejected**, because
`mapped-test-file:tests/test_carry.py` was a genuine file-level change and naming
it licensed the downgrade.

The anchors are now per test — `mapped-test-added:`, `mapped-test-removed:`,
`mapped-test-edited:`, each naming a node id. In that same scenario neither
criterion is anchored at all, and #292's existing rejection holds both ratings
**with no new enforcement code**. The two halves compose exactly as `DR-292` said
they would.

Implementation citations stay file-level: `coverage_refs` are precise to a file
and a hunk label, and this issue changed the test axis only.

## What this does not do

- It does not make mapping stable (#182). A spurious mapping change still forces
  a re-judgement; #292's rejection is what stops that moving the rating.
- It does not make any rating correct on its merits.
- It does not narrow any stage other than test-evidence judgement.
