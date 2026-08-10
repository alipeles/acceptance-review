# Judgement — #144 Gate 2, run 5

`check --base 9724df4 --head 1affd3a`. **Still NOT CLEAN**, and this is the
cleanest the run gets without work that is not #144's.

| | run 3 | run 4 | run 5 |
|---|---|---|---|
| derived → linked | 24 → 21 | 24 → 19 | 24 → **19** |
| merges | 3 | 5 | 5 |
| contradictions | 1 (7 obligations) | 0 | **0** |
| strongly supported | 15 | 14 | **15** |
| nominally / partially | 1 / 3 | 1 / 2 | **1 / 0** |
| unsupported | 4 | 4 | **4** |
| recommended tests | ? | 5 | **4** |

`typed-schemas-pydantic-models` cleared — it is the one blocker this task owned
and it is closed. Every remaining weak obligation is one of the four Task-prose
ones, and the only non-`addressed` coverage is the prompt-implemented rule.

## What remains, and why none of it is this task's

**Four Task-prose obligations** — `duplication-per-requirement`,
`later-stages-per-obligation`, `duplication-is-ordinary-restatement`,
`duplication-not-input-fault`. Identical across all five runs. The model reads
the mandate's problem statement as a requirement to preserve, and the
recommendations ask for tests that the tool remains slow and duplicative.
**#212**, commented with this evidence.

**`reason-clause-counts-as-same-requirement` — code partially addressed.** Test
evidence is strongly supported; the coverage axis is right that the code only
partly responds, because the rule is implemented as prompt text rather than as
code. Nothing in `linking.py` decides that a reason clause is not a second
requirement — it asks the model to. Worth stating rather than arguing with: an
obligation whose implementation is a paragraph of prompt genuinely is only
partly code, and that is a property of the whole stage, not a gap in this change.

## The decomposition finding, now proven rather than suspected

`constraint-06` and `completion-04` merge, and they should not. The evidence is
exact:

| | text |
|---|---|
| `completion-04` in the task file | "**A test asserts that** a requirement followed by a clause giving its reason yields one obligation rather than two." |
| what derivation produced from it | "A requirement followed by a clause giving its reason yields one obligation rather than two." |

Derivation dropped "A test asserts that". The linking stage was handed two
behaviour statements and judged them identical, which is correct for what it
saw — its recorded reason says exactly that: *"they are the same requirement
stated in different words."*

The linking prompt already carries the negative example for this case. It cannot
fire, because it keys on text that no longer exists by the time linking runs.
Adding a second example would be equally unreachable and would make the prompt
appear to cover a case it cannot see.

Filed as a child of **#181**. It is distinct from #212: that one is narrative
context becoming a requirement; this is one section yielding two different
obligation shapes depending on the run, with the test framing silently dropped.
