# Judgement — #217 Gate 1 run 1

At `95a3856` (pre-implementation). **Gate 1 passed.**

`Requirements: 34   with obligations: 33   deliberately none: 1   unaccounted for: 0`

Zero open questions, so step 3 had nothing to triage. The breakdown is accurate:
no invented obligations, none of the real ones missing.

## One finding, attributed

`obl-three-dispositions-only` is linked to five scope exclusions that do not
state it — `exclusion-04` is "nested-bullet parse coverage, which is #216", which
has nothing to do with the disposition set. A scope exclusion carrying a
neighbouring requirement's obligation is **#210** exactly. Attributed there, not
addressed here.

Decomposition confirmed by the human in-session before coding began.
