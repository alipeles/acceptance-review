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

## 1. The ten-test gap between local and CI — SETTLED, not a defect

**Resolved 2026-08-31. Nothing to fix. Do not reopen this.**

The suite has two tests parametrised over every committed task file under
`dogfood-logs/`: `tests/requirement/test_region_coverage.py::
test_the_repositorys_own_task_files_are_fully_covered` and
`tests/requirement/test_task_file.py::test_parses_every_committed_task_file`.
So **each committed dogfood run directory adds exactly two tests** to the suite.

`e5e5ec7`, which added the five `dogfood-logs/316-*` run directories, was
committed to `main` and is **not an ancestor of `c177a1b`** (verified with
`git merge-base --is-ancestor`). CI's `ci.yml` triggers on `pull_request`, so
GitHub checks out the **branch merged into `main`** — five extra run
directories, ten extra tests. The local checkout of the bare branch has neither.

Verified by collecting both: a detached worktree at `c177a1b` collects **1625**;
this repo at `4a149a5`, which contains `e5e5ec7`, collects **1635** — the same
number CI's 1633 passed + 2 xfailed implies. Diffing the two collected lists
with the repo path normalised leaves exactly those ten ids and nothing else.
The earlier "1623 passed, 2 xfailed" is 1625 collected, so it was consistent all
along.

The prior note here that "no test parametrises over `dogfood-logs/`" was wrong;
that is what sent the search in the wrong direction.

**The general rule, which will recur:** a branch collects fewer tests than CI
whenever `main` gained a dogfood-log directory after the branch point, and
CLAUDE.md's convention of committing process artifacts to `main` makes that the
normal case. **Comparing a local test count against a CI test count across a
branch is meaningless.** Compare a local count only against a local count at the
same commit.

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

### SHIPPED in the working tree, uncommitted — 2026-09-01

**The human waived the split into separate issues and asked for the change
directly.** Two things landed together in `defects/pair_mapping.py`, and they
have to stay together — see below.

1. **`_batches` builds rectangles instead of one test per request.** Tests owed
   an identical defect set are grouped and share a call, up to
   `DEFAULT_TESTS_PER_BATCH = 4`. `DEFAULT_PAIR_BATCH_SIZE = 40` still caps
   judgements per response, so four tests in a call are offered a quarter as
   many defects each — the response does not get bigger.
2. **`test_id` is no longer enumerated in the pair schema.** `_allowed` split
   into `_constrained_ids` (defect ids, into the schema) and `_scanned_ids`
   (both, into `scan`), so a test id the call never offered is still recorded as
   an `UnusableAnswer` rather than believed.

**Why together.** A free-text `test_id` with ONE test per call measured 0.8021
against the enumerated control's 0.8785. With several tests it measured 0.9653
against 0.9688 — indistinguishable. Ship one without the other and the measured
result is a regression.

Also: `tests_per_batch` is a new `RunConfig` field and `--tests-per-batch` flag,
folded into the pair request key beside `size` so changing it invalidates
transcripts.

**Suite: 1636 passed, 2 xfailed.** `ruff check` and `ruff format --check` clean
over `src` and `tests`. Two test doubles had to change and the change is not
cosmetic: they read the offered test ids off the *schema enum*, which no longer
exists, so `tests/support.py::_tests_offered` reads them off the `### test <id>`
headings in the prompt — where the model reads them.

**Not yet measured: whether anything actually caches.** That needs one real
`acceptance check --mode record`. Nothing in the pilot can show it; every pilot
prompt is under the 1,024-token floor.

### The two prefilter experiments, cleaned up and parked

**`ruff check .` and `ruff format --check .` are now clean over the whole repo.**
They were red because of `docs/experiments/coverage-prefilter/` (committed
unlinted in `4a149a5`, which is why `main`'s CI is failing) and
`docs/experiments/prefilter-committee/` (untracked, never linted). **`main` stays
red until this is pushed.**

Both were run by an agent somewhere else and arrived carrying absolute paths into
a container — `/root/exp`, `/root/head314` — so as committed they could not run
here and their figures could not be checked. `prefilter-committee/paths.py` now
names the three external inputs as environment variables and every script stops
with a sentence when one is missing. **No computation changed**, only paths and
lint. One real fragility fixed on the way: `transfer314.py` built predicates
closing over loop variables, which is correct only because the scorer consumes
them before the next iteration; they are bound as arguments now.

Inputs a future session needs, none of which are or should be in the repo: a
worktree at each corpus head carrying a `.coverage` file from an instrumented
suite run, and the #316 review's own JSON. Plus `pip install coverage`, which is
deliberately not a project dependency.

**`docs/experiments/README.md` is new** and is the thing that makes them
revisitable: an index saying which experiments are settled and which two are
parked on M8.4, with what M8.4 decides for each. Both stop at the same wall — a
small set of pairs where a static signal and the pair judge disagree, which
nothing static can adjudicate — so injection over those pairs settles both at
once and gives the first measurement of pair-verdict accuracy against ground
truth.

### The pilot arms behind it

Uncommitted in the working tree: two new arms in
`docs/experiments/pair-response-shape/pilot.py`, their figures in
`findings.json`, and a *Dropping `test_id`* section in that directory's
`README.md`. Cost $0.42, nine draws each, recorded so a re-run replays free.

- **`per-test`** — the control. One call per test, which is what
  `pair_mapping.py::_batches` already does, with the shipped `_Unions` schema
  unchanged so `test_id` is present and pinned to that call's one test.
- **`no-test-id`** — the candidate. The same, with `test_id` and its
  one-element `tests` wrapper removed from the schema.

They send byte-identical request content — a probe asserts it before any call —
so the only difference is the response schema.

**Recall does not drop.** Candidate better on 4 draws of 9, worse on 3, equal on
2; mean 0.8889 against 0.8785; narrower spread (0.0625 against 0.0938);
kills-per-defect floor 0.763 against 0.711, so DR-173's failure mode — an arm
buying a smaller response by answering *no* more often — is absent. It also
sends 6.5% fewer prompt and 14% fewer output tokens.

**The caching half of #324's acceptance cannot be answered by this pilot.** Both
arms read a 0.0% cached share, and that is meaningless here: the per-call prompt
on the archetype fixtures is **725 tokens** (candidate) and **775** (control),
under OpenAI's **1,024-token floor**. Nothing could cache whatever the schema
did. It needs a real review run. `cached_tokens` is now recorded per arm in
`findings.json`, so that run's figure has somewhere to go.

**One thing the pilot did confirm that #324 only believed:** the two arms' request
content is byte-identical and the candidate still sends 6.5% fewer prompt
tokens, which is the response schema being billed as prompt.

**Not yet done:** the change itself. Removing `test_id` from
`pair_mapping.py::_TestVerdicts` and `_allowed` moves every pair request key and
re-records that stage's corpus. The recall precondition is now satisfied, so
this is clear to do on those grounds.

**Two drafted filings are in `docs/DEFERRED.md`, unfiled, awaiting approval** —
the batching finding below, and a comment reporting all of this on #324.

### The surprise: one test per call costs about 11 points of recall

Both per-test arms fall below the pilot's bar on **9 draws of 9**, where the
case-batched `union` arm — same response schema — falls below on 1. Mean 0.8785
and 0.8889 against 0.9688.

It is the batching, not the schema and not the reworded instruction. Five of the
thirteen cases hold one test, so there a per-test arm and `union` send the same
tests; they score **identically, 1.0000 to 1.0000, over 45 edge-draws**. The
whole drop is in the eight multi-test cases: 0.9630 against 0.8560 over 243
edge-draws.

`_batches` chose one test per request deliberately, and its docstring gives the
reason — a multi-test batch offers a schema inviting every test x every defect,
so answers would be dropped on the way back, the silent filter DR-164 forbids.
That priced the choice in **requests**. It never priced it in **recall**.

**Do not act on it from these numbers.** 27 labelled edges over 8 constructed
cases holding 2-3 tests each, where a real review holds 496 candidate tests, and
case batching does not scale to a real review anyway. Queued as a filing.

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
