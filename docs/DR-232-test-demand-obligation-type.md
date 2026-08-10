# DR-232 — a demand for a test is its own obligation type

**Issue:** #232 (with #219, #230 in the same change)
**Status:** resolved
**Date:** 2026-08-09

## The problem

A mandate saying *"a test asserts that X"* demands something different from one
saying *"X"*. Code that already does X, with nobody having written the test,
satisfies the second and violates the first. They are separate pieces of work.

Decomposition could not hold that difference. `ObligationType` had nine values
and none of them meant "this obligation demands a test", so the distinction
lived only in the `description` — free text, which every later stage would have
had to recover by reading English. It was not recovered. On this repo's own task
file the framing was dropped for all five Completion expectations (Gate 1 run 1)
and #144's linking then merged each with its Constraint twin, because by that
point the two obligations genuinely were the same statement.

Worse, the loss was **unstable within a single call**: Gate 1 run 4 kept the
framing on two of five identically-shaped bullets and dropped it on three. A
review could therefore report a behavior delivered while the demanded test was
never written — the exact gap this product exists to catch.

## What was tried first, and why it failed

**Attempt 1 — instruct derivation to keep the framing.** It worked on the
Completion expectations (5/5 by run 5) and immediately caused the inverse
defect: told emphatically that requirements of that shape keep their framing,
derivation began *supplying* it. `constraint-05` — "A requirement disposed of
without an obligation carries a reason that does not itself state a property the
change must preserve" — derived as *"A test asserts that a requirement disposed
of…"*. The Constraint and its Completion twin became one statement again, and
linking merged them correctly. Same loss, opposite route.

**Attempt 2 — state the converse explicitly, with an example and a test.** The
control fixture passed; this repo's task file still framed three of eight
Constraints (run 7). Notably `constraint-07` contains no test vocabulary at all
and was framed anyway, so "the subject matter confused it" does not explain it.

**Attempt 3 was not made.** Two failures of the same shape is the *Working
agreement* §3 interrupt, and the third attempt would have been a different
approach rather than a fix.

Separately, the linking prompt's own criteria pointed the wrong way on this
pair. Criterion 2 asks whether *the same set of tests would demonstrate both* —
and the test that asserts X **is** the evidence for X, so it reads true. The
negative example ("a behavior and a requirement to TEST that behavior") was
being weighed against a criterion that contradicted it.

## The decision

Add **`test_demand`** to `ObligationType`, and derive the distinction from the
type rather than from wording.

1. **`ObligationType.TEST_DEMAND`**, and spec §7.3 gains it as a tenth type. The
   spec is the product's source of truth, so this is a spec change, not only an
   enum addition.
2. **The derivation prompt selects the type from the requirement text alone** —
   `test_demand` when *this* requirement asks for a test, never because another
   bullet elsewhere asks for a test of the same behavior.
3. **Linking never asks about a mixed pair.** `_can_state_one_requirement`
   returns false when exactly one side is `test_demand`, and `_pairs` filters on
   it, so the pair is settled in code and never batched.

## Why skip the pair rather than override the answer

A question with only one admissible answer is not a question, and asking it
costs twice. It spends a slot in a pair batch; and a wrong `true` lands inside a
transitive component, where #144's clique rule then suppresses **every other
merge in that component**. Both Gate 1 run 2 and run 5 lost real merges exactly
that way, and run 2's suppression also made a non-merger assertion pass for the
wrong reason — it would have kept passing with the fix reverted.

The saving is visible in the corpus: the invoice fixture needed two linking
sweeps before this change and needs one after.

## Cost accepted

`ObligationType` is persisted on every stored `Obligation`. Adding a value is
backward-compatible for reading existing state, but state written after it
cannot be read by anything pinned to the old set. Nothing outside this repo
consumes it, so the cost is confined to re-recording the corpus — which this
change was already paying for.

## Measured

On this repo's own task file, run 7 (prompt-only) against run 8 (typed):

| | run 7 | run 8 |
|---|---|---|
| Constraints given invented test framing | 3 of 8 | **0 of 8** |
| Completion expectations carrying the demand | 5 of 5, in text | **5 of 5, typed** |
| behaviour ↔ test-of-behaviour merges | 3 | **0** |

## Consequence for tests

The prompt tests asserted `"test" in description.lower()` — a heuristic over
free text, which is the shape the markdown-never-as-interchange invariant exists
to forbid, and which cannot tell a test demand from a behavior obligation that
merely mentions testing. They now assert on the type. The structural non-merge
is unit-tested in `tests/requirement/test_linking.py` against a model double
that answers `true`, so a later change reinstating the question would still have
to keep the obligations apart.

## Related

#232, #219, #230, #144 (`DR-144`), #204 (`DR-204`), #205 (typing as its own
pass — compatible; it inherits the taxonomy rather than defining it), #148
(whether an obligation needs test evidence at all — a `test_demand` obligation
is the case where the evidence *is* the test, which that issue will want).
