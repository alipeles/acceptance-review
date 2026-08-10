# Judgement — #214 Gate 1, run 2

Command: `.venv/bin/acceptance decompose --task current-task.md --mode record`
Base SHA: `078d216` (branch `214-verdict-mandate-coverage`).

Run 2 exists because the mandate was rewritten between runs: the human ruled
that mandate coverage keys off the **requirement's disposition**, which is
already a structured, validator-enforced pydantic model, rather than off a
heuristic judging requirement text. That correction re-armed Gate 1.

## Result

29 requirements, 28 yielded an obligation, 1 deliberately declined, **0 open
questions**. One flag at the bottom of the output — see below.

## Is the breakdown accurate?

Yes, with one redundancy that I attribute to the tool rather than to the
mandate.

Every one of the 29 requirements maps to the bullet it came from. Nothing
invented, nothing missing. The constraint/completion pairing worked as intended
in six of seven cases: the functional obligation is shared ("also serves
completion-0N") and a separate `test_demand` obligation sits beside it, which is
the #232 distinction being drawn correctly.

`completion-01` (`- Implementation`) was again declined as *"This section marker
stands alone with no requirement under it."* Same call as run 1 on identical
text — the one stability datum this pair of runs offers, and it held.

## The flag: one spurious link stopped a genuine duplicate merging

```
Unreconciled linking answers: answers contradict each other: these obligations
are linked transitively but at least one pair among them was denied, so none of
them were merged
  affected: unanswered-open-question-no-obligation,
            constraint-05-unanswered-open-question-yields-no-obligation,
            exclude-split-granularity
```

`constraint-05` and `completion-06` produced two functional obligations with
byte-identical descriptions. They should have merged, as the other six pairs
did. They did not, because `exclude-split-granularity` — from an unrelated scope
exclusion — was linked into the same cluster, and `_confirmed_clusters`
(`linking.py:382`) merges **nothing** in a cluster containing a denied pair.

**Disposition: tool defect, drafted as a child of #181 and queued.** The reason
it is not a wording problem: the same constraint/completion pattern is used
throughout this file and merged correctly six times. Rewriting my bullet to dodge
it would be editing the input to change the output, which is the one edit the
project forbids.

**Why I proceeded anyway.** The failed merge left every obligation attached to
its correct requirement — `exclude-split-granularity` is still linked to
`exclusion-05` alone, and nothing was wrongly merged. The only cost is one
redundant pair. The obligation set is complete and correctly attributed, so it is
sound to build against; I have noted the redundancy so a Gate 2 wobble on those
two ids is read as this defect rather than as new evidence.

## Open questions

None raised, so the three-case triage has nothing to classify. Same as run 1, on
a mandate that grew from 25 requirements to 29.

## Not a finding

The `constraint-05-` and `completion-09-` / `completion-10-` id prefixes are the
fallback naming used when a slug would otherwise collide. Cosmetic, consistent
with #231's "ids are minted per response" note, and not raised.
