# Judgement — #315, Gate 1, run 2

Run id `3aa3bcb7cd13414e`, continuing `b6c50be77e12866f`, at `dc9a22a`. The only
input change from run 1 is the rewritten Task section.

`requirements: 0 derived, 25 carried, 1 revised; 2 decompose call(s)` — $0.011
against run 1's $0.17.

## Gate 1 passes on this run

26 requirements, 25 with obligations, 1 deliberately none (`completion-01`,
*"Implementation."*, correctly yielding nothing — it is a section marker, not a
demand). No open questions. No invented obligations; no requirement of mine
unrepresented.

## The carry behaved

I verified this by diffing the two runs' `output.log`. The whole diff is
`task-01` plus the run footer: every one of the other 25 requirements produced
byte-identical obligations, ids included. That is what `--continue` is for, and
it is the outcome #251's Gate 1 showed is *not* free without the flag — there,
rewording one bullet inverted whether four untouched requirement pairs merged.

`task-01` now yields the single obligation `scores-failures-against-reference-set`,
replacing run 1's three, one of which was an unusable sentence fragment. The two
figures it previously duplicated are left to `constraint-07` and `constraint-08`,
which state them properly.

## Findings carried over from run 1

`completion-03` is still typed `invariant` where its five siblings of identical
form are `test_demand`, and is still merged into `constraint-02`, so the demand
that a test exist for it is still absent from the obligation set. Carried
unchanged from run 1, as expected — a carried requirement is not re-derived.
Attributed to the tool, recorded against the existing `docs/DEFERRED.md` entry
*"Two obligation-type slips, one of which loses the `test_demand` distinction
DR-232 exists to carry"*. No wording of mine fixes a type.

The practical cost to this task is small and I will cover it in the
implementation: the property `constraint-02` states needs a test whether or not
an obligation demands one, and `completion-02` (a separate, correctly-typed
`error_handling` obligation about rejection) already forces most of that shape.

## Open questions

None. Same known cause as run 1 (#303).

## Disposition

Gate 1 passes at `dc9a22a` on run 2. Proceed to implementation.
