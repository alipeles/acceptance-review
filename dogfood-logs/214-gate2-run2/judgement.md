# Judgement — #214 Gate 2, runs 1 and 2

Base `0923f77`; run 1 head `be4367d`, run 2 head `bb1f1ef`. The only difference
between the two heads is **three added tests** — no source change.

## Result

| | run 1 | run 2 |
|---|---|---|
| verdict | INCOMPLETE | INCOMPLETE |
| coverage gaps | 2 | 0 |
| weak test evidence | 2 | 4 |
| obligations flagged | 4 | 4 |
| **overlap between the two sets** | | **1 of 4** |

**Not clean. Gate 2 fails.**

## Run 1's four findings were all real, and all are addressed

Every one was a genuine hole in my own tests. None was a tool defect.

| finding | disposition |
|---|---|
| `byte-identical-inputs-...` — code evidence *unclear* | **Real.** I never wrote the test. The obligation was in my own mandate. Added over the real pipeline. |
| `completion-10-test-demand-byte-identical...` — code evidence *unclear* | **Real.** Same omission, test-demand side. |
| `declined-requirement-coverage-accounting` — partially supported | **Real.** My test used a bare marker, which any implementation credits — including one that re-judges the decline. It could not fail. Added a case whose requirement text reads like a real requirement. |
| `record-coverage-on-result-and-report` — partially supported | **Real.** I asserted the field and never that the report renders it. Recording a figure without rendering it is the same defect one level down. |

Run 2 confirms the fixes: `constraint-01/completion-02` and `constraint-07` both
moved **partially → strongly supported**, and both code-evidence gaps closed.

I also verified the determinism test discriminates rather than trusting that it
does: injecting a `uuid4()` into `derived_obligation_id` fails it, and reverting
passes it.

## Run 2's four findings are dominated by rating instability

7 of 21 obligations moved rating between the two runs. Two moved **up** — the
two I fixed. Four moved **down**, on a diff that only added tests:

```
completion-09   strongly supported -> partially supported
completion-10   strongly supported -> partially supported
constraint-09   strongly supported -> nominally supported
constraint-11   strongly supported -> unsupported   (no mapped test at all)
```

`constraint-11` is the decisive one. In run 1 it cited two mapped tests:

```
tests/benchmark/test_coverage.py::test_cli_and_benchmark_share_one_pipeline
tests/coverage/test_open_questions.py::test_no_open_questions_issues_no_model_call
```

Both still exist, neither was touched between the heads, and in run 2 the
obligation has **`(no mapped test)`**. The mapped set went from two to zero with
no change to the tests. That is a mapping failure, not a judgement about
evidence — and CLAUDE.md's rule that a verdict is only as trustworthy as the
mapping behind it applies to a negative verdict exactly as it does to a clean one.

**I read each recommendation before concluding this**, because #180's corrected
reading is that a falling rating is usually the judge finally noticing a real
hole, and that inference must not be skipped:

- **`constraint-09`** asks for a test using "a model client that would fail if
  consulted". `derive_verdict` takes no client parameter — it structurally
  cannot consult a model, and its signature already guarantees what the
  recommendation asks a test to demonstrate.
- **`completion-09`** asks for an assertion that "inspects the completion
  produced by `run_review`, not a direct helper call", with all three
  dispositions present. That is `test_the_verdict_is_derived_with_each_requirements_disposition_in_hand`,
  which the same run cites as evidence for the obligation it says is missing it.
- **`completion-10`** asks for input "rich enough to include a resolved open
  question and at least one declined requirement". The fixture has both:
  `task-01` is declined, `q-rounding` is resolved.
- **`constraint-11`** has no mapped test to reason about, per above.

So none of the four is a hole I can close by writing code. Three describe tests
that exist; one lost its mapping.

## Disposition

Run 1's findings: **addressed**, all four.

Run 2's findings: **attributed to tool defects** — rating instability (#180) and
mapping instability (#182) — with a drafted comment on #180 queued carrying the
`constraint-11` evidence, which is a cleaner reproduction than the corpus
currently holds: a mapped set collapsing from two tests to zero across an
additive diff, with both tests still present.

This is the same call as #153 and #235, on the same cause, and it is the human's
to make rather than mine.
