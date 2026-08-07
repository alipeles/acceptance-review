# Judgement — #218 Gate 2 run 1

`6ae97fd` → `c61e3cf`. **Not clean.** INCOMPLETE, 5 weak obligations.

The change is visibly working on itself: 5 inline `recommended test:` lines, 0
standalone `Recommended tests:` sections. The tool dogfooded its own fix.

## Acted on

**Recommendation 11 was the substantive one** — *"the summary counts weak
obligations from the recommendation list instead of from the obligations
input, so missing recommendations reduce the weak count"*. That would be the
#214 blindness one axis over: answering less scoring better.

It is not present — `derive_verdict` (`verdict.py:76-84`) builds the count from
`obligations`, and never receives the recommendations at all. But nothing pinned
it, and a later refactor threading them in would look harmless. Test added.

## Attributed

- **`typed-schemas-are-pydantic-models`** — `unsupported / no mapped test`.
  Verbatim the #148 case that blocked #217's Gate 2, in a second consecutive PR.
  Evidence attached to #148.
- **`tests-avoid-live-model-calls`** — a standing repo invariant rather than
  this change's behaviour. Same shape.

## Deferred as tautology-adjacent

Recommendations for `no-standalone-recommendations-section` and
`closing-line-points-at-retrieval-command` both amount to asserting the code
says what it says. The first turned out to have a fair core and was addressed in
run 3; see that judgement.
