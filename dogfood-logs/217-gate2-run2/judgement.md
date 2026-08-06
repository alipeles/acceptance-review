# Judgement — #217 Gate 2 run 2

`6ae97fd` → `007966f`. **Not clean.** INCOMPLETE: 7 obligations with
non-discriminating test evidence. No obligation unaddressed — run 1's true
positive is resolved.

Mandate coverage 37 of 41. The four declines are scope exclusions pointing at
#216/#214/#209 plus the `Implementation` section marker, each with a correct
reason. Those are right outcomes, not gaps.

All unrequested changes are now **[in_service]** — run 1's `separable` flag on
the `supplied_ids.py` union walk cleared once the mandate named it.

## Acted on

Two recommendations were genuine gaps and are closed in `6c06517`:

- **literal-tag dispatch** was asserted nowhere. Without it a `no_obligation`
  could be read as a `yielded` whose ids happened to be absent — the
  contradiction rebuilt inside the parser.
- the **empty** open-question payload was untested at the schema boundary. The
  existing test covered a *named but unproduced* id, which is the reconciliation
  path, not the schema one.

## Not acted on

Recommendations 3, 4 and 5 restate guarantees that already have direct tests
(`test_a_response_that_never_mentions_a_requirement_is_rejected`, the schema
assertions, and the existing no-live-call guards). Carried to run 3 to see
whether they persist.
