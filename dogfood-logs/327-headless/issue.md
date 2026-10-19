# #327 Defects are enumerated for criteria owed no test, and nothing can ever read them

`pipeline.py` gives `enumerate_defects` every obligation, including the ones `required_evidence` says no test is owed for (#266).

Their defects reach nothing. `defects/support.py::derive_support` runs over `needs_tests` only, and `coverage/recommendations.py::recommend_tests` filters on the same predicate. So each such criterion costs one enumeration call per run and produces records no consumer reads.

The enumerator asks about one criterion per call, so the waste scales with how many scope exclusions and code-only criteria a mandate has. #316's own task file has three.

## Fix

Pass `needs_tests` rather than `obligations`, and move the call below the `needs_tests` split. The call's position relative to test discovery must not change — #313 placed enumeration before any test is discovered on purpose, so a denominator cannot drift toward what is already covered (#252) — and `needs_tests` is computed from decomposition alone, so the ordering constraint survives.

## Acceptance

- A criterion whose `required_evidence` demands no test is absent from every enumeration request, asserted against the request rather than the output (the #266 pattern: an obligation offered and then dropped passes an output check).
- A criterion that does require tests is still enumerated for, as the control.
- Narrowing what the enumerator is given re-records its transcripts; note the cost where the figures render.

Found during #316's Gate 2, out of scope there because that issue's task file excludes recording the ways a criterion could fail. Parent: #183.
