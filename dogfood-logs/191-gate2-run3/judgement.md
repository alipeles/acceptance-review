# #191 Gate 2, round 3 — judgement

**Not clean.** INCOMPLETE: two obligations with non-discriminating test evidence.
No open questions. Unrequested changes down to two `separable` documentation
items (the DR-180 update and the experiment README) — both required by the
*issue's* Acceptance rather than by the task file, which is the distinction
CLAUDE.md draws deliberately, so no action.

Neither remaining finding is a gap in the delivered work. One is a stable false
recommendation; the other is a mapping failure.

## The three rounds side by side

Rounds 2 and 3 each differ from the previous one by **added tests only**.

| obligation | r1 | r2 | r3 |
|---|---|---|---|
| `test-verdict-call-carries-configured-bounded-obligations` | flagged | flagged | flagged |
| `bounded-obligations-per-verdict-call` | flagged | clear | clear |
| `test-obligation-count-reaches-recorded-request` | flagged | clear | clear |
| `tool-identifies-no-fewer-defects` | flagged | clear | clear |
| `test-editing-mapped-test-leaves-other-obligation-defects-unchanged` | strong | **flagged (real)** | clear |
| `test-adding-mapped-test-leaves-obligation-defects-unchanged` | strong | flagged | **flagged (unsupported)** |
| `test-review-pipeline-uses-separated-defect-verdict-steps` | strong | flagged | clear |

Five of the seven changed rating across rounds. Four of the five moved without
any change to their own evidence.

## Finding 1 — flagged in all three rounds, and wrong in all three

`test-verdict-call-carries-configured-bounded-obligations`, `partially
supported`. The run cites **both** relevant tests, including
`test_the_verdict_bound_counts_criteria_and_not_defects`, which was written in
round 2 specifically to satisfy this recommendation and does everything its
`inputs` now asks for: more criteria than the batch size, one criterion carrying
five defects so defect count and criterion count diverge, and an assertion over
the verdict-call request payload rather than the final review.

Its `detects` clause has also been incoherent in two of three rounds:

> The verdict request is built from the wrong batch dimension, so the number of
> defects carried per call is bounded by the number of obligations instead of
> the configured defect-verdict batch size.

That inverts the two dimensions. The mandate bounds *obligations per verdict
call* (`constraint-03`), which is what `defect_verdict_batch_size` does; there is
no sense in which defects being "bounded by the number of obligations" is the
defect. Round 1's statement of the same finding was coherent, so the wording
degraded while the flag persisted.

**Disposition:** tool defect. Unlike the round-2 findings this one is *stable* —
three for three — so it is not the instability. It is a recommendation making a
checkable false claim about the code, which is the #225 family, but the stable
variety. Queued.

## Finding 2 — the mapping dropped a test it had already found

`test-adding-mapped-test-leaves-obligation-defects-unchanged`: **`unsupported`,
"(no mapped test)"** — while the *code* evidence for the same obligation cites
`tests/test_discrimination_wiring.py`, the file that contains it.

In round 1 this obligation was `strongly supported`, citing
`test_adding_a_test_leaves_the_obligations_enumeration_request_unchanged` — a
test whose name is very nearly the obligation's own text. Nothing about that
test has changed since.

**Disposition:** tool defect, the #245/#173 mapping family, and a cleaner
instance than most: the mapper found the test in round 1, and by round 3 reports
the obligation has no mapped test at all while still pointing at its file.
Queued.

## What the three rounds establish

The delivered work is not what the gate is failing on. Every finding that named
a real gap — four in round 1, one in round 2 — was fixed, and none has recurred.
What remains is one stable false recommendation and one mapping dropout.

The more important result is the movement itself, and it is **post-change**.
#191 stabilises which defects get *named*; five of seven obligations still moved
rating across rounds that added only tests. That is the verdict half, which #191
does not claim to fix and #192 owns.
