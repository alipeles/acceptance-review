# Task

Build a set of labelled cases for the judgement "would this test fail if this
defect were present?", where every label comes from actually running the test
against the defect rather than from a model.

The defects are fixed-operator mutants on BugsInPy projects: each is one small
mechanical edit, such as flipping a comparison or changing a constant, so the
edit is the defect and can never misdescribe what was injected. Each case holds
the requirement text the test is meant to check, the test's source, the
implementation hunk the defect was injected into, a text description of the
defect, the exact edit applied, and whether the test failed with the edit in
place.

Tests run in the existing sandbox (`src/acceptance/execution/sandbox.py`). A
test that already fails on the unmutated code is set aside rather than
labelled, as `src/acceptance/mutation/baseline.py` does.

Because an edit can change no behaviour at all, some survivors are not evidence
of a weak test. The build draws a random sample of survivors for a person to
check, and its report gives the sample size and the share found to change no
behaviour.

The set holds at least 200 cases, at least 30% of them killed and at least 30%
survived.

## Constraints
- BugsInPy declares no license and this repository is public. Cases derived
  from BugsInPy are written only to a gitignored local directory and never
  committed; only aggregate counts and rates may be committed. The build reruns
  from a pinned list of BugsInPy bug ids, and rebuilding from the same pinned
  inputs produces the same file.
- The cases load through a typed loader in `src/acceptance/benchmark/`, the
  same way `GroundTruthLabels` loads.

## Scope exclusions
- Improving how the checker's mutation tier writes its own edits.
- Using the cases to score any judge.
