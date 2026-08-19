# Judgement — #258 Gate 2, run 4

**Still INCOMPLETE, and by the gate's own measure further from clean than run 3
was.** Six tests were added and nothing else changed. Four obligations improved.
The one obligation that had been strongly supported fell.

Base `a4abbf4` → head `5399afd`. Live calls: the diff grew, so nothing replayed.

## What the added tests were for

Run 3's thirteen prescriptions were triaged into four that were right about this
delivery (`dogfood-logs/258-gate2-run3/judgement.md`). All four asked for the
same thing — evidence built against a corpus containing the near misses, rather
than against the real corpus where every path is already correct. Six tests
close them:

- `test_collection_is_identical_with_and_without_the_root_task_file` and
  `test_the_tests_that_read_it_pass_when_it_is_absent` — one snapshot of the
  tree, the root task file the only thing that changes, two collections compared
  id by id.
- `test_a_path_outside_dogfood_logs_is_not_a_case` — plants a sibling directory,
  the corpus directory itself, and the repository root.
- `test_each_committed_file_yields_exactly_one_case` — cardinality plus
  membership plus no duplicates.
- `test_the_parse_test_enumerates_the_corpus_and_nothing_else` — pins the
  parametrize to the corpus, which is where the pre-#258 call site went wrong.
- `test_the_scan_covers_helper_modules_and_conftest_too` — the guard's scan
  covers helpers, not only `test_*.py`.

Both snapshot tests are discriminating by injection: reintroducing the root file
into the region-coverage case list fails the collection comparison, and making
the parse test read the root file again fails the absent-file run.

## What moved

```
Changes since a752f82c:
  moved:
    - A test asserts that parsing succeeds for every committed task file …
        test evidence: strongly supported -> partially supported
    - No test reads the task file at the repository root.
        test evidence: indeterminate -> partially supported
    - A test run reports no failures when no task file is present …
        test evidence: unsupported -> partially supported
    - No test's outcome or case list depends on the task file …
        test evidence: unsupported -> partially supported
```

Three genuine improvements, and one regression that no change in the diff can
explain — the source under review is byte-identical between the runs, and the
only edits are additional tests.

| | run 3 | run 4 |
|---|---|---|
| strongly supported | 1 | **0** |
| partially supported | 10 | 14 |
| unsupported | 2 | 0 |
| indeterminate | 1 | 0 |
| test evidence not required | 6 | 6 |
| recommended tests | 13 | 14 |
| obligations with `(no mapped test)` | 3 | **0** |

Two things improved that are worth naming: **every obligation now carries a
mapped test**, where three carried none, and **the omitted prescription did not
recur** — a fresh live call answered all fourteen criteria, so #275's
`NOT OBTAINED` path was not exercised this time. That is the first evidence
about frequency: the omission is not deterministic for this input.

## The regression is the finding

Obligation 1 is *"A test asserts that parsing succeeds for every committed task
file under `dogfood-logs/`."* It was **strongly supported** in run 3 on one
citation. In run 4, on strictly more evidence, it is **partially supported**, and
the prescription it now carries reads:

> **detects:** Parser silently skips one committed file by not including it in
> the parametrized corpus.

That test is in the diff. It is
`test_the_parse_test_enumerates_the_corpus_and_nothing_else`, which asserts the
parametrize's argvalues equal `committed_task_files()` — precisely a file
omitted from the parametrized corpus. The mapping cited it against obligations 6,
7 and 10, and not against obligation 1, whose prescription it satisfies.

So the same run: (a) lowered a rating while evidence only increased, (b)
prescribed a test that exists in the diff under review, and (c) mapped that test
to three other obligations. This is #225 — *"a rating falls as its evidence
improves, and the recommendation prescribes a test already in the strength call's
own mapped set"* — in a controlled instance, since the source diff is unchanged
between the two runs and the only variable is added tests. Queued as a comment
on #225.

## Disposition

**Gate 2 fails for the second assessable time.** #258 stays unmerged.

The addressable subset is now addressed: four prescriptions were acted on, all
four obligations moved up, and the two that had no mapped test have one. What
stands between this branch and a clean gate is no longer a list of missing
tests — it is fourteen prescriptions of which the run itself demonstrates at
least one is satisfied by code it is looking at. Continuing to write tests
against this target is chasing a number that moved backwards on a strictly
larger body of evidence.

Nothing here retracts the delivery. The issue's Acceptance is met and is now
asserted rather than argued: collection is identical with and without the root
task file, the affected tests pass with it absent, and 1,290 tests are green.
