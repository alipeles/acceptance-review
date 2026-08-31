# Judgement — #316 Gate 1, run 3

Run `b436ac408cd65b32`, continuing `4b869f02db47b1c5`. 0 derived, 14 carried, 1
revised; 5 decompose calls, $0.0314. No open questions raised.

**Not accepted**, for one duplication of my own authoring rather than anything
the tool did wrong.

## Findings

**1. The Task section is now correct.** Splitting the compound subject into three
sentences produced exactly four obligations for four sentences, each carrying the
requirement's content: `test-evidence-rating-derived-from-recorded-judgements`,
`test-prescriptions-derived-from-judgements`,
`conclusion-derived-from-recorded-judgements`, `remove-older-test-judgement`. The
rating obligation that vanished in run 2 is back.

**2. Everything below task-01 is byte-identical to run 2.** Verified by diffing
the two logs from `[constraint-01]` down: no difference. Rewording one
requirement moved that requirement and nothing else. This is the property
`--continue` exists to give, and it is worth recording because #251's Gate 1
measured the opposite when no continued run was named — rewording one Scope
exclusion bullet there inverted whether four untouched requirement pairs merged.

**3. I wrote the same requirement twice.** constraint-06 ("The ratings keep the
names they have today") and exclusion-03 ("Renaming a rating, or rewording what a
rating means") say the same thing from opposite directions, and produced
`keep-rating-names` and `keep-rating-names-and-meanings-unchanged`. The linking
stage did not merge them and raised nothing — the same silence as #304, though
across a Constraint/Exclusion pair rather than #304's Constraint/Completion pair.
The authoring error is mine and the ticket-grade rule forbids it, so the fix is
to say it once. Noted against #304, not filed.

## Disposition

Fold the exclusion into constraint-06 and delete it; re-run with
`--continue b436ac408cd65b32`.
