# Declaration — #243

## What I implemented

- `run_case` (`src/acceptance/benchmark/runner.py`) now calls
  `require_nonempty_registry(case.case_id, case.inputs.task_text)` as its first
  statement, so a case whose task file yields no requirements raises
  `EmptyRequirementRegistryError` before the temp task file is written and
  before `run_check` runs. The module docstring says why the runner checks even
  though the corpus case builders already do.

## What I tested

All in `tests/benchmark/test_runner.py`:

- `test_running_the_empty_skeleton_over_an_archetype_case_yields_an_all_miss_score`
  (the M-B0.2 acceptance test) now runs over
  `# Task / Add CSV export. / ## Constraints / - Apply the active filters to the export.`,
  which yields one requirement (the constraint). Its assertions are unchanged.
- `test_the_all_miss_score_depends_on_the_checker_not_the_input` (new) runs the
  same case through a test double that decomposes the constraint into the
  labelled obligation and classifies it `not_addressed`. It asserts
  `gap_recall == 1.0`. This is what shows the all-miss assertion can fail.
- `test_run_case_refuses_a_task_file_that_yields_no_requirements` (new) feeds
  the old `## Deliverable` text and asserts `EmptyRequirementRegistryError`
  naming the case id, and that nothing was written to the review store.
- `test_run_case_does_not_mutate_the_input_case` now uses the readable task text.

Full suite: 1876 passed, 2 xfailed. `ruff check` and `ruff format --check` clean.

## What I left out

- The synthetic cases in `test_scoring.py`, `test_alignment.py`, `test_case.py`
  — they never call `run_case`, so the guard does not touch them.
- The corpus case builders — unchanged; they already call the same check.

## What I assumed

- That a `# Task` section alone is not enough for the companion test. The
  decomposer treats `# Task` as the opening summary, and the default test double
  answers the summary as "already required", so no obligation came out. I added
  a `## Constraints` bullet so the double's obligation lands on a real
  requirement. The guard itself would accept the `# Task`-only text.
- That `gap_recall == 1.0` is the right strength for the companion assertion;
  the issue only asks that the all-miss assertion "fails if the checker reports
  the labelled gap", which any non-zero value shows.

## What I know is unverified

- I did not check whether any caller outside the test suite builds a case with
  an unreadable task file and relies on `run_case` scoring it as zero. A grep
  found `run_case` called only from `tests/benchmark/test_runner.py` and
  `tests/benchmark/test_labels.py`; the latter goes through
  `build_benchmark_case`, which already guards.
