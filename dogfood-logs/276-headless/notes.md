# Notes — #276 headless run

## Decompose

`decompose` exited 0 and produced 7 obligations from 4 requirements
(`decompose.log`; stderr with cost and run id in `decompose.stderr`).

Obligations I believe are correct: `show-required-evidence-in-bracket`,
`print-required-evidence-reason-beneath-restated-text`,
`satisfied-by-absence-marked` (from task-01), `decomposition-fixture-regression-test`
(task-02), `json-output-unchanged` (exclusion-01).

Obligations I believe are invented, and inverted:

- `review-report-not-unchanged`, from exclusion-02 ("The rendered review report is
  unchanged."). The restated text says the opposite: "The rendered review report
  changes to reflect the new evidence metadata and absence marker formatting
  requirements." The obligation id itself carries the negation.
- `review-report-evidence-reason-display` and `review-report-absence-marking`, also
  from exclusion-02. They demand that the review report gain the new lines — the
  exact thing the exclusion forbids. They appear to be task-01's obligations
  re-derived against the review report.

Missing: none that I can see.

Open questions: none were raised.

Also: `satisfied-by-absence-marked` is typed `invariant`; the other two display
obligations are `explanation_observability`. Harmless, but inconsistent.

## Reproduction

The three new tests in `tests/requirement/test_requirement_map.py`, run before the
fix (`pytest -q tests/requirement/test_requirement_map.py -k "required_evidence or narrowed or absence"`):

```
>       assert 'The formatter exists; only a test is asked for.' in block
E       AssertionError: assert 'The formatter exists; only a test is asked for.' in '    -> usd-format  [functional/explicit]\n       Format money as USD.\n'

>       assert "satisfied by absence" in _line_for(output, "pdf-untouched")
E       AssertionError: assert 'satisfied by absence' in '    -> pdf-untouched  [functional/explicit]'

FAILED tests/requirement/test_requirement_map.py::test_the_cli_shows_each_obligations_required_evidence
FAILED tests/requirement/test_requirement_map.py::test_the_cli_shows_the_reason_for_a_narrowed_required_evidence
FAILED tests/requirement/test_requirement_map.py::test_the_cli_marks_an_obligation_satisfied_by_absence
3 failed, 31 deselected in 0.52s
```

The bracket printed `[functional/explicit]` with no `required_evidence`, no reason
line and no absence mark — the defect the issue describes. After the fix,
`tests/test_cli.py` and `tests/requirement/test_requirement_map.py` pass (83 passed).

Full suite after the fix: 1854 passed, 25 failed before updating
`tests/test_cli.py::test_render_decomposition_lists_obligations_and_open_questions`
(it pinned the old bracket text, which the issue changes); after that edit the
remaining 24 failures are all in `tests/benchmark/test_corpus.py` and
`tests/benchmark/test_rating_regression.py`. I verified the same 24 fail on an
unmodified checkout of `origin/main` (`/tmp/main-checker`, 24 failed, 38 passed):
this clone is shallow and lacks the pinned corpus commits
(`UnresolvableRevisionError: ... revision '4d13ba1' ...`). Not caused by this change.
`ruff check .` and `ruff format --check .` pass.

## Check

`check.log`: verdict UNABLE-TO-DETERMINE. Points for the human:

- None of the three new tests was mapped to any obligation ("no mapped test" on
  obligations 1–4), though each test is named for exactly one obligation. The
  mapping step looks half-blind here.
- The three inverted exclusion-02 obligations (6–8) were all rated "addressed" —
  with "examined 8 changes ... none breaches this boundary" — for a boundary that
  is stated backwards. The checker therefore reported the report as changed when
  `report.py` was not touched.
- The `json-output-unchanged` defect injection removed the reason line from
  `_render_flat` and no test caught it. That is a real gap in my tests (the flat
  fallback's reason line is untested), though the defect was labelled as a JSON
  change, which it is not: `_render_flat` is text output.
- Unrequested-change item 3 calls changing `_render_flat` unrequested; I believe
  it is in scope, since the flat fallback is part of `decompose`'s text output.

## Deferred

### [2026-10-19] A scope exclusion "X is unchanged" decomposes into obligations that X changes
- **Kind:** filing
- **Found during:** #276, headless run
- **Where:** `src/acceptance/requirement/` (decomposition); see `dogfood-logs/276-headless/decompose.log`, requirement `exclusion-02`
- **Severity:** blocker
- **What's wrong:** The exclusion "The rendered review report is unchanged." yielded `review-report-not-unchanged` ("The rendered review report changes to reflect ...") plus two obligations demanding the report gain new lines. `check` then rated all three "addressed". An inverted exclusion turns a boundary into a demand, and the checker passed it.
- **Why I didn't act:** Out of scope for #276, and the fix is in decomposition prompts (no-go list).
- **Drafted fix:** File as a child of #181 (decomposition umbrella), title "A scope exclusion can decompose into its own negation", body quoting the requirement and the three obligations from `dogfood-logs/276-headless/decompose.log`, and the "addressed" ratings from `check.log` obligations 6–8.
- **Status:** open

### [2026-10-19] Tests named for an obligation are not mapped to it
- **Kind:** filing
- **Found during:** #276, headless run
- **Where:** `src/acceptance/evidence/mapping.py`; `dogfood-logs/276-headless/check.log`, obligations 1–4
- **Severity:** should-fix
- **What's wrong:** `test_the_cli_shows_each_obligations_required_evidence`, `test_the_cli_shows_the_reason_for_a_narrowed_required_evidence` and `test_the_cli_marks_an_obligation_satisfied_by_absence`, all added in the diff under review, were mapped to no obligation.
- **Why I didn't act:** Out of scope; mapping belongs to #182.
- **Drafted fix:** File as a child of #182 (test discovery & mapping umbrella), with the check.log excerpt and the head SHA in `revisions.txt`, asking first whether the new tests were discovered as candidates at all.
- **Status:** open

### [2026-10-19] The flat fallback's reason line in `decompose` output has no test
- **Kind:** defect
- **Found during:** #276, headless run (check's defect injection)
- **Where:** `src/acceptance/cli.py`, `_render_flat`
- **Severity:** nice-to-have
- **What's wrong:** Removing the `_required_evidence_reason` call from `_render_flat` fails no test. The orphan list's reason line and absence mark are likewise untested.
- **Why I didn't act:** The issue's acceptance asks for a test against a decomposition fixture, which the requirement-major tests satisfy; widening further was optional.
- **Drafted fix:** Extend `tests/test_cli.py::test_render_decomposition_lists_obligations_and_open_questions` with a narrowed, absence-satisfied obligation and assert its reason line and mark.
- **Status:** open
