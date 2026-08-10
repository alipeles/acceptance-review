# Judgement — #228 Gate 2, run 1

**Outcome: INCOMPLETE. Three findings, all three real and all three addressed.**

> 1 obligation(s) not fully implemented (byte-identical-review-state);
> 2 obligation(s) with non-discriminating test evidence
> (test-fails-no-requirements-naming-case,
> benchmark-no-requirements-fails-naming-case).

## Mapping was sound — checked first, per DR-164

Before judging the findings: 105 mapped rows across the partitions, 48 with
empty `obligation_ids`, **16 of 17 obligations mapped**, and all 11 tests in the
new file seen and mapped sensibly. This was not a half-blind review.

## Finding 1 — `byte-identical-review-state`, code evidence *unclear*

**Real, and my authoring defect.** "Two runs over byte-identical task text
produce byte-identical review state" was a **Constraint**, and the tool
correctly reported `(no corresponding change)`. It is a standing invariant of
the system, not a requirement of this change; as a constraint it demanded work
this diff had no business doing.

**Disposition: fixed the task file.** Moved to Scope exclusions, where #153's
machinery renders it "The change does not alter whether…" and confirms it by
non-violation on code evidence alone. Confirmed in run 2, obligation 16.

## Finding 2 — `benchmark-no-requirements-fails-naming-case` (task-01), *unsupported*

**Real, and the sharpest finding of the run.** The task statement is "fails,
naming the case, **instead of being scored**". Ten tests asserted the first
half. **None asserted the second.** The recommendation named exactly what was
missing, including the part that makes it evidence:

> Include a control case with a non-empty registry to show ordinary scoring
> still works for valid inputs. […] assert the case object is not returned and
> no score is produced […] assert the test would fail if the code instead
> returned a BenchmarkCase with score=0.0 or similar.

That is a correct reading of a genuine hole. "No score was produced" proves
nothing without showing the harness would have produced one.

**Disposition: addressed.** Added
`test_an_unreadable_case_is_never_scored_while_a_readable_one_still_is`, which
takes a readable case through `decompose_case` to a real
`decomposition_accuracy` and then the same case with only its task text changed.
Verified by injection: with the guard short-circuited the subject fails and the
control still passes.

## Finding 3 — `test-fails-no-requirements-naming-case` (completion-02), *partially supported*

**Real.** Mapped only to `test_a_task_file_with_no_requirements_raises_naming_the_case`,
which calls the guard **directly** rather than through a builder. The
recommendation's stated defect — "the guard is never reached … because the
builder returns a case object" — is precisely what that test cannot detect.

**Disposition: addressed** by the same new test, which goes through
`build_decompose_case`. Strongly supported in run 2, obligation 1.

## Unrequested changes — 6, all correctly identified

Two `separable` ones are fair and were left as they are: the `obligations.py`
comment correction (documentation, deliberate) and the `session-state.md`
rewrite (process record, outside the mandate by construction). The four
`in_service` ones are accurate descriptions of deliberate choices.

## Nothing attributed to a tool defect in this run

All three findings were real gaps in my work. The tool was right three times.
