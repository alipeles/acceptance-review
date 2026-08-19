# Judgement — #269 Gate 2, run 2

`check --task current-task.md --base 9def9e7 --head 8e6a934`.

**Not clean.** `Task completion: INCOMPLETE` — *2 obligation(s) with
non-discriminating test evidence (completion-10-fixtures-still-produce-recorded-movements,
revised-requirement-records-revision-reason).*

Run 1's finding is gone: `schema-change-blocks-carry-forward` is now
`strongly supported`, citing both new tests.

## Finding 1 — a real defect, not a missing test

`constraint-33` — *a revised requirement's disposition records why it was
revised* — came back unsupported. Investigating it found the behaviour was
**absent**, not merely untested.

A carried requirement's disposition was built by `_carried_disposition`, which
stamps `derivation="carried"` and `carried_from`. A **revised** requirement's
disposition came out of the ordinary `_requirement_map` path, which knows nothing
about carry-forward — so it reported `derivation="derived"` and
`revision_reason=None`, which is exactly what a genuinely new requirement
reports.

That is not cosmetic. The whole point of the revised path is that the requirement
had a predecessor and was re-asked against it, with its obligation identifiers
available for reuse. A disposition that cannot say so loses the only record that
an id could have been reused and was not. Fixed in `7fc842d` by `_stamp_revisions`,
with one shared definition of the reason feeding both the disposition and the
ledger so the two cannot drift apart.

## Finding 2 — the constraint this feature could most easily violate

`completion-10` — *the decomposition movements recorded as correct in
`tests/fixtures/decompose-stability/` are still produced when the task file
genuinely changes* — came back unsupported, and the recommendation named the
right shape: drive the real path with one requirement edited and another
byte-identical.

This is DR-180's constraint: **do not buy stability by blunting the decomposer.**
#191 is the cautionary tale — its pre-change discrimination judge scored
beautifully on variance precisely because it answered `caught` to 114 of 114
defects. A carry-forward that carried everything would score perfectly on every
stability assertion in this branch and be exactly as useless.

Addressed in `7fc842d` with a test whose re-derivation returns a **different**
obligation from the one on file, so an implementation that carried the edited
requirement anyway would still show the superseded obligation — and would pass
every other test in the module. That is what makes it discriminating rather than
confirmatory.

## What run 2 establishes that run 3 then could not

Every other obligation was addressed, no open questions were unresolved, and both
merge-decision obligations — `carry-forward-unchanged-merge-decisions` and
`reask-merge-decision-when-either-obligation-changed` — were
**`strongly supported`**, each citing two tests.

That last fact is the baseline for run 3's second defect: one commit later, on
untouched evidence, both were rated not-strongly-supported.

## Dispositions

Both findings addressed in code. No tool defect attributed from this run.
