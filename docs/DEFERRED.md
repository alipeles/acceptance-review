# The bundled queue

Things found mid-iteration that were deliberately not acted on at the time.
Claude queues here instead of interrupting; the queue is presented at the next
gate and worked with `/triage`. See `CLAUDE.md` *Working agreement* §4.

Resolved entries are deleted. Anything filed lives on GitHub, which is
authoritative (#168), so keeping a second copy here only costs context; an
entry resolved without a filing is recorded in the commit that resolved it.

Kind: `defect` (a bug, smell, missing test, spec inconsistency, dependency
problem, outside the current task's scope) · `filing` (a drafted issue,
sub-issue, or comment asserting a new finding — nothing reaches GitHub until
approved at a gate) · `decision` (an open design decision, with the
recommendation and the alternative rejected).

Severity: `blocker` (an Acceptance item of the task in flight depends on it) ·
`should-fix` (real defect, no Acceptance item blocked) ·
`nice-to-have` (cleanup, ergonomics, docs).

---

<!-- Template — copy, don't edit:

### [YYYY-MM-DD] <one-line title>
- **Kind:** defect | filing | decision
- **Found during:** #144, Gate 1
- **Where:** src/acceptance/requirement/obligations.py:118
- **Severity:** blocker | should-fix | nice-to-have
- **What's wrong:** one or two concrete sentences.
- **Why I didn't act:** out of scope for #144 / would change the review-state schema.
- **Drafted fix:** for a defect, what you would do — specific enough to approve or
  reject without a follow-up, with the diff sketch if it is small. For a filing, the
  issue body as it would be filed, its labels, and its parent umbrella.
- **Status:** open

-->

### [2026-08-10] A Completion expectation and its Constraint twin get unstable, mutually exclusive mappings
- **Kind:** filing
- **Found during:** #228, Gate 2 (runs 1 and 2)
- **Where:** `src/acceptance/evidence/mapping.py`
- **Severity:** blocker — it is why #228's Gate 2 cannot be made clean
- **What's wrong:** Where a Completion expectation ("A test asserts that X")
  sits alongside its Constraint twin ("X"), the mapping stage attaches the
  supporting tests to one or the other and not both, and which one it picks
  moves between runs. Whichever misses is then reported `unsupported / (no
  mapped test)` with a recommendation to write a test that already exists and is
  cited under the twin in the same report.
- **Why I didn't act:** there is nothing to fix in #228's code. The tests the
  tool asks for exist; adding duplicates to move a label is the "fix the output,
  not the wording" failure CLAUDE.md forbids.
- **Drafted fix:** file as a child of **#182**, labels `bug`, `track:checker`.

  > **Title:** Mapping splits a Completion expectation from its Constraint twin, unstably
  >
  > Child of #182. Cross-references #180 — same convergence failure, isolated here
  > to the mapping call with a self-contradiction that needs no cross-run comparison.
  >
  > ## One report contradicting itself
  >
  > `dogfood-logs/228-gate2-run2/output.log`. Obligation 3 (`completion-04`,
  > *"A test asserts that every case in the archetype corpus and every case in the
  > decomposition-regression corpus passes the check"*):
  >
  > ```
  > test evidence: unsupported  [tier: static]
  >   (no mapped test)
  >   recommended test: A test is added that iterates over both corpora and
  >   verifies each case passes the check.
  >   detects: The current tests may only exercise one corpus, or only a
  >   hand-picked subset.
  > ```
  >
  > Obligation 8 (`constraint-04`, *"The check covers every case in the archetype
  > corpus and every case in the decomposition-regression corpus"*), eighty lines
  > later in the same report:
  >
  > ```
  > test evidence: strongly supported  [tier: static]
  >   8.6  tests/…::test_every_archetype_task_file_yields_requirements
  >   8.7  tests/…::test_every_decompose_regression_task_file_yields_requirements
  > ```
  >
  > And unrequested change #5, same report, calls those tests surplus:
  >
  > > The new test file includes broad corpus-wide assertions that every archetype
  > > and every decompose-regression case yields requirements, plus a count check.
  >
  > The report says the tests do not exist, cites them as strong evidence, and
  > flags them as unnecessary extras.
  >
  > ## The instability, from the mapping transcripts
  >
  > Same tests, same obligation wording, two runs over the same branch:
  >
  > ```
  > run 1:  test_every_archetype_task_file_yields_requirements
  >           -> test-all-corpus-cases-pass-check, cover-all-corpus-cases
  > run 2:  test_every_archetype_task_file_yields_requirements
  >           -> check-covers-all-corpus-cases, does-not-determine-requirement-text
  >
  > run 1:  test_an_archetype_case_fails_before_it_materializes_a_repo
  >           -> test-build-performs-check-before-scoring, pre-score-check-before-build,
  >              error-instead-of-build-for-no-requirements
  > run 2:  test_an_archetype_case_fails_before_it_materializes_a_repo
  >           -> test-failure-uses-supplied-task-file
  > ```
  >
  > Run 2 drops the `test_demand` obligation in both cases, and for the archetype
  > test substitutes an unrelated **scope exclusion**
  > (`does-not-determine-requirement-text`) — a code-evidence-only obligation that
  > should attract no test mapping at all.
  >
  > Between the runs one test was added and none removed, and the wording of both
  > affected requirements is byte-identical.
  >
  > ## Why this blocks
  >
  > #228's Gate 2 named three obligations in run 1 and a **disjoint** two in run 2,
  > with the run-2 pair having been strongly supported in run 1. Every run-1
  > finding was real and was fixed. The gate still cannot be made clean, because
  > what it names is not stable under the fix.
  >
  > The mapping prompt tells the model a test may evidence multiple obligations and
  > that returning several ids is expected. It does that correctly for the
  > Constraint twin and not for the Completion one. The §7.1 task-file shape makes
  > this pairing the norm, not an edge case: Completion expectations routinely
  > restate Constraints in "A test asserts that…" form.
  >
  > ## Acceptance
  >
  > - A test mapped to a Constraint obligation is also mapped to the Completion
  >   expectation that demands a test of that same constraint, or the report
  >   explains why the two are distinct.
  > - No obligation is reported `unsupported / (no mapped test)` while a test cited
  >   under another obligation in the same report demonstrates it.
  > - A scope-exclusion obligation attracts no test mapping — it is
  >   code-evidence-only by construction (#153).
  > - Two runs over an unchanged branch produce the same obligation→test mapping,
  >   or the instability is measured and reported rather than silently changing a
  >   verdict.
  >
  > Evidence: `dogfood-logs/228-gate2-run1/` and `dogfood-logs/228-gate2-run2/`,
  > with the judgement in run 2.
  >
  > Related: #182, #180, #153, #164, #235.
- **Status:** open
