# Judgement — #248 Gate 2, run 2 (NOT CLEAN — escalated)

Command: `.venv/bin/acceptance check --task current-task.md --base 4619e78 --head 737c386 --mode record`
Base `4619e78`, head `737c386`. Run 1's inputs are in `dogfood-logs/248-gate2-run1/`.

**Verdict: INCOMPLETE, 13 obligations with non-discriminating test evidence** —
up from 3 in run 1, after two tests were ADDED and nothing removed.

## Run 1 → run 2: the rating fell as the evidence improved

Run 1 raised three findings. One was real and was fixed: task-01's
recommendation asked for a repeated-obligation response shape other than the
single observed one. It was right — every echo test used one obligation emitted
twice, so `more_obligations[1:]` was only ever exercised empty, and a guard
collapsing the WHOLE remainder passed all 16 tests. Verified by injection, then
covered by `test_an_echo_surrounded_by_genuine_obligations_collapses_only_the_echo`
and `test_two_requirements_each_echoing_are_both_collapsed`.

Run 2's own diff section reports the result:

```
closed:  1 obligation   unsupported -> strongly supported
moved:  11 obligations  strongly supported -> partially supported
```

The eleven include obligations whose tests this change never touched — "Tests
issue no live model calls", "Two runs over byte-identical task text produce
byte-identical review state", and a scope-exclusion preservation invariant.
Adding two tests cannot have weakened them.

This is **#225** ("a rating falls as its evidence improves") and **#180**
(rating instability across runs), reproduced on a small diff with a committed
before/after pair.

## Two recommendations are factually wrong about the code

1. `test-repeat-head-yields-one`: *"the existing test case uses a non-identical
   repeat."* False. `_echo_response()` builds `[_obligation(*USD),
   _obligation(*USD)]` — two separate dicts with identical contents — and
   `test_an_echoed_required_obligation_yields_one_obligation` asserts on exactly
   that shape.

2. `test-later-repeat-kept` and `dedupe-repeated-obligation-response`: both ask
   for a test detecting that the implementation *"deduplicates repeated
   obligations only when the repeated item is later in the list, not at the
   head"*. That is the inverse of `constraint-05`, which this same report rates
   `strongly supported` — the tool is prescribing a test for the negation of a
   requirement it has already judged satisfied.

3. `test-no-repeat-suffix` asks for a test that no suffix leaks into "an
   internal, unobserved copy". Unobservable by construction.

## Why this was escalated rather than fixed

`CLAUDE.md` *Working agreement* §3: failed the same way twice, and a third
attempt would be a different approach rather than a fix. Writing further tests
to move these ratings would be chasing a judge that is demonstrably unstable and
in places factually wrong about the code it is reading — which is the definition
of editing to change what the review says.

The evidence that the change is correct is independent of the tool's rating and
is recorded in the commits: four defect injections, each failing the tests that
claim the behaviour.

| injection | result |
|---|---|
| guard removed entirely | 7 tests fail |
| description-only comparison (#248 as originally filed) | 4 of 5 parametrised cases fail |
| dedupe anywhere in the remainder | position-0 test fails |
| collapse the whole remainder | surrounded-echo test fails |

## Separable changes — correct findings, no action taken

`docs/DEFERRED.md` and `session-state.md` are flagged `separable`. That is
accurate: both are process bookkeeping this repo requires on every branch, and
neither is demanded by the mandate. They will be flagged on every dogfood run
that follows the working agreement, which is worth a decision of its own.

## Status

Escalated to the human. Gate 2 is not clean and was not made clean.
