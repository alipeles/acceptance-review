# Judgement — #144 Gate 2, run 2

`check --base 9724df4 --head 249d5cb`, after the linking prompt gained an explicit
test for sameness. **Still NOT CLEAN.**

| | run 1 | run 2 |
|---|---|---|
| derived | 24 | 24 |
| linked | 18 | **17** |
| strongly supported | 14 | 12 |
| nominally supported | 0 | 1 |
| unsupported | 4 | 4 |
| merges | 5 | 7 |

Derivation is byte-stable across a linking-prompt change, which is the two-stage
separation working: only stage 2's request key moved.

## The named over-merge is fixed

`constraint-04` (*the links are typed fields*) merged with `constraint-10`
(*typed schemas are pydantic models*) in run 1. In run 2 `constraint-04` pairs
only with `completion-06`, its own acceptance criterion, and `constraint-10`
stands alone as obligation 12.

Un-merging it exposed a real gap that the over-merge had been hiding:
`constraint-10` is now **nominally supported**, because no test asserts the
schemas are pydantic models. That is the tool being right — the requirement was
never demonstrated, and merging it into a well-tested neighbour had been
laundering that.

## A new mis-link, of the same class

`completion-04` — *"a test asserts that a requirement followed by a clause giving
its reason yields one obligation rather than two"* — is now attached to
obligation 1, which is *"a task file stating one requirement in two sections
yields one obligation linked to both requirements"*.

Its actual partner is `constraint-06`, the reason-clause rule, which stands alone
as obligation 11 with the matching test
(`test_a_requirement_and_its_reason_clause_are_one_requirement`) as its evidence.

This fails **both** halves of the criterion just added to the prompt. The two
conditions differ — one is a requirement stated in two sections, the other a
requirement followed by its reason — and the demonstrating tests are different
and both exist in the tree. So this is not a borderline judgement the criterion
failed to reach; it is a link the criterion forbids.

**Second over-merge in two runs.** The first lumped a behavior with its
implementation technology; this one attaches an acceptance criterion to the wrong
rule while the right rule sits unmerged beside it. Worth treating as a pattern
rather than a third prompt edit: the prompt hands the model every obligation and
asks for pairs, which invites nearest-neighbour attachment among several
plausible partners.

## Remaining blockers

1. **4 Task-prose obligations** (`duplication-per-requirement`,
   `later-stages-per-obligation`, `duplication-is-ordinary-restatement`,
   `duplication-not-input-fault`). Attributed to **#212** — the model reads
   narrative context as requirement. Commented there with this run's evidence.
   Explicitly **not** a task-file wording problem: a mandate's opening is
   supposed to describe the problem being fixed.
2. **`constraint-10` nominally supported** — genuine, and addressable here: no
   test asserts the response schemas are pydantic models.
3. **The `completion-04` mis-link** above.
