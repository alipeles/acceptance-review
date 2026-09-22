# #348 Gate 2, run 3 — run `74a2ec85e3b40404`, continuing `845dbd7c4ca04392` — NOT clean

Verdict INCOMPLETE: `docs-ranking-experiment-findings` unsupported, 0 of 2.
Every other obligation addressed and strongly supported, or a scope exclusion
confirmed from code. Two findings, both attributed to tool defects with filings
queued in `docs/DEFERRED.md`.

## 1. `docs-ranking-experiment-findings` — unsupported — tool defect

Run 2 had it `indeterminate` with no test. Run 3 has the test run 2 asked for,
`tests/test_rank_prefilter_findings.py`, and rates it WORSE, because the
judge never saw it: every pair between that test and both of the criterion's
defects is `[prefiltered]`, reason "the test's module imports no first-party
module, the test takes no fixture, and it references no name defined in
docs/experiments/rank-prefilter/FINDINGS.md — no path to the defect exists".

The test opens FINDINGS.md by path. The prefilter follows imports, fixtures
and names only, so it cannot see that, and a prefiltered pair counts as a
proven survival. The test does discriminate — changing one replay share in
FINDINGS.md fails it — so the evidence exists and the tool cannot reach it.
Queued: "The reachability prefilter 'proves' no path from a test that reads
its subject from disk", against #182.

The recommended test for this criterion is the test that already exists (it
asks for the log values as the source of truth, which is what
`test_the_replay_figures_in_the_findings_are_the_ones_the_replay_printed`
does). That is #250/#287's shape — a recommendation for a test that exists —
arising here from the prefilter rather than from mapping.

## 2. `[separable]` item 14 — the `UnjudgedCause` docstring — tool defect

The same `review_state.py` hunks were `in_service` in run 2. The docstring had
to change: it said "Three causes" and that every cause but `PREFILTERED` counts
as unknown, both false once `DEFECT_ALREADY_COVERED` exists. Queued: "The same
unchanged hunk is `in_service` in one run and `separable` in the next",
against #185.

## Also

- `[already_present] asked-count-excludes-unanswered-pairs` again; recorded
  against the #183 filing queued at run 1.
- `completion-01: Implementation` declined as a section marker, as in run 2.
- 14 other unrequested changes, all `in_service`.
