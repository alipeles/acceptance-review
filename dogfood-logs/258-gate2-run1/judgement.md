# Judgement — #258 Gate 2, run 1

Base `3aeb676`, head = working tree at `1e9ac67`. Command:

```
.venv/bin/acceptance check --task current-task.md --base 3aeb676 --mode record
```

## Result: BLOCKED — no report was produced

```
acceptance: model error: no recommendation for 2 of 13 weak obligation(s):
region-coverage-omits-missing-path, no-failures-without-root-task-file
```

Three runs — two `record`, one `replay` — byte-identical each time. **Gate 2 is
not clean, and cannot be assessed at all:** the run aborts before the report is
rendered, so there is no coverage classification, no open-question list, no
unrequested-change list and no verdict to judge. The only thing known about the
review is that 13 of 20 obligations were rated below `strongly_supported`.

This is a handled path, not a crash — `coverage/recommendations.py:183` raises
`SchemaValidationError` and `cli.py:786` prints it and exits 1.

## Diagnosis

Established from the recorded transcript
(`.acceptance/cache/transcripts/21e168cc…json`), not inferred from the message.

**It is not truncation.** The response parses as complete JSON, terminates
cleanly on `"}]}`, and used 2,236 completion tokens with no `max_tokens` in the
request.

**It is not the DR-164 call-size shed either**, which was the first hypothesis
and is wrong. The skipped obligations sit at positions **10 and 11 of 13**, and
positions 12 and 13 were answered. A response running out of room drops the
tail; this one stepped over two in the middle and carried on. All 13 ids were in
the request and both missing ids are present in the enum-constrained schema, so
the model could have named them.

**What the two have in common is that no test can close their gap.**

| obligation | why a test cannot establish it |
|---|---|
| `region-coverage-omits-missing-path` | `glob` resolves a literal final component through `exists()`, so it provides the property outright — verified by injection: deleting the `is_file()` filter leaves the test green. |
| `no-failures-without-root-task-file` | a property of a whole suite run, not assertable from inside one without invoking pytest recursively. |

`_Recommendation` (line 67) requires seven fields — `required_inputs`,
`expected_output`, `plausible_defect` and the rest — and has **no
representation for "this gap cannot be closed by a test."** The prompt instructs
*"Return one recommendation per criterion you are given."* The model's only
options were to invent a test or stay silent; it stayed silent, silence is
equally unrepresentable, and the run died.

The design already contains this exact judgement, scoped too narrowly.
`_weak_obligations` (line 81) excludes `CODE_ONLY` obligations, and its docstring
says why: *"Theirs is not a gap a test could close… Recommending one would
prescribe evidence that cannot exist, which is worse than recommending nothing."*
That is right, and it applies equally to these two — which are ordinary
`boundary` and `functional` obligations, not scope exclusions.

**Partitioning would not fix this.** At a partition of five, the same two
obligations remain unanswerable and the same error fires on a smaller call.

## Disposition

Tool defect. Drafted as a child of #185 in `docs/DEFERRED.md`. Per the human's
decision, it is fixed as **its own issue first**, and #258's Gate 2 is re-run
against the fixed tool rather than being worked around here.

**No finding here is attributable to #258's own change**, which is complete: both
call sites repointed, 1,199 tests pass, `ruff check`/`format` clean on the five
touched files, the issue's acceptance grep returns nothing, and the suite passes
with `current-task.md` deleted at the identical test count.

## Not to be forgotten when the gate is re-run

The blocked run says nothing about the other 13 weak obligations. When the report
finally renders it may well be unclean for ordinary reasons, and that will be a
second, separate assessment — not a formality.
