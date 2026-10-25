# Task

The defect-to-test pair judgement, "if the delivered code had this defect,
would this test fail?", is decided by Jev first, and by Claude Sonnet 5.5 only
for the pairs Jev is unsure of. This replaces today's judge, which asks the
default model about up to 40 pairs in one call.

Jev is asked about one pair at a time, with targeted context: the function
holding the defect with the defect's lines marked, the test with its file's
imports and the helpers it uses, and the project code the test calls.
`docs/experiments/jev/m52/targeted_prompt.py` is the experiment's version of
that context. Jev's probability that the test fails decides the pair on its own
at 0.34 or more (the test fails) and at 0.24 or less (the test survives).

A pair whose probability falls between those two goes to Sonnet, one pair per
call, with the requirement text, the original code and the defect's
description. Sonnet answers yes or no in a schema-constrained response; no
token probability is read. When Sonnet gives no usable answer, Jev's
probability decides the pair at 0.5.

Jev is a provider in `llm.py`, recorded and replayed like any other. Its
probability is recorded with its call, so replaying a recorded review
reproduces every decision with no live call, and two recorded runs over the
same input produce byte-identical review state.

A verdict Jev decides keeps the static evidence tier and records that it
carries no reasoning.

## Scope exclusions
- Re-fitting the 0.34 and 0.24 cut-offs.
- Changing how defects are enumerated, or which pairs reach the judge.
