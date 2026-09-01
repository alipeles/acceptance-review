# Prefilter committee — experiment notes

> **Parked until M8.4, deliberately.** The result is in `FINDINGS.md` and is not
> waiting on more static measurement: three specific pairs cap every transferred
> committee, and whether they are filter blind spots or judge error is a
> question only defect injection can answer. See `docs/experiments/README.md`
> for what M8.4 settles here and in `coverage-prefilter/`, which hits the same
> wall on the same families of pair.
>
> **Not runnable from a clean checkout.** It needs a worktree at each corpus's
> head, each holding a `.coverage` file from an instrumented suite run, and the
> #316 review's own JSON. `paths.py` names the three environment variables and
> each script stops with a sentence when one is missing. It also needs
> `pip install coverage`, which is not a project dependency because the tool
> does not use it.
>
> These scripts were run elsewhere and arrived carrying absolute paths into a
> container (`/root/exp`, `/root/head314`), so as first committed they could not
> run here and their numbers could not be checked. Only the path handling and
> the lint changed; no computation did.

Working notes for scoring the three-voter prefilter committee on both pair
corpora: **locality** (`pair-prefilter/locality.py`), the **code-4 embedding
pair** (description and region similarity, `pair-prefilter/score.py`), and
**coverage reachability** (`coverage-prefilter/score.py`'s default rule). Rule
under test, the standing instruction of 2026-08-30: **reject a pair only when
every voter rejects it.** Written in the shape of
`docs/experiments/pair-prefilter/README.md`.

**This file is the method and its traps. The findings are `FINDINGS.md`; raw
numbers in `committee314.json` and `committee316.json`; the scripts are the
record of how each number was produced.**

## The two corpora

| | #314 Gate 2 | #316 Gate 2 |
|---|---|---|
| pairs | 12,450 | 23,808 |
| kills | 127 (1.0%) | 268 (1.1%) |
| defects x tests | 75 x 166 | 48 x 496 |
| head | `2945551` | `3e1d3a9` |
| source | `pair-prefilter/verdicts.json.gz` | stored review `3e1d3a9…json` |

Having two corpora is what makes the deployment question askable: thresholds
tuned to zero loss on one corpus are applied unchanged to the other, which is
the position a shipped filter is always in. Nothing here retunes on the corpus
being scored except where the row says "tuned on self".

## Method

1. **#314 corpus**: `corpus.load()` exactly as `pair-prefilter/score.py` runs
   it, worktree at `2945551`. Embedding similarities replay from the recorded
   Voyage cache; the union figure reproduces FINDINGS' 22.0% to the digit,
   which is the check that this harness matches that one.
2. **#316 corpus**: `corpus316.py` builds the same `Corpus` shape from the
   stored review: defects and the change set are read directly, and each
   test's source is re-extracted from the worktree by AST and **verified
   against the verdict's own `test_digest`** before it is admitted. All 496
   verify. Its embeddings are fresh Voyage calls through the experiment's
   recorded client (about 60 paced requests; 90 of the 496 test sources were
   already in the cache from #314).
3. **Coverage voter**: one instrumented suite run per corpus head
   (`pytest --cov=acceptance --cov-context=test`; 3m51s and 5m15s), then the
   `coverage-prefilter` default rule: a defect's candidates are the tests
   whose per-test contexts touch any implicated hunk line, import-only lines
   ignored, judge-everything fallback when a defect has no test-context line
   (1 of 75 defects on #314, 9 of 48 on #316).
4. **Committee solve**: `score.best_lossless_union` unchanged, with the base
   keep-predicate widened from locality to locality-or-coverage. The solver
   already treats the base voter as a set of pairs no threshold may touch, so
   a third voter is a one-line change, which is the point of measuring it this
   way.
5. **Transfer**: the (description, region) thresholds the solver picks on one
   corpus are applied verbatim to the other, under both base predicates.

## Traps

**Test-source extraction must match `discovery._node_source` byte for byte.**
`ast.get_source_segment` differs from discovery's line-slice
(`lines[lineno-1:end_lineno]` joined with `\n`) on 13 of 496 tests; the digest
check catches the mismatch immediately, which is what it is for. Use the
line-slice.

**The import-only-line trap carries over from `coverage-prefilter`.** A `def`
line executes at import, so nearly every hunk contains an empty-context line;
collecting candidates from test-context lines only, with an explicit fallback,
is what makes the voter mean anything.

**Zero-loss thresholds are corpus statistics, not properties of the filter.**
Both transfers lose kills that the tuned-on-self run keeps. Treat any zero-loss
figure as an in-sample number; the transferred rows are the deployment
estimate.

**The oracle is still the judge.** Kills are the pair judge's own verdicts.
Every residual lost pair in the transfers belongs to the families
`coverage-prefilter/FINDINGS.md` flags as candidate judge error (end-to-end
byte-identical tests, doc-text reads, carry-forward ledger tests), so the
committee's ceiling depends on M8.4 adjudicating those, in either direction.

## Reproducing

The scripts ran in a disposable container with two checkouts: `REPO` at
`3e1d3a9` (also the working dir, so the embedding cache resolves under
`.acceptance/cache/`) and a worktree at `2945551`. `committee314.py`,
`corpus316.py`, `committee316.py`, `transfer314.py` pin those paths at the top;
point them at your own checkouts to re-run. Fresh embeddings need
`VOYAGE_API_KEY`; everything else is cache and CPU.
