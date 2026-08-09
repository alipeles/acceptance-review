# Judgement — #144 Gate 2, run 4

`check --base 9724df4 --head bb2af16`, after interleaved pair ordering and
reason-before-verdict. **Still NOT CLEAN.**

| | run 1 | run 2 | run 3 | run 4 |
|---|---|---|---|---|
| derived → linked | 24 → 18 | 24 → 17 | 24 → 21 | 24 → **19** |
| merges | 5 | 7 | 3 | **5** |
| contradictions | — | — | 1 (7 obligations) | **0** |
| strongly supported | 14 | 12 | 15 | 14 |
| unsupported | 4 | 4 | 4 | 4 |
| recommended tests | 4 | ? | ? | 5 |

The linking mechanism is now behaving: no contradiction, five defensible merges,
every reason arguing for its verdict. Runs 1 and 2 reached similar merge counts
by over-merging; this one reaches it by agreeing with itself.

## Blockers

**1. The four Task-prose obligations** — `duplication-per-requirement`,
`later-stages-per-obligation`, `duplication-is-ordinary-restatement`,
`duplication-not-input-fault`. Unchanged across all four runs. Attributed to
**#212**; the model reads narrative context as requirement. Not a task-file
wording problem and not #144's to fix.

**2. `reason-clause-counts-as-same-requirement` — code partially addressed.**
Test evidence is strongly supported; the coverage axis says the code only partly
responds. Fair: the rule lives in a prompt, not in code. Nothing in
`linking.py` implements "a reason clause is not a second requirement" — it asks
the model to apply it. An obligation whose implementation is a paragraph of
prompt is genuinely only partly code.

**3. `typed-schemas-pydantic-models` — nominally supported.** Real. No test
asserts the response schemas are pydantic models. Addressable here.

## The finding that outlasts this run

`constraint-06` and `completion-04` merged — *"a requirement followed by a
clause giving its reason yields one obligation"* and *"**a test asserts that** a
requirement followed by a clause giving its reason yields one obligation"*.

By the criterion we just put in the prompt, and flipped the example for, those
are **different** requirements: code can already satisfy the rule with nobody
having written the test. They merged anyway, and the prompt is not at fault —
derivation rendered `completion-04` as a behaviour obligation, not as "add a
test", so the linking stage never saw the distinction it was told to make.

The same task-file grammar produces both framings. On the invoice fixture,
Completion expectations become *"Add a test that asserts…"* and correctly do not
merge. On this repo's task file they become behaviour statements and do merge.

So the merges on this task file are of a shape we have agreed should not merge,
and the linking stage cannot tell, because the distinction was erased upstream.
That is a decomposition defect (#212 / #181 family), it is the load-bearing
cause of the remaining instability, and no linking-prompt wording reaches it.
