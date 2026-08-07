# Judgement — #218 Gate 2 run 4

`1c71535` → `e52a57c`, the first run after rebasing onto #217.

**The tool reports NO-MATERIAL-GAPS. Do not read that as a clean gate.**

## What the report says

- 14 obligations, all `addressed`, all `strongly supported`
- 0 open questions, 0 recommended tests
- 5 unrequested changes, all `[in_service]`
- mandate coverage 25 of 30, the 5 declines being 4 scope exclusions (#219) and
  the `Implementation` marker

Mapping is not half-blind (DR-164): **14 of 14** obligations carry mapped tests,
33 links total, measured from the persisted review rather than the cache.

## Why it is not comparable to run 3

The task file is **byte-identical** between runs 3 and 4, and **12 of the 14
obligations were reworded**. Only 2 survive verbatim.

The cause is legitimate and identifiable: #217 changed `_Decomposition`'s
response schema, `request_key` hashes the response schema, so the decompose
transcript was invalidated and the obligation set was re-derived by a fresh call.
In #220's terms this is case 2 — changed, and its inputs moved.

But it means the 3-weak → 0-weak movement is **not** evidence that the added
tests closed anything. Different obligations were judged. A stable count
concealed a re-split, which is the failure mode the session notes already warn
about.

## The false positive

```
12. Represent typed schemas as pydantic models.
       code evidence: addressed
         (no corresponding change)
       test evidence: strongly supported  [tier: static]
         12.1  tests/coverage/test_recommendations.py::test_recommendation_round_trips_through_persistence
         12.2  tests/test_verdict.py::test_completion_result_round_trips_through_persistence
```

Both cited tests round-trip a model through persistence. **They would pass if
the schemas were dataclasses with the same serialisation.** They do not
discriminate the obligation. And `code evidence: addressed` is asserted with
`(no corresponding change)` — a claim with no citation behind it.

This is the same #148 obligation that read `unsupported / (no mapped test)` in
runs 1-3. Nothing in the code changed that could make it testable.

**This is worse than the blocking behaviour #148 has produced so far.** Until
now #148 caused honest `unsupported` readings that *blocked* a gate. Here it
manufactured `strongly supported` from non-discriminating evidence and
*unblocked* one. A defect that can turn a gate green is a different severity of
problem from one that turns it red.

Obligation 7 has the same `(no corresponding change)` shape and is **fine** — a
preservation obligation, correctly `addressed` with no diff refs per #133, with
two genuinely discriminating tests behind it. The shape alone is not the tell.

## Disposition

**Attributed to #148**, with this run attached as evidence of the escalation.
Not addressed here: no test can evidence obligation 12, which is the whole point
of #148.

**The work itself is complete.** Every obligation #218 actually set out to
deliver is implemented and genuinely tested. The unreliability is in the tool's
judgement of one obligation, not in the change.

**Recommendation: do not treat this as a clean Gate 2 in the PR.** Record it as a
pass with a known false positive, so the next reader is not told the tool
verified something it cannot verify.
