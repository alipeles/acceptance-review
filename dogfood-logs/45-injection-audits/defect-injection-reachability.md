# Which defects defect injection cannot reach, and whether tests can

Injection answers one question: *if this defect were present, would any of the
builder's tests fail?* It answers it by making the defect present and running
the tests. That method has classes of defect it cannot touch, and they are not
the same as the classes tests cannot cover. This document separates the two,
because conflating them is how a review reports "your tests do not catch this"
about a defect that was never injected.

Three kinds of limit, and only the first is permanent.

---

## 1. Injection is impossible in principle

### 1a. The defect already holds in the delivered code

**Why injection cannot reach it.** Injection works by making a false thing true.
If the thing is already true, there is no edit that makes it truer. The stage is
handed an unsatisfiable instruction and produces something else — on #45's own
review that was usually an edit that *removed* the defect, which then reads as a
kill when tests assert the current behaviour.

**Can tests cover it?** Yes, and this is the case where injection is not merely
unnecessary but actively worse than doing nothing. The defect is present in the
code right now. If the suite is green, the suite demonstrably does not catch it
— no injection required, and that is a stronger statement than a mutation
experiment could make.

**What the review should do.** Recognise the case and report it directly: this
criterion has a defect that is present and unnoticed. Today the review instead
spends a descriptor call, injects something unrelated, and reports whatever
happens.

**Seen at #45's Gate 2.** `execution-tier-disabled-by-default` ("the tier is off
by default, so the code-reading judgement still runs first") is a true statement
about the delivered code. So is `execution-disabled-by-default` and
`prechange-run-only-when-execute-flag-set`.

### 1b. The defect is about content nothing executes and nothing reads

A defect in an internal comment, or in a docstring no test asserts on.

**Why injection cannot reach it.** The edit applies, the file still parses,
nothing observable changes. Every test passes, and the result is recorded as a
survival — a finding that the tests do not discriminate.

**Can tests cover it?** No. Nothing could fail on it. **Test coverage is not
relevant to this defect**, and the honest verdict is that the criterion is not
testable rather than that the tests are weak.

This is the one class where the right answer is neither injection nor the static
judge, but a statement that the criterion is not evidenceable by test at all.
`RequiredEvidence` already carries that idea for obligations; nothing carries it
for defects.

### 1c. The defect is about a property of the run rather than of an output

"Two runs over the same input are not byte-identical", "the review costs too
much", "the stage issues one call per pair". A mutation makes one run behave
differently; it cannot make a *relationship between runs* false.

**Can tests cover it?** Sometimes, and this repo has such tests —
`test_determinism.py` compares two runs. Where such a test exists, injection is
simply the wrong instrument, not a verdict on the tests.

---

## 2. Injection is impossible in our current implementation

These are limits of the descriptor format, not of the method. They should be
recorded as *not decided* and handed to the static judge, which is what happens
today.

### 2a. The defect needs coordinated edits in more than one place

DR-171 (the mutation-targeting decision record) Decision 2 fixes the descriptor
as **one contiguous span in one file**. A defect like "the setting is read in
three places and one of them ignores it" cannot be expressed that way.

**Can tests cover it?** Yes, ordinarily. This is purely our restriction, and
Decision 2 records that a multi-span form was left open.

### 2b. The edit exceeds the size bound

Twelve lines, by configuration. A defect whose smallest faithful expression is
larger is refused.

**Can tests cover it?** Yes. The bound exists so that a reader can judge whether
the mutant is the named defect, not because a larger edit is meaningless.

### 2c. The file has no parser we can validate with

Validity checks that a mutated file still parses *when we have a parser for it*.
For a format we cannot parse, the check is skipped rather than failed — so this
is currently a soundness gap rather than a refusal: we may inject something
malformed and read the resulting failures as kills.

**Can tests cover it?** Yes, and this is the class DR-171 Decision 3's 2026-09-14
revision was written to admit — a requirement stated in prose can be broken in
prose, and the tests that read that prose catch it.

---

## 3. Not a limit at all, despite appearances

### 3a. Absence defects

`not_wired` (the logic exists but nothing calls it), `missing_case` (an input
falls through unhandled), `documented_not_implemented`.

DR-171's "What injection cannot decide" section expected these to be
unreachable, on the reasoning that the implicated lines are where behaviour
*should* be and is not, so there is no span to replace.

**That is wrong in the ordinary case, and #45's Gate 2 measured it.** All 19
`not_wired` and `missing_case` defects named at least one changed region. The
reason is that the delivered code usually does the right thing: "nothing calls
it" is injected by *deleting the call*, which is an ordinary span replacement.

The expectation holds only in the sub-case that is really 1a — where the code
genuinely already omits the behaviour, so the defect is already true.

---

## What this means for the review

Only 1a, 1b and 1c are permanent. Everything in section 2 is a restriction we
chose and could lift, and section 3 was a mistaken expectation.

The distinction that matters for what the review reports:

- **1a** should produce a finding, not an injection. The defect is present.
- **1b** should mark the criterion as not evidenceable by test, not as weakly
  tested.
- **1c, 2a, 2b, 2c** should fall back to the static judge, which is what the
  `not_mutable` outcome already does.

Today all of them land on `not_mutable` and are handed to the static judge
alike. That is safe for everything except 1a and 1b, where it is wrong in
opposite directions: 1a understates a real defect, and 1b reports weak tests for
a criterion no test could ever bear on.
