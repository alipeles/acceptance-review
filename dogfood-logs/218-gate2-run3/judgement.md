# Judgement — #218 Gate 2 run 3

`6ae97fd` → `79522b2`. **Not clean, and this is where the work stopped.**
INCOMPLETE, 3 weak obligations.

`no-standalone-recommendations-section` cleared — run 2's fix worked. But
`closing-line-points-at-retrieval-command` and `tests-avoid-live-model-calls`
**came back**, having been absent from run 2 and present in run 1.

## The finding that matters is the instability

| run | head | weak obligations |
|---|---|---|
| 1 | `c61e3cf` | 5 — incl. closing-line, tests-avoid-live |
| 2 | `22738d7` | 2 — **neither** |
| 3 | `79522b2` | 3 — **both back** |

Every change between runs was **additive test-only**. Two obligations flipped
out and back with nothing touching what they judge. That is DR-180's pattern and
#193's, and DR-180's rule applies in both directions: *instability is not a
licence to dismiss a finding* — but it is equally not a reason to keep patching
against a moving target. Three of the five findings withdrawn in one session
under #202 were of exactly this kind.

So: **stopped here deliberately**, rather than chase a set that changes between
runs.

## Disposition of all three

| obligation | disposition |
|---|---|
| `typed-schemas-are-pydantic-models` | **#148** — present in all three runs, and in both of #217's. Design/approach obligation, no test can evidence it. |
| `tests-avoid-live-model-calls` | **#148** — standing repo invariant, not this change's behaviour. |
| `closing-line-points-at-retrieval-command` | **#180/#193** — oscillating. Its recommendation ("the same closing line text but it no longer corresponds to the retrieval command internally") is a tautology; the line is asserted by existing report tests. |

## Unrequested changes

One, `[in_service]`, and accurate: the `_supplied_enum` helper added to
`tests/support.py` to auto-complete empty recommendation lists in the doubles.
Necessary — under the new invariant a double returning `{"recommendations": []}`
is a broken checker rather than a no-op one — but genuinely not named by the
mandate. Recorded rather than waved off.

## Not clean, so no PR

Two of three attributed to #148, one to #180/#193. All three tracked. Nothing
waived, nothing suppressed.
