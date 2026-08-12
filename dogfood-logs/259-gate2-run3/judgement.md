# Judgement — #259 Gate 2, run 3

**Base:** `c4828de` · **Head:** `87de1e0` · **Mode:** record

Three runs, all committed. Runs 1 and 2 are kept because the movement between
them is the finding, not noise.

## Verdict: NOT CLEAN — one obligation short, and that one is a tool defect

29 of 30 obligations strongly supported. The gate is blocked on exactly one:

**Obligation 15 — `completion-10`, "A test asserts that two runs over the same
obligation set choose the same pairs" — `unsupported`, "(no mapped test)".**

The test exists. It is
`tests/requirement/test_link_prefilter.py::test_two_runs_over_the_same_obligation_set_choose_the_same_pairs`,
and **the same report cites it twice elsewhere in the same run**:

- obligation 24 (`constraint-15`, "Two runs over the same obligation set choose
  the same pairs") — `strongly supported`, citing that test at 24.4;
- obligation 5 (`completion-06`, about the demand-type gate) — citing it at 5.5,
  which is a spurious mapping; that test has nothing to do with the type gate.

So in one run the mapper gave the test to the Constraint twin, gave it to an
unrelated obligation, and withheld it from the Completion twin whose text is
nearly the test's own name. **That is #245 verbatim** — "Mapping splits a
Completion expectation from its Constraint twin, unstably."

It was mapped correctly in runs 1 and 2:

```
run 1  obligation 15  ->  ...choose_the_same_pairs   (strongly supported)
run 2  obligation 15  ->  ...choose_the_same_pairs   (strongly supported)
run 3  obligation 15  ->  (no mapped test)           (unsupported)
```

Nothing about that test or that obligation changed between run 2 and run 3. The
only edit was two boundary tests added elsewhere in the same file.

**Disposition: attributed to a tool defect (#245), queued as a filing.** There is
no code change that answers it — writing a second determinism test to satisfy a
mapper that already found the first one, and cited it twice, is chasing a rating.

## What runs 1 → 3 actually establish

Run 1 raised three real gaps. All three recommendations were correct and specific,
all three are now fixed, and defect injection confirms each new test discriminates:

| gap | fixed by | injected defect | caught |
|---|---|---|---|
| nothing asserted the *linking path* embeds per obligation | `test_the_linking_path_embeds_every_obligation_exactly_once` | embed only `obligations[:1]` | yes |
| nothing varied the threshold to show it changes what is asked | `test_changing_the_threshold_changes_which_pairs_are_sent` | filter always returns True | yes |
| every provenance assertion read the **in-memory** object | `test_both_records_survive_a_round_trip_through_the_persisted_review` | `Field(exclude=True)` on `link_prefilter` | yes |

Run 2 raised the exact-threshold boundary. **That one was verified on its merits
before acting**: mutating `<=` to `<` passed all 1101 tests, so the gap was real
and not a rating artifact. Two boundary tests now pin it, and the same mutation
fails.

Run 2's `[separable]` finding about formatter churn was also correct and is fixed
— see below.

## The instability is the other finding, and it is #225

Run 1 → run 2 → run 3 moved ratings that had no evidence change:

- **Run 1 → 2:** obligation 1's mapped evidence was byte-identical — the same
  single test — and it fell `strongly supported` → `partially supported`.
  Non-discriminating obligations went 3 → 13 while the work only *added* tests.
- **Run 2 → 3:** adding **two** boundary tests moved **twelve** obligations up to
  `strongly supported`, most of them untouched by those tests, and moved one
  down to `unsupported` by dropping its mapping.

Both directions are the same defect: ratings that move under unchanged evidence.
This is #225 reproducing on a second task file, after #248. Queued as a comment
on #225 with these three runs as evidence.

## Formatter churn — addressed, cause queued

Run 3 flagged `[separable]`: "The CLI tests were reformatted extensively without
changing the asserted behavior." True. `tests/test_cli.py` showed 457 changed
lines for a 5-line edit.

The cause is repo-wide, not this branch: **49 files are not `ruff format` clean**,
and the `PostToolUse` hook reflows any dirty file it touches. Five of the files
this work needed were dirty at base. Each was restored and re-patched by script,
taking the branch from 1541/199 to 1172/47 lines. The underlying condition is
queued, not fixed here.

## Dispositions

| finding | disposition |
|---|---|
| obligation 15 unsupported with its test cited twice elsewhere | **tool defect — filing queued on #245** |
| ratings move under unchanged evidence, both directions | **tool defect — filing queued on #225** |
| three gaps from run 1 | **fixed**, each injection-verified |
| exact-threshold boundary | **fixed**, mutation-verified before and after |
| formatter churn flagged separable | **fixed**; repo-wide cause queued |
