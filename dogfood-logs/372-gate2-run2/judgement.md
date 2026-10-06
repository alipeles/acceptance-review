# #372 Gate 2, run 2 — judgement

Run on head `6a3a205`, continuing run 1 (`34601fedf98e6a6d`). Verdict
INCOMPLETE. **Not clean.** The BugsInPy data was moved out of the repo for this
run (see `revisions.txt`), and the foreign-test contamination of run 1 is gone.

Four obligations moved to strongly supported: BugsInPy mutants, the sandbox,
rebuild reproducibility, and the typed loader.

## Real finding — addressed in the commit after `6a3a205`

- **labels-from-running-tests (partial).** The survivor-sample test checked
  the sample's size, not its members. It now asserts every sampled id is a
  case the build produced, and that the case survived. Defect injection
  (sampling killed cases instead) makes it fail.

## Attributed to tool defects (drafts queued in `docs/DEFERRED.md`)

- **test-failure-status-recorded (partial)** and
  **baseline-failing-test-set-aside (partial)**: both recommendations name
  defects that would not violate the obligation. The first says the case "has
  no field for the edit-in-place failure status"; `killed` is that field. The
  second says a red test "not among those selected" could still be labelled;
  only selected tests are ever run, so only they can be labelled. This is #283
  again, added to the queued #283 comment.
- **labelled-cases-for-test-failure-judgement (indeterminate, both runs).**
  This is a `test_demand` obligation with no defect enumerated, which is #325.
  Comment queued.
- **random-survivor-sample-for-human-check (indeterminate, both runs).** Gate 1
  typed this obligation `human_review`, and no defect was enumerated for it, so
  its rating cannot be reached. That makes it a downstream cost of #196 (the
  decomposer typing automatable obligations `human_review`). Comment queued.
- **Unrequested change 2, `pyproject.toml` package-data.** It was `in_service`
  in run 1 and is `separable` in run 2, on an unchanged hunk. This is #359.
  Comment queued.

## Not a finding, but not "strongly supported" either

- 8 (implementation hunk), 16 (sample size) and 17 (no-change share): the tool
  rates these "no plausible defect: test evidence not obtainable", although
  tests exist for each (`test_the_build_labels_every_usable_test_against_every_mutant`,
  `test_the_report_holds_counts_and_the_spot_check_share_only`).
- 18–20 (200 cases, 30% killed, 30% survived) are properties of the built
  data, which is never in the repo. Their evidence is the local build: two
  byte-identical builds, recorded as counts in `findings.json`. **Non-code
  evidence, for the human.**
