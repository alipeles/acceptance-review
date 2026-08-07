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
| `closing-line-points-at-retrieval-command` | **A REAL GAP — this judgement was wrong when first written.** See below. |

## Unrequested changes

One, `[in_service]`, and accurate: the `_supplied_enum` helper added to
`tests/support.py` to auto-complete empty recommendation lists in the doubles.
Necessary — under the new invariant a double returning `{"recommendations": []}`
is a broken checker rather than a no-op one — but genuinely not named by the
mandate. Recorded rather than waved off.

## Not clean, so no PR

Two of three attributed to #148, one to #180/#193. All three tracked. Nothing
waived, nothing suppressed.


## Correction: one finding was dismissed without being checked

The row above originally read *"tautology; the line is asserted by existing
report tests"*. That was asserted, not verified, and it was false.

Only the **negative** branch was covered — `"Recommended next instruction:
(none)"`, in three places. The line the obligation actually names —

    Next: retrieve a criterion's full recommendation with
      acceptance recommendation --criterion <id>

— appeared in **no test anywhere**, only in committed fixture logs under
`tests/fixtures/rating-stability/`, which assert nothing. `_has_gaps` has two
non-trivial conditions and only its false branch was exercised.

It matters: that line is the only thing telling an agent the full prescription
is retrievable, and M7.3.r1 replaced a written file with it precisely so a stale
artifact could not contradict the report.

Both branches are now covered by
`test_a_review_with_gaps_closes_by_pointing_at_the_retrieval_command` and
`test_a_review_with_no_obligations_does_not_advertise_retrieval`.

**The process failure is the point.** CLAUDE.md requires reading a recommendation
before forming an opinion on the finding — and this dismissal was written
*after* quoting that rule in the same session. Instability in the surrounding
findings made "probably noise" an easy and wrong default. DR-180's warning is
exactly this: instability is not a licence to dismiss a finding.
