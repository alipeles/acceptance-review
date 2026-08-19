# Judgement — #269 Gate 2, run 6 (final)

`check --task current-task.md --base a4abbf4 --head 8a3c20b`.

**Not clean**, and for one reason only: the rating collapse filed on #251.

| rating | run 4 | run 5 | run 6 |
|---|---|---|---|
| strongly supported | **37** | 4 | 4 |
| partially supported | 3 | 48 | 47 |
| unsupported | 4 | 0 | 1 |
| not required | 8 | 8 | 8 |

Run 6 adds one test to run 5 and is indistinguishable from it. The report has not
recovered from the collapse that run 5 introduced, which is the expected
behaviour of the defect: once an obligation has been re-judged downward it stays
there, and nothing in this branch can lift it.

## What run 6 was for: `completion-10`

The one finding from run 4 that was a genuine gap in my work rather than a tool
artefact, and the last one outstanding.

| | run 4 | run 6 |
|---|---|---|
| rating | **unsupported**, `(no mapped test)` | **partially supported** |
| cites | — | `test_carry_forward_re_asks_every_requirement_the_corpus_actually_changed` |

The new test parametrizes over all six consecutive pairs of the seven runs in
`tests/fixtures/decompose-stability/` and asserts the carry plan over each: a
requirement whose text moved is re-asked, one whose text is byte-identical is
carried, one that disappeared is reported. That is the precise mechanism by which
carry-forward could destroy the corpus's recorded movements — carry a requirement
whose text changed and run N's decomposition is frozen in place.

**Injection-verified.** Switching identity from requirement *text* to requirement
*id* — the plausible wrong implementation, since `section-ordinal` ids look stable
— fails all six pairs. An earlier injection that forced a fallback candidate
failed only two, because the carry-key check caught the rest; the id version is
the one that actually models the defect, and it is the one recorded.

The residual recommendation asks for *"the real corpus with at least one pair of
consecutive runs where the task file genuinely changes and at least one
requirement remains unchanged"* — which is what the test does, six times over —
and detects *"the implementation preserves the recorded movements for the tested
corpus but would not for other edits"*, which asks for generalisation beyond the
corpus the obligation itself names. I do not think there is more to do here.

## Standing assessment

Every finding across six runs has now been either fixed or attributed:

| finding | run | disposition |
|---|---|---|
| `schema-change-blocks-carry-forward` unsupported | 1 | fixed — two tests, both injections confirmed |
| `revised-requirement-records-revision-reason` unsupported | 2 | **defect, not a missing test** — fixed by `_stamp_revisions` |
| whole-review abort | 3 | tool defect — fixed independently by #279 |
| nine evidence gaps | 4 | fixed |
| ratings collapse 37 → 4 | 5 | tool defect — filed on #251 |
| `completion-10` unsupported | 4 | fixed, this run |

**1223 tests pass**, ruff check and format clean.

## Why this lands anyway

On the human's decision, and on the precedent #271 set explicitly — *"Gate 2 is
not clean and this lands anyway"* — with the condition that the only outstanding
findings be attributable to a tool defect rather than to the delivery. That
condition is now met: `completion-10` was the last finding attributable to this
work, and it is closed.

The honest statement of what is unknown: with 4 of 60 obligations rated strongly
supported, this report cannot distinguish a good delivery from a bad one. The
last reading that could is run 4's, which showed every obligation addressed and
15 evidence gaps, nine of which are now closed and one of which was
`completion-10`. That is the evidence this merge rests on, not run 6.
