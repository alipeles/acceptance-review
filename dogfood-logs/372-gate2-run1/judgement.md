# #372 Gate 2, run 1 — judgement

Run `34601fedf98e6a6d`, continuing `9a1225e794aaffef`. Verdict INCOMPLETE.
**Not clean.** It cost $1.04.

## The run was contaminated (tool defect)

Test discovery walked into the gitignored `.acceptance/mutant-labels/projects/`
(the BugsInPy checkouts the build fetches) and offered thefuck's and
youtube-dl's own tests as candidate evidence. 202 of the 207 unjudged pairs
name one of those tests, and most of the "Execution findings" set-asides are
them too. Cause, verified: `evidence/discovery.py` walks the tree with a fixed
`_EXCLUDED_DIRS` list and reads neither `.gitignore` nor `.acceptance/ignore`.
Not in the backlog. Queued as a filing under #182 (test discovery & mapping)
in `docs/DEFERRED.md`. Every mapping-based rating in this run is suspect
because of it, so the rerun moves the data out of the repo while it runs.

## Real findings — addressed in `37064fb`

- **labels-from-running-tests (partial).** There was no test that a run which
  never completes is kept out of the labels. Added
  `test_a_run_that_never_completes_is_never_turned_into_a_label`. Defect
  injection (label every outcome) makes it fail.
- **sandbox-tests-run-in-existing-sandbox (partial).** Every build test
  injected a fake sandbox, so nothing proved a real build uses the real one.
  Added `test_a_real_build_runs_every_test_through_the_existing_sandbox`.
  Injection (a wrapped default runner) makes it fail. The recommendation
  itself was wrong; see below.
- **fixed-operator-mutants-on-bugsinpy-projects (partial).** Added
  `test_a_fix_to_a_test_file_or_a_non_python_file_is_never_mutated`.
- **test-failure-status-recorded (indeterminate, no mapped test).** Added a
  focused test, `test_killed_is_true_exactly_when_the_test_failed_with_the_edit_in_place`.
- **bugs-in-py-pinned-rebuild-determinism (partial).** The enumerated defect
  "output depends on unpinned environment" is fair: nothing recorded what the
  environments resolved to. The label file now records every environment's
  packages, and `test_each_environment_s_packages_are_recorded_and_change_the_file`
  checks it.

## Recommendations that misread the requirement (tool defect)

- `sandbox-tests-run-in-existing-sandbox`: it asks to prove that the `sample`
  and `report` commands run tests in the sandbox. They run no tests at all.
- `test-failure-status-recorded`: it asks for a failure status "not equivalent
  to a simple killed/survived boolean". The requirement is "whether the test
  failed", which is exactly a boolean.
- `bugs-in-py-pinned-rebuild-determinism`: it asks to change the inputs
  between two builds. The requirement is about the *same* inputs.

These are the #283 shape (a prescription's `detects` names a defect that would
not violate the obligation). A comment is queued for #283.

## Judged after the rerun

- `typed-loader-for-cases`, `random-survivor-sample-for-human-check`,
  `report-gives-sample-size` and `share-found-to-change-no-behaviour` show no
  mapped test, although the tests the recommendations ask for already exist
  (`test_loader_rejects_a_case_with_a_field_it_does_not_know`,
  `test_the_survivor_sample_takes_one_case_per_edit_and_is_seeded`,
  `test_the_report_holds_counts_and_the_spot_check_share_only`). Possibly
  caused by the contamination. Judged on run 2.
- `labelled-cases-for-test-failure-judgement` (`test_demand`) is
  indeterminate with no defect enumerated. This looks like #325 (the
  enumerator will not enumerate for a `test_demand` criterion).
- 18–20 (200 cases, 30% killed, 30% survived) are properties of the built
  data, which is never in the repo. Their evidence is the local build,
  recorded as counts in `docs/experiments/372-mutant-labels/findings.json`.
  This is non-code evidence for the human.
