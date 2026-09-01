# Session state — the two follow-ups after #316

Rolling state. Keep the headings; rewrite the contents wholesale rather than
appending. Delete this file when both items below are done, and go back to one
file per issue.

**The GitHub issue stays authoritative** (#168). This file carries only what the
issues do not.

*Last updated: 2026-09-01*

---

## Status

**#316 landed** as `58b8463` via PR #323, closing the last open child of #312,
the defect-first evidence parent. `main` is at that commit and CI is green:
**1633 passed, 2 xfailed**, ruff lint and format both clean.

Two follow-ups, in this order. **CLAUDE.md exempts both from Gate 1 and Gate 2 —
no `current-task.md`, no `decompose`, no `check`.** That exemption covers these
two and nothing else; anything they turn up takes both gates in full.

## 1. A local pytest run collects ten fewer tests than CI does

**Do this first.** Until it is settled, "the suite passes" from this machine is a
weaker claim than it sounds, and everything after it rests on that claim.

On `c177a1b`, CI reported **1633 passed, 2 xfailed**. The same commit on this
machine reported **1623 passed, 2 xfailed**, and `pytest --collect-only -q`
counted 1625 where CI's total implies 1635.

What I ruled out, and verified:

- Nothing was lost between HEAD and the working tree. Identical test-file lists,
  identical count of `def test_` (1052 either side), and the only uncommitted
  diff was four formatting line-joins with nothing semantic in them.
- Every test added during #316 is present in HEAD — checked by name for five of
  them, including the whole of `tests/test_concurrency.py`.
- Nothing skipped: `pytest -rs` reported no skips.
- No test parametrises over `dogfood-logs/`, and the fixture directories that
  are parametrised over (`tests/fixtures/archetypes`, `rating-regression`,
  `rating-stability`) did not change.

**What I did not check, and would start with:** whether a `conftest.py`,
`pytest.ini`/`pyproject` setting, or a stale `__pycache__` is excluding a
directory locally; whether `.venv`'s pytest version differs from CI's; and what
`pytest --collect-only -q` produces on a clean clone of the same commit, diffed
against the same command here. That diff names the missing ten directly and is
the cheapest first move.

Earlier in the session I reported 1633 locally and later 1623, and CI says 1633
is right — so the local run is the anomaly, not the earlier report.

## 2. #324 — nothing caches, because every call sends a unique response schema

Worth roughly **$2.90 of a $6.87 review**. #316's Gate 2 reported **0.0% cached
prompt tokens on all seven stages**, 1,012 calls.

**Measured, so do not re-derive:**

- The message prefix is fine. Messages 0 and 1 of a pair call are the shared
  preamble and the `## Defects` block, ~**1,544 tokens** — clear of OpenAI's
  1,024 floor — taking only **6-7 distinct values across 1,762 pair calls**. The
  defect-block move that landed in #314 as `8921b91` works.
- **1,762 distinct response schemas across 1,762 pair calls.** Removing the
  `test_id` enum collapses that to **7**; removing `defect_id` alone leaves 617.
- Every stage constrains at least one id per call, which is why all seven read
  0.0% rather than one of them.
- I believe the structured-output schema is part of the provider's cached
  prefix. **Not confirmed from OpenAI's side.** The in-repo evidence is #302,
  which removed a per-batch `test_id` enum from the retired mapping stage after
  measuring 461 of 464 calls caching nothing.

**The first task is the pilot arm, not the change.** Removing the constraint can
cost recall: `test_id` sits at the top of the pair response and its enum holds
exactly one value today, so the model cannot get it wrong; unconstrained it must
echo a long pytest node id exactly, and a paraphrase loses that call's 24-40
judgements at once. The response-shape pilot already found that shortening the
*defect* ids cut output 25% and lost a third of the labelled kills, returning
nothing on 4 of 13 cases.

`docs/experiments/pair-response-shape/pilot.py` scores shapes against #315's
labels with request content held identical across arms. Add an arm that **drops
`test_id` from the response entirely** — a batch holds one test, so the caller
already knows which; removing the field is safer than leaving it unconstrained
and saves output too. **Nine seeds**: the pilot's notes record three giving a
wrong answer where nine gave the right one.

Changing `_allowed` moves every pair request key and re-records that stage's
corpus.

## Also open, not scheduled

- [#325](https://github.com/alipeles/acceptance-review/issues/325) — a
  `test_demand` criterion is never enumerated for, so since #316 it is
  permanently `indeterminate` and blocks any clean verdict. Under #183.
- [#326](https://github.com/alipeles/acceptance-review/issues/326) — eleven
  ground-truth labels name `nominally_supported`, which the tool no longer
  produces. **They are correct as written**, so this is a decision, not a
  relabelling: three options are in the issue and my recommendation is to score
  the two classes as agreeing rather than edit eleven human judgements. Labelled
  `decision` and `human-gate`. Under #186.
- [#327](https://github.com/alipeles/acceptance-review/issues/327) — defects
  enumerated for criteria owed no test, which nothing can read. Under #183.
- **Still owed from #314:** `docs/DR-314-pair-response-shape.md` describes a
  response shape no longer in the code. Deliberately not drafted by an agent —
  CLAUDE.md wants a Decision Record written by hand after reading the numbers.
- **The embedding prefilter's hold-out is unrun.** Its 22.0% of pairs excluded
  with all 127 kills kept is fitted in-sample, not an operating point. The
  missing measurement is a hold-out against #315's archetype labels; embeddings
  are cached, so re-runs make no calls.

## A committed experiment that bears on both items

`docs/experiments/coverage-prefilter/` was untracked and is now committed. It is
not mine — another session scored it against **this** session's #316 Gate 2 run
at head `3e1d3a9` — and I committed it as written. Read `FINDINGS.md` before
touching the pair stage; its headline is that coverage reachability is **not**
shippable as a silent prefilter for the static judge.

Two things in it change what the items below are worth:

- It measures the #316 Gate 2 run independently: 23,808 pairs, 268 kills, a
  **1.1% kill rate**, 48 defects against 496 tests. That corroborates the pair
  counts in this file from a second source.
- It argues the coverage map is the right **test selection for M8.4's defect
  injection** — a test that never executes a line cannot fail on a mutation of
  it — at roughly 20 CPU-minutes and zero tokens against $6.02 of static
  judging per run. If that holds, it is a larger lever than #324's caching fix,
  and the two are independent.

It also names 43 pairs where coverage and the judge disagree, and says several
look like judge error rather than filter blind spots. Those are a ready-made
case list for the first real measurement of pair-verdict accuracy.

## Numbers worth not re-deriving

- #316's Gate 2: **$6.87**, 1,012 calls, 992 of them pair judgements, 30
  criteria, 48 defects, **496 candidate tests**, 23,808 pairs.
- #314's Gate 2, for comparison: **$4.25**, 375 calls, 37 criteria, 75 defects,
  166 candidate tests, 12,450 pairs. **More criteria and more defects, less
  money** — the driver is candidate tests, which scale with how much of the
  suite a diff touches.
- The union response shape is working: output per pair fell **43.9 → 29.1
  tokens**, a 34% drop against the pilot's projected 18%.
- Pricing: prompt **$0.75/M**, output **$4.50/M**.
- **Defect-id aliasing does not work.** Per-batch short ids cut output 25% and
  lose a third of the labelled kills. Do not retry; a shorter but still
  *meaningful* id is the untested variant.

## Two process notes from this session

**Run `ruff format --check` as well as `ruff check`.** CI runs both and I ran
only the first, so four unformatted files reached the branch and CI failed.
CLAUDE.md's Commands section now lists both.

**Task-file wording drifts when a decision is made mid-task.** #316's Gate 2
found two disagreements between the mandate and the code, and both were the
mandate: a ruling during the session dropped `nominally_supported` and widened
what `unsupported` means, and neither constraint was updated. The tool caught it
precisely. If a decision changes what the software should do, change
`current-task.md` in the same breath.
