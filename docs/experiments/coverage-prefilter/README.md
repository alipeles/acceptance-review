# Coverage-context prefilter — experiment notes

Working notes for an offline experiment on whether **recorded per-test coverage**
can cut the (defect, test) pair set before the judge in `defects/pair_mapping.py`
sees it. Written in the shape of `docs/experiments/pair-prefilter/README.md`,
which asked the same question of embeddings; this asks it of execution evidence.

**This file is the method and its traps. The findings are `FINDINGS.md`, and the
raw numbers are `findings.json`.**

## Why the question exists

Same economics as `pair-prefilter`: the pair stage dominates run cost, its kill
rate is about 1%, and a prefilter is the only lever that reaches output tokens,
because removing a pair removes its verdict. On the #316 Gate 2 run this
experiment scores against, the stage cost $6.02 of the run's $6.87 (3.87M prompt
tokens, 0.69M output tokens, 992 live calls, 0% cached).

Coverage promises something embeddings cannot: a physical claim. A test whose
recorded coverage never touches a defect's implicated lines did not execute that
code, where an embedding filter only claims the two texts look unrelated. The
question is whether that claim holds against the judge's recorded kills.

## Method

1. Check out the reviewed revision and run the suite once under coverage with
   per-test dynamic contexts:

   ```bash
   git checkout 3e1d3a9eaa7e7610dcda30fa42654ebb9e21ebf4
   .venv/bin/pytest -q -p no:cacheprovider --cov=acceptance --cov-context=test tests
   ```

2. Resolve each defect's `code_refs` (`path#hunk`, 0-based, the
   `coverage/prompt.py::hunk_label` scheme) to head-side line ranges via the
   stored review's change set (`new_start`, `new_lines`).

3. A defect's candidate tests are the tests whose coverage context touches any
   implicated line. Everything else is excluded.

4. Score against the same review's pair verdicts: what share of pairs survives,
   and how many recorded kills the filter would have excluded.

```bash
python docs/experiments/coverage-prefilter/score.py \
    .acceptance/cache/reviews/3e1d3a9eaa7e7610dcda30fa42654ebb9e21ebf4.json \
    --coverage-file .coverage --repo-root .
```

No model calls. The suite run took 5m15s (1,623 passed, 2 xfailed; Python
3.11.15, pytest 9.1.1, coverage 7.16.0, Linux container).

## Traps

**Import-time lines poison the conservative rule.** A `def` line, an import, a
module constant all execute at import, under an empty coverage context. Almost
every hunk contains at least one (44 of 48 defects here), so the rule "a line
only executed at import might be reached by anyone, keep every test" keeps 96.5%
of pairs and filters nothing. Any usable rule must ignore import-only lines when
collecting candidates, and then module-level defects (regions with *only*
import-time lines) need an explicit judge-everything fallback rather than a
silent empty candidate set.

**Score fallbacks against judged test ids, not observed contexts.** The first
cut of the scorer set fallback candidates to "every test seen in a coverage
context". Judged tests that never appear as a context then leak out of the
fallback set, which flatters the filter and invents lost kills. The fallback
universe must be the review's own judged test ids.

**Context labels carry phase suffixes.** `tests/x.py::test_y|run` (also
`|setup`, `|teardown`); strip the suffix before comparing to `test_id`.

**The oracle is the model.** The baseline labels are the pair judge's own
verdicts, which DR-180 and DR-173 document as unstable. A kill the filter
excludes is therefore a *disagreement*, not a proven filter error, and it cuts
both ways: several lost kills are pairs where coverage shows the test never
executes the implicated code on the fixture it actually runs, which indicts the
verdict, not the filter. M8.4 injection is the adjudicator; until it runs,
recall figures here are agreement with a noisy oracle.

**Widening regions is a null.** Expanding every hunk range to its enclosing
function bodies (AST `end_lineno`) recovers zero of the lost kills. The losses
are not region narrowness; the killing tests genuinely do not execute those
functions.

**Coverage cannot see file reads.** Tests that assert on README or
decision-record *text* kill documentation defects through `open()`, which
line coverage does not record. Defects whose refs are not Python fall back to
judge-everything here; a real implementation could track file reads instead.

## Relation to the embedding prefilter

`pair-prefilter` (embeddings, #314's corpus): excludes 22.0% with zero lost
kills. This filter (coverage, #316's corpus): excludes 61.3% but loses 43 of
268 kills. Different corpora, so not directly comparable, and different failure
surfaces: embeddings miss on wording, coverage misses on data dependencies and
absence defects. The natural combination is `pair-prefilter`'s own rule, reject
only when every filter rejects, which needs both scored on one corpus. Unrun.
