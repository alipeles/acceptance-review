# Judgement — #258 Gate 2, run 3

**A report rendered for the first time. It is INCOMPLETE — not clean.**

Base `a4abbf4` → head `a752f82`, after rebasing onto #279 (the fix for #275).
The gate can now be *assessed*, which is what changed; the assessment is
negative.

## Read this before reading the ratings: no live call was made

`--mode record` was used, but **every request hit cache**. The rebase moved the
SHAs and left the tree byte-identical, so every request was identical to run 2's
and replayed from its transcripts — the newest file in `.acceptance/cache/`
predates this run by an hour and a half.

So run 3 is **run 2's model responses rendered by the fixed tool**, not a second
opinion. Two consequences, both important:

- The report's judgements are one model run, not two agreeing.
- The omitted recommendation on obligation 5 is the **same** omission, not a
  reproduction of it. Nothing here is independent evidence about how often that
  happens.

This also confirms #279's claim that it moved no request key: a tool change that
altered a prompt or a schema would have forced a re-record.

## The numbers

| | count |
|---|---|
| obligations | 20 |
| strongly supported | **1** |
| partially supported | 10 |
| unsupported | 2 |
| indeterminate (recommendation NOT OBTAINED) | 1 |
| test evidence not required | 6 |
| recommended tests | **13** (12 prescribed, 1 NOT OBTAINED) |
| open questions | 0 |
| unrequested changes | 3, all `in_service` — none `separable`, none `risky` |
| mandate coverage | 20 of 21 requirements; the decline is the "Implementation" marker |

The gate needs every obligation strongly supported and zero recommended tests.
One of twenty is strongly supported. This is not close.

## Mapping check (DR-164) — the clean-verdict trap does not apply, but read on

The verdict is not clean, so the trap this check exists for is not live. The
mapping is nonetheless mostly healthy: across the six mapping calls, four
returned 14–17 obligation ids over 11–12 candidate tests. **One did not** —
10 of its 12 candidates came back with empty `obligation_ids`, 3 ids in total.
Three obligations carry `(no mapped test)`: 5, 13 and 20.

## Triage, finding by finding

### Obligation 5 — `no-root-task-file-read`, indeterminate, prescription NOT OBTAINED

#279 working exactly as designed: the omission is recorded, named with its
arithmetic (13 asked, 12 returned), excluded from the twelve rated obligations,
and the verdict stays red. **No action against #258.**

It is also the live argument for the **re-ask** that #275 deferred — a single
retry over the missing id would most likely have produced the prescription, and
without one this obligation cannot clear no matter what tests are written. That
decision is already filed.

Its `(no mapped test)` is the #245 twin split, already commented on #245 today
with this exact pair: obligation 4 (`…-check`, the Completion twin) cites three
tests from `tests/test_root_task_file_is_not_read.py`; obligation 5 (the
Constraint) cites none, from the same file that exists to satisfy it.

### Obligations 13 and 20 — unsupported, no mapped test

- **13, `no-failures-without-root-task-file`**: nothing in the suite asserts it.
  It was verified by hand — the suite passes with `current-task.md` deleted, at
  an identical test count — and a hand check is not evidence. **The tool is
  right.** A test can get partway there (build the corpus from a tree with no
  root task file and assert the case lists are unaffected); asserting *"a test
  run reports no failures"* in full needs a subprocess run, which is the M8
  execution tier and does not exist yet.
- **20, `no-root-task-file-dependence`**: the task-level umbrella, same shape.

### Ten partially supported — three different causes, and only one is mine

Read against what the tests actually do:

1. **Real, addressable thin spots** — obligations 3, 7, and partly 4 and 10. The
   corpus tests assert over the *real* corpus where a synthetic tree would be
   discriminating: nothing plants a sibling path outside `dogfood-logs/`, and
   nothing pins one case per file against a corpus built to duplicate one.
   `test_the_repository_root_task_file_is_not_a_case` already does this for the
   root file, so the shape is established and the gap is cheap to close.
2. **Recommendations that cross a declared scope exclusion** — obligations 8 and
   9. Both prescribe parser edge cases: an empty-section format, and an
   off-by-one span boundary. *"How a task file is parsed into sections"* is
   `exclusion-02`, which the same report shows as `addressed` on the code axis.
   The tool is asking for evidence about behavior the mandate excluded, and it
   knows the exclusion is there. **Tool defect — queued.**
3. **Unfalsifiable or mis-targeted defects** — obligations 2, 11, 12. *"The case
   list is populated only in some environments"*, *"non-empty but missing some
   intended coverage cases"* (which is not the obligation — the obligation is
   non-emptiness), and for 12 a defect that is circular: *"a different missing
   path is omitted correctly, but the specific dangling symlink in the test is
   still included."* Obligation 12's own test already carries a docstring
   explaining, from injection, that `glob` and not the `is_file()` filter holds
   the property up. This is the #225/#252 shape. **Queued.**

## Disposition

**Gate 2 fails.** #258 stays unmerged and no PR is opened.

Nothing here retracts the delivery: the issue's own Acceptance is met — the grep
returns nothing, the parse test runs over the committed corpus, the case list is
non-empty and inside `dogfood-logs/`, and the suite passes with the root task
file deleted (1,284 tests). What the gate says is that the *evidence* for several
obligations is thinner than "strongly supported", and on two of them it is right.

**The stronger form of that last check, run here for the first time:** the two
collections are compared directly rather than counted, and `pytest --collect-only`
is **identical with and without the root task file** — same 1,284 ids, same
order. Counting alone is not discriminating, and this run proves why: two
consecutive full runs on the same commit reported 1,282 and 1,284, because
creating `dogfood-logs/258-gate2-run3/` in between added its `current-task.md`
to the corpus and with it one parse case and one region-coverage case. **The
corpus grows by one directory per dogfood run, so the suite's size moves between
runs by design** — any future claim of the form "identical test count" should be
a collection diff instead.
