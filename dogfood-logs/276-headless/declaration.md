# Declaration — #276

## Implemented

- In `src/acceptance/cli.py`, a helper `_obligation_bracket` builds the bracket
  `[type/derivation, required_evidence]`, e.g. `[functional/explicit, tests_only]`,
  and appends `, satisfied by absence` when `satisfied_by_absence` is true.
- A helper `_required_evidence_reason` prints `why <required_evidence>: <reason>`
  under the restated obligation text when `required_evidence_reason` is non-empty.
- Both are used in all three places `decompose`'s text output lists obligations:
  the requirement-major view, the "Obligations mapped to no requirement" list, and
  the flat fallback for a task file with no parsed requirements. The orphan list
  previously showed only `[type]`; it now shows the full bracket too.

## Tested

- Three new tests in `tests/requirement/test_requirement_map.py`, against a
  hand-built decomposition fixture with one default obligation, one narrowed to
  `tests_only` with a reason, and one `satisfied_by_absence`:
  `test_the_cli_shows_each_obligations_required_evidence`,
  `test_the_cli_shows_the_reason_for_a_narrowed_required_evidence`,
  `test_the_cli_marks_an_obligation_satisfied_by_absence`. All three failed before
  the change and pass after.
- Updated `tests/test_cli.py::test_render_decomposition_lists_obligations_and_open_questions`,
  which pinned the old bracket text that the issue asks to change.

## Left out

- `--json` output and the rendered review report (`report.py`) are untouched.
- The orphan list and flat fallback have no dedicated new test for the reason line
  or the absence mark; only the requirement-major view is tested for all three.

## Assumed

- The mark for an absence-satisfied obligation goes inside the same bracket, as
  the words `satisfied by absence`. The issue only says it must be distinguishable.
- The reason line is labelled `why <value>:`, which is my wording, not the issue's.

## Unverified

- I did not run `decompose` on a task file whose model output actually narrows
  `required_evidence`, so the live output with a reason is seen only in tests.
- 24 benchmark-corpus tests fail in this session; I verified they fail identically
  on unmodified main, because this clone is shallow and lacks the pinned commits.
