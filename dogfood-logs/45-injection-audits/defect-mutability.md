# Defect mutability — #45, head 518f876

71 defects enumerated. **39 mutable, 32 not.**

Mutability is decided without running any test: region resolution, the
descriptor call, then the five mechanical checks in `validity.py` — it
applies, it changes something, it is inside a region the defect named, it is
within the size bound, and the file still parses if it has a parser.

---

## not mutable — halted-baseline-prevents-any-test-run

- **criterion:** candidate-tests-run-once-before-changes
- **type:** `missing_case`
- **regions named:** 3
- **defect:** A halted baseline returns before mutation, but the criterion still requires the candidate tests to have been run once against the delivered code; if the halt path is taken without a prior run being guaranteed, the obligation is missed for that input.
- **why not:** the replacement for src/acceptance/mutation/baseline.py lines 151..152 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/mutation/baseline.py` lines 151-152

```diff
-    if not runnable:
-        return Baseline(set_aside=dropped)
+    if not runnable:
+        return Baseline(set_aside=dropped)
```

## not mutable — not-attempted-from-copy-failure-may-be-unexplained

- **criterion:** carry-reason-for-non-settlement
- **type:** `other`
- **regions named:** 2
- **defect:** If preparing the mutated copy fails, `_attempt` returns `NOT_ATTEMPTED` with an error string, but that reason comes from the filesystem exception rather than from the execution outcome itself; a reader checking the execution record would need to inspect whether this path always produces a meaningful non-settlement reason for every failure mode.
- **why not:** the replacement for src/acceptance/mutation/runner.py lines 173..179 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/mutation/runner.py` lines 173-179

```diff
-    except OSError as error:
-        return MutationAttempt(
-            defect_id=defect.id,
-            outcome=MutationOutcomeKind.NOT_ATTEMPTED,
-            descriptor=descriptor,
-            reason=f"the mutated copy could not be prepared: {error}",
-        )
+    except OSError as error:
+        return MutationAttempt(
+            defect_id=defect.id,
+            outcome=MutationOutcomeKind.NOT_ATTEMPTED,
+            descriptor=descriptor,
+            reason=f"the mutated copy could not be prepared: {error}",
+        )
```

## not mutable — failing-tests-still-count-in-support

- **criterion:** continue-with-set-aside-tests
- **type:** `other`
- **regions named:** 6
- **defect:** The executed verdicts are appended to the pair verdict list, but the support derivation still receives the full defect sets and may therefore let set-aside failing tests continue to influence the conclusion instead of being excluded from it.
- **why not:** the mutated src/acceptance/pipeline.py does not parse: unmatched ')' (<unknown>, line 495)

**edit** — `src/acceptance/pipeline.py` lines 480-481

```diff
-    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
-        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
+    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
+        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
+    )
+    defect_sets = [
+        defect_set.model_copy(
+            update={
+                "defects": [
+                    defect
+                    for defect in defect_set.defects
+                    if defect.id not in {attempt.defect_id for attempt in attempts if attempt.settled}
+                ]
+            }
+        )
+        for defect_set in defect_sets
+    ]
```

## not mutable — set-aside-tests-not-rendered

- **criterion:** continue-with-set-aside-tests
- **type:** `wrong_output_shape`
- **regions named:** 3
- **defect:** The report never renders the list of set-aside candidate tests, so a caller cannot identify which failing tests were excluded from the conclusion.
- **why not:** the replacement for src/acceptance/report.py lines 135..136 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/report.py` lines 135-136

```diff
-    if review.set_aside_tests:
-        lines.extend(_set_aside_block(review))
+    if review.set_aside_tests:
+        lines.extend(_set_aside_block(review))
```

## not mutable — not-attempted-defects-may-never-reach-reading-judgement

- **criterion:** execution-could-not-settle-defects
- **type:** `missing_case`
- **regions named:** 5
- **defect:** When the mutant cannot be prepared or the run is incomplete, the attempt is marked not_attempted, but the diff does not show a corresponding mechanism that guarantees every such defect is still carried into the code-reading judgement rather than being left without an execution-settled fallback.
- **why not:** the replacement for src/acceptance/mutation/runner.py lines 211..219 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/mutation/runner.py` lines 211-219

```diff
-    unobserved = [outcome for outcome in result.outcomes if not outcome.completed]
-    if unobserved:
-        return MutationAttempt(
-            defect_id=defect.id,
-            outcome=MutationOutcomeKind.NOT_ATTEMPTED,
-            descriptor=descriptor,
-            tests_run=tests,
-            reason=_why_unobserved(unobserved, result.outcomes),
-        )
+    unobserved = [outcome for outcome in result.outcomes if not outcome.completed]
+    if unobserved:
+        return MutationAttempt(
+            defect_id=defect.id,
+            outcome=MutationOutcomeKind.NOT_ATTEMPTED,
+            descriptor=descriptor,
+            tests_run=tests,
+            reason=_why_unobserved(unobserved, result.outcomes),
+        )
```

## not mutable — not-mutable-defects-stop-at-static-judge

- **criterion:** execution-could-not-settle-defects
- **type:** `missing_case`
- **regions named:** 5
- **defect:** Defects that cannot be expressed as one contiguous edit are returned as not_mutable and then removed from the execution path, but the code shown does not demonstrate any later static pair-judgement path that still reaches a conclusion for those defects specifically.
- **why not:** the replacement for src/acceptance/mutation/verdicts.py lines 71..98 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/mutation/verdicts.py` lines 71-98

```diff
-def remaining_defect_sets(
-    attempts: Sequence[MutationAttempt],
-    defect_sets: Sequence[DefectSet],
-) -> list[DefectSet]:
-    """`defect_sets` with every defect execution settled removed.
-
-    This is what the static pair judgement is given. A set left with no defects
-    is dropped entirely rather than passed on empty: `DefectSet` requires a
-    reason on an empty set, and one written here would claim the enumeration
-    found nothing plausible when in fact execution answered all of it.
-
-    The *full* sets still go to `derive_support`, so the denominator a criterion
-    is rated against is unchanged. Only the question put to the model shrinks.
-    """
-    settled = {attempt.defect_id for attempt in attempts if attempt.settled}
-    if not settled:
-        return list(defect_sets)
-
-    remaining: list[DefectSet] = []
-    for defect_set in defect_sets:
-        keep = [defect for defect in defect_set.defects if defect.id not in settled]
-        if not keep:
-            continue
-        if len(keep) == len(defect_set.defects):
-            remaining.append(defect_set)
-            continue
-        remaining.append(defect_set.model_copy(update={"defects": keep}))
-    return remaining
+def remaining_defect_sets(
+    attempts: Sequence[MutationAttempt],
+    defect_sets: Sequence[DefectSet],
+) -> list[DefectSet]:
+    """`defect_sets` with every defect execution settled removed.
+
+    This is what the static pair judgement is given. A set left with no defects
+    is dropped entirely rather than passed on empty: `DefectSet` requires a
+    reason on an empty set, and one written here would claim the enumeration
+    found nothing plausible when in fact execution answered all of it.
+
+    The *full* sets still go to `derive_support`, so the denominator a criterion
+    is rated against is unchanged. Only the question put to the model shrinks.
+    """
+    settled = {attempt.defect_id for attempt in attempts if attempt.settled}
+    if not settled:
+        return list(defect_sets)
+
+    remaining: list[DefectSet] = []
+    for defect_set in defect_sets:
+        keep = [defect for defect in defect_set.defects if defect.id not in settled]
+        if not keep:
+            continue
+        if len(keep) == len(defect_set.defects):
+            remaining.append(defect_set)
+            continue
+        remaining.append(defect_set.model_copy(update={"defects": keep}))
+    return remaining
```

## not mutable — containment-check-only-looks-at-resolved-regions

- **criterion:** mechanical-validity-checks
- **type:** `scope_too_narrow`
- **regions named:** 2
- **defect:** The containment check only considers regions that were resolved from the current change set; if a defect names no region in the edited file, the code reports it as not mutable rather than mechanically validating the edit against that obligation.
- **why not:** the replacement for src/acceptance/mutation/validity.py lines 133..138 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/mutation/validity.py` lines 133-138

```diff
-    named = [region for region in regions if region.path == descriptor.path]
-    if not named:
-        return (
-            f"the defect names no region in {descriptor.path}, so an edit there could not be "
-            "credited to it"
-        )
+    named = [region for region in regions if region.path == descriptor.path]
+    if not named:
+        return (
+            f"the defect names no region in {descriptor.path}, so an edit there could not be "
+            "credited to it"
+        )
```

## not mutable — parse-check-still-applies-to-all-mutants

- **criterion:** mechanical-validity-checks
- **type:** `scope_too_narrow`
- **regions named:** 1
- **defect:** The new validity gate still rejects mutants by parsing the edited file for Python and JSON only, so edits to other file types can slip through without any mechanical parse check at all.
- **why not:** the replacement for src/acceptance/mutation/validity.py lines 40..56 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/mutation/validity.py` lines 40-56

```diff
-#: Extensions whose files are parsed after the edit. A file whose extension is
-#: not here is left to the other three checks, and that is the revision's point:
-#: a missing parser is not a defect in the file.
-#:
-#: **It is a list of parsers we have, not a claim about which files are
-#: parseable.** Gate 2 of #45 found the gap that distinction hides — with only
-#: Python here, a mutated `.json` passed validity however malformed it was,
-#: while the requirement is that a file *that has a parser* still parses. Any
-#: format the checker can parse without a new dependency belongs here.
-#:
-#: `tomllib` is deliberately absent: it arrives in Python 3.11 and this project
-#: runs 3.10, so adding it would be a parse check that silently does nothing.
-_PARSERS = {
-    ".py": ast.parse,
-    ".pyi": ast.parse,
-    ".json": json.loads,
-}
+#: Extensions whose files are parsed after the edit. A file whose extension is
+#: not here is left to the other three checks, and that is the revision's point:
+#: a missing parser is not a defect in the file.
+#:
+#: **It is a list of parsers we have, not a claim about which files are
+#: parseable.** Gate 2 of #45 found the gap that distinction hides — with only
+#: Python here, a mutated `.json` passed validity however malformed it was,
+#: while the requirement is that a file *that has a parser* still parses. Any
+#: format the checker can parse without a new dependency belongs here.
+#:
+#: `tomllib` is deliberately absent: it arrives in Python 3.11 and this project
+#: runs 3.10, so adding it would be a parse check that silently does nothing.
+_PARSERS = {
+    ".py": ast.parse,
+    ".pyi": ast.parse,
+    ".json": json.loads,
+}
```

## not mutable — missing-no-region-report

- **criterion:** no-edit-without-named-region
- **type:** `other`
- **regions named:** 3
- **defect:** A defect with no named region is treated as not_mutable in the mutation runner, but the review/reporting path never surfaces that specific fact as an observable report that the defect cannot be edited.
- **why not:** the replacement for src/acceptance/report.py lines 131..133 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/report.py` lines 131-133

```diff
-    if review.mutation_attempts:
-        lines.extend(_mutation_block(review))
-        lines.append("")
+    if review.mutation_attempts:
+        lines.extend(_mutation_block(review))
+        lines.append("")
```

## not mutable — no-region-defects-silently-dropped

- **criterion:** no-edit-without-named-region
- **type:** `other`
- **regions named:** 3
- **defect:** When a defect has no resolved regions, the descriptor builder skips asking about it and returns None, but the surrounding pipeline could still end up with no explicit record that this defect was uneditable rather than merely unattempted.
- **why not:** the replacement for src/acceptance/pipeline.py lines 310..313 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/pipeline.py` lines 310-313

```diff
-    defects = [defect for defect_set in defect_sets for defect in defect_set.defects]
-    regions_by_defect = {defect.id: regions_for(defect, change_set) for defect in defects}
-    sources = _sources_for(regions_by_defect, repo)
-    descriptors = build_descriptors(defects, regions_by_defect, sources, client, unusable)
+    defects = [defect for defect_set in defect_sets for defect in defect_set.defects]
+    regions_by_defect = {defect.id: regions_for(defect, change_set) for defect in defects}
+    sources = _sources_for(regions_by_defect, repo)
+    descriptors = build_descriptors(defects, regions_by_defect, sources, client, unusable)
```

## not mutable — report-could-expose-executed-lines

- **criterion:** no-line-execution-recording
- **type:** `other`
- **regions named:** 5
- **defect:** The report now renders mutation attempts and set-aside tests, so if any line-execution details were attached to those records elsewhere in the pipeline, this output path would surface them; the diff does not show a dedicated guard against recording executed line numbers.
- **why not:** the edit replaces 34 lines, over the 12-line bound; the smallest edit that makes the defect true is what was asked for

**edit** — `src/acceptance/report.py` lines 270-303

```diff
-def _mutation_block(review: Review) -> list[str]:
-    """What was injected, and what each test did about it (M8.4).
-
-    The injected text is rendered, not summarised, and that is the point.
-    DR-171 Decision 3 spends no model call confirming that a mutant really
-    violates the obligation — it would be judging its own output at the tier it
-    is checking. Showing exactly what was injected is the whole of what replaces
-    that: a reader who thinks a survival is unfair can see the edit and say so.
-
-    A defect execution could not settle renders with its reason. Those went to
-    the static judge, and a reader comparing a criterion's executed and
-    predicted parts needs to know which is which.
-    """
-    lines = ["Defects injected, and which tests caught them:"]
-    for attempt in review.mutation_attempts:
-        lines.append("")
-        lines.append(f"  [{attempt.outcome.value}] {attempt.defect_id}")
-        descriptor = attempt.descriptor
-        if descriptor is not None:
-            span = f"{descriptor.start_line}-{descriptor.end_line}"
-            lines.append(f"    injected at {descriptor.path} lines {span}:")
-            for line in descriptor.replacement.splitlines() or [""]:
-                lines.append(f"      | {line}")
-        if attempt.killing_tests:
-            lines.append(f"    caught by ({len(attempt.killing_tests)}):")
-            lines.extend(f"      {test_id}" for test_id in attempt.killing_tests)
-        elif attempt.settled:
-            lines.append(
-                f"    no test caught it; {len(attempt.tests_run)} candidate test(s) ran "
-                "and none failed"
-            )
-        if attempt.reason:
-            lines.append(f"    {attempt.reason}")
-    return lines
+def _mutation_block(review: Review) -> list[str]:
+    """What was injected, and what each test did about it (M8.4).
+
+    The injected text is rendered, not summarised, and that is the point.
+    DR-171 Decision 3 spends no model call confirming that a mutant really
+    violates the obligation — it would be judging its own output at the tier it
+    is checking. Showing exactly what was injected is the whole of what replaces
+    that: a reader who thinks a survival is unfair can see the edit and say so.
+
+    A defect execution could not settle renders with its reason. Those went to
+    the static judge, and a reader comparing a criterion's executed and
+    predicted parts needs to know which is which.
+    """
+    lines = ["Defects injected, and which tests caught them:"]
+    for attempt in review.mutation_attempts:
+        lines.append("")
+        lines.append(f"  [{attempt.outcome.value}] {attempt.defect_id}")
+        descriptor = attempt.descriptor
+        if descriptor is not None:
+            span = f"{descriptor.start_line}-{descriptor.end_line}"
+            lines.append(f"    injected at {descriptor.path} lines {span}:")
+            for line in descriptor.replacement.splitlines() or [""]:
+                lines.append(f"      | {line}")
+        if attempt.killing_tests:
+            lines.append(f"    caught by ({len(attempt.killing_tests)}):")
+            lines.extend(f"      {test_id}" for test_id in attempt.killing_tests)
+        elif attempt.settled:
+            lines.append(
+                f"    no test caught it; {len(attempt.tests_run)} candidate test(s) ran "
+                "and none failed"
+            )
+        if attempt.reason:
+            lines.append(f"    {attempt.reason}")
+        if attempt.executed_lines:
+            lines.append(f"    executed lines: {len(attempt.executed_lines)}")
+    return lines
```

## not mutable — parser-check-still-applies-to-nonparsed-files

- **criterion:** no-parser-not-invalid
- **type:** `other`
- **regions named:** 1
- **defect:** The validity check still rejects a mutant for a file type that has no parser, so a documentation or other non-parsed file can be marked not_mutable just because it cannot be parsed.
- **why not:** the replacement for src/acceptance/mutation/validity.py lines 52..56 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/mutation/validity.py` lines 52-56

```diff
-_PARSERS = {
-    ".py": ast.parse,
-    ".pyi": ast.parse,
-    ".json": json.loads,
-}
+_PARSERS = {
+    ".py": ast.parse,
+    ".pyi": ast.parse,
+    ".json": json.loads,
+}
```

## not mutable — parser-map-misses-supported-file-types

- **criterion:** no-parser-not-invalid
- **type:** `scope_too_narrow`
- **regions named:** 1
- **defect:** The parser lookup only recognizes .py, .pyi, and .json, so any other file type that actually has a parser in this project would still be treated as having none and could be rejected for the wrong reason.
- **why not:** the replacement for src/acceptance/mutation/validity.py lines 52..56 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/mutation/validity.py` lines 52-56

```diff
-_PARSERS = {
-    ".py": ast.parse,
-    ".pyi": ast.parse,
-    ".json": json.loads,
-}
+_PARSERS = {
+    ".py": ast.parse,
+    ".pyi": ast.parse,
+    ".json": json.loads,
+}
```

## not mutable — execution-tier-runs-whole-suite

- **criterion:** no-whole-suite-run
- **type:** `other`
- **regions named:** 4
- **defect:** The new execution tier calls the project's test runner with the full candidate test list, and if that list is the whole suite then the implementation will execute the whole suite instead of avoiding it.
- **why not:** the replacement for src/acceptance/pipeline.py lines 315..323 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/pipeline.py` lines 315-323

```diff
-    attempts = run_mutations(
-        defect_sets,
-        change_set,
-        repo,
-        baseline,
-        from_mapping(descriptors),
-        execution.sandbox,
-        execution.max_edit_lines,
-    )
+    attempts = run_mutations(
+        defect_sets,
+        change_set,
+        repo,
+        baseline,
+        from_mapping(descriptors),
+        execution.sandbox,
+        execution.max_edit_lines,
+    )
```

## not mutable — executed-result-not-stored-as-conclusion

- **criterion:** observation-not-prediction
- **type:** `other`
- **regions named:** 4
- **defect:** The execution tier records attempts and verdicts, but nothing in the changed code shows the final stored conclusion being rewritten to the observed run result instead of leaving the old predicted conclusion in place, so the review can still conclude with a forecast.
- **why not:** the replacement for src/acceptance/review_state.py lines 1269..1270 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/review_state.py` lines 1269-1270

```diff
-    findings: list[Finding] = Field(default_factory=list)
-    recommendations: list[TestRecommendation] = Field(default_factory=list)
+    findings: list[Finding] = Field(default_factory=list)
+    recommendations: list[TestRecommendation] = Field(default_factory=list)
```

## not mutable — json-parser-missing-from-validity-check

- **criterion:** parser-files-still-parse
- **type:** `scope_too_narrow`
- **regions named:** 1
- **defect:** The validity check only parses .py and .pyi files, so a mutated .json file can be accepted even when it no longer parses.
- **why not:** the edit replaces 17 lines, over the 12-line bound; the smallest edit that makes the defect true is what was asked for

**edit** — `src/acceptance/mutation/validity.py` lines 40-56

```diff
-#: Extensions whose files are parsed after the edit. A file whose extension is
-#: not here is left to the other three checks, and that is the revision's point:
-#: a missing parser is not a defect in the file.
-#:
-#: **It is a list of parsers we have, not a claim about which files are
-#: parseable.** Gate 2 of #45 found the gap that distinction hides — with only
-#: Python here, a mutated `.json` passed validity however malformed it was,
-#: while the requirement is that a file *that has a parser* still parses. Any
-#: format the checker can parse without a new dependency belongs here.
-#:
-#: `tomllib` is deliberately absent: it arrives in Python 3.11 and this project
-#: runs 3.10, so adding it would be a parse check that silently does nothing.
-_PARSERS = {
-    ".py": ast.parse,
-    ".pyi": ast.parse,
-    ".json": json.loads,
-}
+#: Extensions whose files are parsed after the edit. A file whose extension is
+#: not here is left to the other three checks, and that is the revision's point:
+#: a missing parser is not a defect in the file.
+#:
+#: **It is a list of parsers we have, not a claim about which files are
+#: parseable.** Gate 2 of #45 found the gap that distinction hides — with only
+#: Python here, a mutated `.json` passed validity however malformed it was,
+#: while the requirement is that a file *that has a parser* still parses. Any
+#: format the checker can parse without a new dependency belongs here.
+#:
+#: `tomllib` is deliberately absent: it arrives in Python 3.11 and this project
+#: runs 3.10, so adding it would be a parse check that silently does nothing.
+_PARSERS = {
+    ".py": ast.parse,
+    ".pyi": ast.parse,
+}
```

## not mutable — stored-reviews-drop-static-judgement-context

- **criterion:** preserve-code-reading-judgement
- **type:** `stored_form_unreadable`
- **regions named:** 3
- **defect:** The review model now stores `mutation_attempts`, `set_aside_tests`, and a mixed-tier `pair_verdicts`, but the diff does not show any compatibility layer for older stored reviews that only have the previous static judgement shape. If downstream reading expects the old code-reading judgement fields or assumes all verdicts are static, previously written reviews may no longer round-trip cleanly.
- **why not:** the edit replaces 18 lines, over the 12-line bound; the smallest edit that makes the defect true is what was asked for

**edit** — `src/acceptance/review_state.py` lines 1251-1268

```diff
-    pair_verdicts: list[PairVerdict] = Field(default_factory=list)
-    unjudged_pairs: list[UnjudgedPair] = Field(default_factory=list)
-    # One entry per defect the mutation stage was asked about (M8.4), holding the
-    # edit that was injected and what became of it. Empty on every review that
-    # did not run the tests, which is every review until the caller opts in.
-    #
-    # The injected text is here because DR-171 Decision 3 refuses to spend a
-    # second model call confirming that the mutant really violates the
-    # obligation — it would be judging its own output at the same tier as the
-    # thing it checks. Recording exactly what was injected is the whole of what
-    # replaces that, so a reader can disagree with a survival. Weaker than a
-    # proof, and honest about being weaker.
-    mutation_attempts: list[MutationAttempt] = Field(default_factory=list)
-    # Candidate tests that took no part in any conclusion, and why. A test that
-    # failed against the code as delivered tells nothing when it fails under an
-    # injected defect, so it is excluded — and an exclusion nobody can see is
-    # indistinguishable from a test that was never a candidate.
-    set_aside_tests: list[SetAsideTest] = Field(default_factory=list)
+    pair_verdicts: list[PairVerdict] = Field(default_factory=list)
+    unjudged_pairs: list[UnjudgedPair] = Field(default_factory=list)
+    mutation_attempts: list[MutationAttempt] = Field(default_factory=list)
+    set_aside_tests: list[SetAsideTest] = Field(default_factory=list)
```

## not mutable — halted-baseline-drops-usable-tests-too-broadly

- **criterion:** preserve-current-review-conclusions-when-unrunnable
- **type:** `scope_too_narrow`
- **regions named:** 4
- **defect:** A failing candidate test at head halts the review even when the operator opted to allow failing tests, so some unrunnable-or-parked cases do not preserve the current review conclusions.
- **why not:** the replacement for src/acceptance/mutation/baseline.py lines 100..104 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/mutation/baseline.py` lines 100-104

```diff
-        if self.halted and self.usable_tests:
-            raise ValueError(
-                "a halted baseline offers usable tests, which would let injection run "
-                "against a control the review already rejected"
-            )
+        if self.halted and self.usable_tests:
+            raise ValueError(
+                "a halted baseline offers usable tests, which would let injection run "
+                "against a control the review already rejected"
+            )
```

## not mutable — mutation-verdicts-not-carried-into-support-on-unrunnable-path

- **criterion:** preserve-current-review-conclusions-when-unrunnable
- **type:** `unenforced_on_one_path`
- **regions named:** 9
- **defect:** The review can still run the static pair judgement on the full defect sets when execution is disabled or cannot settle a defect, but the derived support and stored review conclusions may ignore the executed verdict tier on that path, so unrunnable cases can produce different conclusions from today.
- **why not:** the mutated src/acceptance/defects/support.py does not parse: unmatched ')' (<unknown>, line 285)

**edit** — `src/acceptance/defects/support.py` lines 277-279

```diff
-    return min(
-        (tier_by_defect.get(defect.id, EvidenceTier.STATIC) for defect in defect_set.defects),
-        default=EvidenceTier.STATIC,
+    return min(
+        (
+            tier_by_defect.get(defect.id, EvidenceTier.STATIC)
+            for defect in defect_set.defects
+            if defect.id in tier_by_defect
+        ),
+        default=EvidenceTier.STATIC,
+    )
```

## not mutable — review-records-weakest-tier-instead-of-strongest

- **criterion:** recorded-at-strongest-evidence-tier
- **type:** `condition_inverted`
- **regions named:** 5
- **defect:** The review state is populated from the weakest evidence tier among the verdicts it rests on, so a review that includes any executed `DEFECT_KILLED` evidence can still be recorded as `STATIC` instead of at the strongest tier it produces on its own.
- **why not:** the mutated src/acceptance/defects/support.py does not parse: unmatched ')' (<unknown>, line 281)

**edit** — `src/acceptance/defects/support.py` lines 277-279

```diff
-    return min(
-        (tier_by_defect.get(defect.id, EvidenceTier.STATIC) for defect in defect_set.defects),
-        default=EvidenceTier.STATIC,
+    return max(
+        (tier_by_defect.get(defect.id, EvidenceTier.STATIC) for defect in defect_set.defects),
+        default=EvidenceTier.STATIC,
+    )
```

## not mutable — not-attempted-mutants-never-run-tests

- **criterion:** run-candidate-tests-on-altered-copy
- **type:** `missing_case`
- **regions named:** 1
- **defect:** When a defect is judged not_mutable or not_attempted, the runner returns before copying the project and before calling run_tests, so those defects never get candidate tests executed against an altered copy.
- **why not:** the replacement for src/acceptance/mutation/runner.py lines 158..168 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/mutation/runner.py` lines 158-168

```diff
-    descriptor = build_descriptor(defect, readable, sources)
-    if descriptor is None:
-        return _not_mutable(
-            defect, "no single contiguous edit was found that would make this defect true"
-        )
-
-    reason = invalidity_reason(
-        descriptor, readable, sources.get(descriptor.path, ""), max_edit_lines
-    )
-    if reason is not None:
-        return _not_mutable(defect, reason)
+    descriptor = build_descriptor(defect, readable, sources)
+    if descriptor is None:
+        return _not_mutable(
+            defect, "no single contiguous edit was found that would make this defect true"
+        )
+
+    reason = invalidity_reason(
+        descriptor, readable, sources.get(descriptor.path, ""), max_edit_lines
+    )
+    if reason is not None:
+        return _not_mutable(defect, reason)
```

## not mutable — descriptor-allows-multi-span-edit

- **criterion:** single-continuous-edit-in-named-region
- **type:** `other`
- **regions named:** 3
- **defect:** The mutation descriptor path can still describe an edit that is not a single continuous stretch in one file, so the injected change could be assembled from multiple disjoint spans instead of one contiguous patch.
- **why not:** the replacement for src/acceptance/mutation/descriptor.py lines 11..15 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/mutation/descriptor.py` lines 11-15

```diff
-The response shape is Decision 2's: a region label, an inclusive line span, and
-the replacement text. `region_label` is narrowed to this defect's own regions
-before the call, so an edit outside them is unrepresentable rather than merely
-refused afterwards — the containment check in `validity.py` still runs, because
-the line span inside a named region can still fall outside it.
+The response shape is Decision 2's: a region label, an inclusive line span, and
+the replacement text. `region_label` is narrowed to this defect's own regions
+before the call, so an edit outside them is unrepresentable rather than merely
+refused afterwards — the containment check in `validity.py` still runs, because
+the line span inside a named region can still fall outside it.
```

## not mutable — descriptor-declines-when-edit-exists

- **criterion:** smallest-edit-that-makes-defect-true
- **type:** `missing_case`
- **regions named:** 3
- **defect:** A defect that does have a valid single-span edit can still be classified as not_mutable if the descriptor call returns an empty region label or the runner rejects the descriptor too aggressively, so the review may skip building an edit even though one exists.
- **why not:** the replacement for src/acceptance/mutation/descriptor.py lines 200..201 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/mutation/descriptor.py` lines 200-201

```diff
-    if not label:
-        return None
+    if not label:
+        return None
```

## not mutable — mutation-copy-applies-edit-to-wrong-file

- **criterion:** smallest-edit-that-makes-defect-true
- **type:** `other`
- **regions named:** 3
- **defect:** The injected edit could be applied to the wrong file if descriptor.path does not match the intended region or if the copy step targets the wrong path, so the throwaway copy would not contain the smallest edit for the named defect.
- **why not:** the replacement for src/acceptance/mutation/runner.py lines 164..166 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/mutation/runner.py` lines 164-166

```diff
-    reason = invalidity_reason(
-        descriptor, readable, sources.get(descriptor.path, ""), max_edit_lines
-    )
+    reason = invalidity_reason(
+        descriptor, readable, sources.get(descriptor.path, ""), max_edit_lines
+    )
```

## not mutable — halt-message-loses-failing-test-reasons

- **criterion:** stop-review-on-failing-candidate-test
- **type:** `wrong_output_shape`
- **regions named:** 2
- **defect:** The CLI prints only the failing test ids and a generic re-run hint when the review halts; if the criterion expects the emitted stopping reason to include the actual failure reason from the candidate test run, this output shape omits it.
- **why not:** the mutated src/acceptance/cli.py does not parse: unmatched ')' (<unknown>, line 970)

**edit** — `src/acceptance/cli.py` lines 965-969

```diff
-            for test in exc.baseline.failing_tests:
-                print(f"  failing at head: {test.test_id}", file=sys.stderr)
-            print(
-                "  re-run with --allow-failing-tests to proceed with these set aside.",
-                file=sys.stderr,
+            for test in exc.baseline.failing_tests:
+                print(
+                    f"  failing at head: {test.test_id} ({test.reason})",
+                    file=sys.stderr,
+                )
```

## not mutable — executed-verdicts-may-not-reach-discrimination-record

- **criterion:** test-fails-discriminate-defect
- **type:** `not_wired`
- **regions named:** 5
- **defect:** The execution tier builds `executed_verdicts`, but the review only records discrimination if those verdicts are actually threaded into the same structures the rest of the pipeline uses; if any caller path bypasses `_run_execution_tier` or drops `executed_verdicts` before persistence, a failing test would not be shown as discriminating for the defect.
- **why not:** the replacement for src/acceptance/pipeline.py lines 480..482 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/pipeline.py` lines 480-482

```diff
-    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
-        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
-    )
+    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
+        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
+    )
```

## not mutable — failing-tests-not-marked-as-discriminating

- **criterion:** test-fails-discriminate-defect
- **type:** `other`
- **regions named:** 4
- **defect:** When a candidate test fails against the altered copy, the execution verdict is recorded with `kills=True` and `tier=DEFECT_KILLED`, but the code never explicitly marks the corresponding review finding or pair verdict as 'discriminates for that defect'; if the downstream review/reporting path only treats `kills` as a generic failure signal, the review could omit the discrimination claim the criterion asks for.
- **why not:** the mutated src/acceptance/mutation/verdicts.py does not parse: unindent does not match any outer indentation level (<unknown>, line 66)

**edit** — `src/acceptance/mutation/verdicts.py` lines 58-66

```diff
-            verdicts.append(
-                PairVerdict(
-                    defect_id=attempt.defect_id,
-                    test_id=test_id,
-                    kills=test_id in killing,
-                    reason=_reason(attempt, kills=test_id in killing),
-                    tier=EvidenceTier.DEFECT_KILLED,
-                    defect_text=texts.get(attempt.defect_id, ""),
-                )
+                PairVerdict(
+                    defect_id=attempt.defect_id,
+                    test_id=test_id,
+                    kills=test_id in killing,
+                    reason=_reason(attempt, kills=test_id in killing),
+                    tier=EvidenceTier.DEFECT_KILLED,
+                    defect_text=texts.get(attempt.defect_id, ""),
+                )
```

## not mutable — survival-path-only-records-failures

- **criterion:** test-fails-discriminate-defect
- **type:** `scope_too_narrow`
- **regions named:** 3
- **defect:** `verdicts_from` emits verdicts only for settled attempts, so if a mutant is classified as `NOT_ATTEMPTED` because some tests did not complete, any failing candidate test from that run is not recorded as discriminating for the defect even though the criterion is about a test that fails against the altered copy.
- **why not:** the mutated src/acceptance/mutation/verdicts.py does not parse: expected an indented block after 'for' statement on line 55 (<unknown>, line 56)

**edit** — `src/acceptance/mutation/verdicts.py` lines 53-55

```diff
-    for attempt in attempts:
-        if not attempt.settled:
-            continue
+    for attempt in attempts:
+        killing = set(attempt.killing_tests)
+        for test_id in attempt.tests_run:
```

## not mutable — execution-tier-alters-candidate-selection

- **criterion:** tests-candidate-selection
- **type:** `other`
- **regions named:** 3
- **defect:** The new execution tier changes which tests are treated as candidates by filtering the mutation run to `baseline.usable_tests` instead of the full discovered test list, so tests that fail at head are removed from later consideration rather than merely being reported separately.
- **why not:** the mutated src/acceptance/mutation/runner.py does not parse: unexpected indent (<unknown>, line 123)

**edit** — `src/acceptance/mutation/runner.py` lines 110-120

```diff
-    attempts = map_calls(
-        defects,
-        lambda defect: _attempt(
-            defect,
-            change_set,
-            project_root,
-            baseline.usable_tests,
-            build_descriptor,
-            config,
-            max_edit_lines,
-        ),
+    attempts = map_calls(
+        defects,
+        lambda defect: _attempt(
+            defect,
+            change_set,
+            project_root,
+            baseline.usable_tests,
+            build_descriptor,
+            config,
+            max_edit_lines,
+        ),
+        max_in_flight=max(1, max_in_flight),
+    )
```

## not mutable — achieved-tier-stays-static

- **criterion:** weaker-tier-evidence
- **type:** `scope_too_narrow`
- **regions named:** 3
- **defect:** The derived support record still writes `achieved_evidence_tier` as `STATIC` instead of using the weakest tier from the verdicts it rests on, so reviews that include executed verdicts are recorded at the wrong tier.
- **why not:** the replacement for src/acceptance/defects/support.py lines 320..324 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/defects/support.py` lines 320-324

```diff
-                    # Derived rather than hardcoded since DR-171 Decision 7: a
-                    # criterion every one of whose defects was settled by
-                    # injection reaches `DEFECT_KILLED`, and one with a single
-                    # predicted defect stays `STATIC`.
-                    "achieved_evidence_tier": result.achieved_tier,
+                    # Derived rather than hardcoded since DR-171 Decision 7: a
+                    # criterion every one of whose defects was settled by
+                    # injection reaches `DEFECT_KILLED`, and one with a single
+                    # predicted defect stays `STATIC`.
+                    "achieved_evidence_tier": result.achieved_tier,
```

## not mutable — execution-tier-not-included-in-rating-input

- **criterion:** weaker-tier-evidence
- **type:** `not_wired`
- **regions named:** 3
- **defect:** The execution tier may run and produce attempts, but if those executed verdicts are not merged into the verdict list passed to `derive_support`, the rating still reflects only static pair judgments and never records the weaker tier from execution.
- **why not:** the replacement for src/acceptance/pipeline.py lines 506..512 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/pipeline.py` lines 506-512

```diff
-    # past would make the benchmark's own runs leave ledger entries behind.
-    #
-    # Handed back HERE rather than after enumeration, which is where it used to
-    # sit, because the entry now carries the pair verdicts as well and they do
-    # not exist until the line above. One hand-back, so a caller cannot write an
-    # entry holding half of what the run produced — the same reason it moved off
-    # linking when #313 added the defect sets.
+    # past would make the benchmark's own runs leave ledger entries behind.
+    #
+    # Handed back HERE rather than after enumeration, which is where it used to
+    # sit, because the entry now carries the pair verdicts as well and they do
+    # not exist until the line above. One hand-back, so a caller cannot write an
+    # entry holding half of what the run produced — the same reason it moved off
+    # linking when #313 added the defect sets.
```

## not mutable — review-model-does-not-persist-mutation-evidence

- **criterion:** weaker-tier-evidence
- **type:** `not_wired`
- **regions named:** 2
- **defect:** The `Review` model has fields for mutation attempts and set-aside tests, but if the pipeline never populates them on the delivered path, the stored review cannot record the weaker evidence tier even when execution ran.
- **why not:** the replacement for src/acceptance/pipeline.py lines 640..647 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/pipeline.py` lines 640-647

```diff
-    return Review(
-        mode="local",
-        reviewed_revision=reviewed_revision,
-        task_source=task_source_for(task_text, task_identifier),
-        delta=delta,
-        # Stamped here, at the end, rather than accepted from the caller: only
-        # after the calls have run does the client know which determinism
-        # controls the provider honoured (#160).
+    return Review(
+        mode="local",
+        reviewed_revision=reviewed_revision,
+        task_source=task_source_for(task_text, task_identifier),
+        delta=delta,
+        # Stamped here, at the end, rather than accepted from the caller: only
+        # after the calls have run does the client know which determinism
+        # controls the provider honoured (#160).
```

## MUTABLE — executed-verdicts-not-marked-as-non-discriminating-in-support

- **criterion:** candidate-tests-not-discriminate-when-none-fail
- **type:** `wrong_output_shape`
- **regions named:** 6
- **defect:** Executed verdicts are stored with `tier=DEFECT_KILLED`, but the support derivation only records the weakest tier and never emits a distinct non-discrimination shape for the no-fail case, so downstream consumers cannot tell from the stored verdicts alone that the candidate tests did not discriminate.

**edit** — `src/acceptance/defects/support.py` lines 269-280

```diff
-def _achieved_tier(defect_set: DefectSet, tier_by_defect: dict[str, EvidenceTier]) -> EvidenceTier:
-    """The weakest tier among the verdicts this criterion's rating rests on.
-
-    A defect with no verdict at all counts as `STATIC` rather than being
-    skipped. It is the least-known case of all, and letting it drop out would
-    let a criterion whose only *answered* defect was executed claim
-    `DEFECT_KILLED` while the rest of its denominator was never looked at.
-    """
-    return min(
-        (tier_by_defect.get(defect.id, EvidenceTier.STATIC) for defect in defect_set.defects),
-        default=EvidenceTier.STATIC,
-    )
+def _achieved_tier(defect_set: DefectSet, tier_by_defect: dict[str, EvidenceTier]) -> EvidenceTier:
+    """The weakest tier among the verdicts this criterion's rating rests on.
+
+    A defect with no verdict at all counts as `STATIC` rather than being
+    skipped. It is the least-known case of all, and letting it drop out would
+    let a criterion whose only *answered* defect was executed claim
+    `DEFECT_KILLED` while the rest of its denominator was never looked at.
+    """
+    return min(
+        (tier_by_defect.get(defect.id, EvidenceTier.DEFECT_KILLED) for defect in defect_set.defects),
+        default=EvidenceTier.STATIC,
+    )
```

## MUTABLE — no-discrimination-report-when-execution-finds-no-kills

- **criterion:** candidate-tests-not-discriminate-when-none-fail
- **type:** `missing_case`
- **regions named:** 4
- **defect:** When execution runs and every candidate test passes against every injected mutant, the pipeline still only appends the executed verdicts and derived support; there is no explicit finding or report text that says the candidate tests do not discriminate for the defect in that no-fail case.

**edit** — `src/acceptance/report.py` lines 296-300

```diff
-        elif attempt.settled:
-            lines.append(
-                f"    no test caught it; {len(attempt.tests_run)} candidate test(s) ran "
-                "and none failed"
-            )
+        elif attempt.settled:
+            lines.append(
+                f"    no test caught it; {len(attempt.tests_run)} candidate test(s) ran "
+                "and none failed; candidate tests do not discriminate"
+            )
```

## MUTABLE — survival-with-partially-observed-run-treated-as-no-discrimination

- **criterion:** candidate-tests-not-discriminate-when-none-fail
- **type:** `scope_too_narrow`
- **regions named:** 1
- **defect:** A mutant run with no failing tests but with some tests not completed is classified as `not_attempted` instead of a non-discrimination result, so the criterion is only handled for fully observed no-fail runs and not for all no-fail executions the criterion could cover.

**edit** — `src/acceptance/mutation/runner.py` lines 211-219

```diff
-    unobserved = [outcome for outcome in result.outcomes if not outcome.completed]
-    if unobserved:
-        return MutationAttempt(
-            defect_id=defect.id,
-            outcome=MutationOutcomeKind.NOT_ATTEMPTED,
-            descriptor=descriptor,
-            tests_run=tests,
-            reason=_why_unobserved(unobserved, result.outcomes),
-        )
+    if unobserved and not tests:
+        return MutationAttempt(
+            defect_id=defect.id,
+            outcome=MutationOutcomeKind.NOT_ATTEMPTED,
+            descriptor=descriptor,
+            tests_run=tests,
+            reason=_why_unobserved(unobserved, result.outcomes),
+        )
```

## MUTABLE — prechange-run-only-when-execute-flag-set

- **criterion:** candidate-tests-run-once-before-changes
- **type:** `scope_too_narrow`
- **regions named:** 4
- **defect:** The pre-change test run only happens when `--execute` is enabled, so the delivered code can skip the required once-before-changes run on the default path.

**edit** — `src/acceptance/pipeline.py` lines 274-275

```diff
-    if execution is None or not execution.enabled:
-        return [], [], []
+    if execution is None:
+        return [], [], []
```

## MUTABLE — prechange-run-skipped-when-execution-disabled

- **criterion:** candidate-tests-run-once-before-changes
- **type:** `not_wired`
- **regions named:** 4
- **defect:** The baseline control run is wired only through the new execution tier; if that tier is off, nothing on the delivered path calls `establish_baseline`, so no pre-change test run occurs.

**edit** — `src/acceptance/pipeline.py` lines 274-275

```diff
-    if execution is None or not execution.enabled:
-        return [], [], []
+    if execution is None:
+        return [], [], []
```

## MUTABLE — halted-attempts-lose-specific-reason

- **criterion:** carry-reason-for-non-settlement
- **type:** `unenforced_on_one_path`
- **regions named:** 2
- **defect:** When execution is halted before mutation runs, `run_mutations` returns `NOT_ATTEMPTED` attempts with a generic halt reason, but the code path that builds those attempts does not preserve any defect-specific non-settlement reason because no descriptor or per-defect outcome exists on that route.

**edit** — `src/acceptance/mutation/runner.py` lines 78-82

```diff
-    if baseline.halted:
-        return [
-            _not_attempted(defect, f"the review halted before injection: {baseline.halt_reason}")
-            for defect in defects
-        ]
+    if baseline.halted:
+        return [
+            _not_attempted(defect, "the review halted before injection: no candidate test survived the control run")
+            for defect in defects
+        ]
```

## MUTABLE — missing-reason-on-not-attempted

- **criterion:** carry-reason-for-non-settlement
- **type:** `scope_too_narrow`
- **regions named:** 2
- **defect:** `MutationAttempt` only requires a non-empty `reason` for unsettled outcomes in its validator, but the runner can still construct `NOT_ATTEMPTED` attempts with an empty reason if one of the helper paths bypasses the validator or if a future caller instantiates the model differently; the non-settlement reason is not guaranteed by the attempt-building code itself.

**edit** — `src/acceptance/mutation/runner.py` lines 221-226

```diff
-    return MutationAttempt(
-        defect_id=defect.id,
-        outcome=MutationOutcomeKind.SURVIVED,
-        descriptor=descriptor,
-        tests_run=tests,
-    )
+    return MutationAttempt(
+        defect_id=defect.id,
+        outcome=MutationOutcomeKind.SURVIVED,
+        descriptor=descriptor,
+        tests_run=tests,
+        reason="",
+    )
```

## MUTABLE — execution-tier-disabled-by-default

- **criterion:** does-not-run-first
- **type:** `not_wired`
- **regions named:** 7
- **defect:** The execution tier is added behind `ExecutionSettings.enabled`, and `ExecutionSettings` defaults `enabled` to false. In the normal CLI path, `run_review` now receives an `execution` object, but `_run_execution_tier` returns immediately when execution is absent or disabled, so the code-reading `judge_pairs` path still runs first unless the caller explicitly passes `--execute`.

**edit** — `src/acceptance/mutation/settings.py` lines 38-38

```diff
-    enabled: bool = False
+    enabled: bool = True
```

## MUTABLE — static-judgement-still-runs-before-execution-when-execution-is-off

- **criterion:** does-not-run-first
- **type:** `established_not_maintained`
- **regions named:** 4
- **defect:** `run_review` now calls `_run_execution_tier` before `judge_pairs`, but when execution is disabled that helper returns empty attempts and verdicts, so the later code-reading judgement is still the first substantive review pass on the default path. The ordering invariant is only established for the opt-in execution path, not maintained for the ordinary review flow.

**edit** — `src/acceptance/pipeline.py` lines 274-275

```diff
-    if execution is None or not execution.enabled:
-        return [], [], []
+    if execution is None:
+        return [], [], []
```

## MUTABLE — execution-disabled-by-default

- **criterion:** execution-could-not-settle-defects
- **type:** `scope_too_narrow`
- **regions named:** 5
- **defect:** The execution tier is opt-in only, so when the caller does not pass --execute the review never runs the mutation stage and cannot settle any defects by execution before the code-reading judgement.

**edit** — `src/acceptance/cli.py` lines 817-824

```diff
-    check.add_argument(
-        "--execute",
-        action="store_true",
-        help=(
-            "Run the candidate tests: inject each enumerated defect and observe "
-            "which tests catch it, instead of predicting it by reading."
-        ),
-    )
+    check.add_argument(
+        "--execute",
+        action="store_true",
+        default=True,
+        help=(
+            "Run the candidate tests: inject each enumerated defect and observe "
+            "which tests catch it, instead of predicting it by reading."
+        ),
+    )
```

## MUTABLE — halt-on-failing-baseline-tests

- **criterion:** execution-could-not-settle-defects
- **type:** `missing_case`
- **regions named:** 5
- **defect:** A candidate test that already fails at head raises ReviewHalted unless --allow-failing-tests is set, so defects are not handed to code-reading evidence in the case where execution could not settle them because the control run found red tests.

**edit** — `src/acceptance/pipeline.py` lines 284-285

```diff
-    if baseline.halted:
-        raise ReviewHalted(baseline)
+    if baseline.halted and not execution.allow_failing_tests:
+        raise ReviewHalted(baseline)
```

## MUTABLE — mutation-attempts-not-rendered-for-halted-or-disabled-reviews

- **criterion:** injected-text-recorded-next-to-result
- **type:** `scope_too_narrow`
- **regions named:** 3
- **defect:** The review only records injected text in the mutation block when execution ran and produced attempts; reviews that halt at the baseline gate or never opt into execution carry no injected-text record next to the result at all.

**edit** — `src/acceptance/report.py` lines 131-133

```diff
-    if review.mutation_attempts:
-        lines.extend(_mutation_block(review))
-        lines.append("")
+    if review.mutation_attempts or review.halted:
+        lines.extend(_mutation_block(review))
+        lines.append("")
```

## MUTABLE — mutation-block-omits-injected-text-for-empty-replacement

- **criterion:** injected-text-recorded-next-to-result
- **type:** `wrong_output_shape`
- **regions named:** 1
- **defect:** The mutation report renders only the replacement lines, so when the injected text is an empty string the reader sees no injected text alongside the result even though the attempt was recorded.

**edit** — `src/acceptance/report.py` lines 291-292

```diff
-            for line in descriptor.replacement.splitlines() or [""]:
-                lines.append(f"      | {line}")
+            for line in descriptor.replacement.splitlines():
+                lines.append(f"      | {line}")
```

## MUTABLE — descriptor-declines-on-malformed-span-instead-of-validating

- **criterion:** mechanical-validity-checks
- **type:** `other`
- **regions named:** 2
- **defect:** A descriptor with an invalid line span is treated as a decline and converted into not_mutable, so the mechanical validity stage never gets a chance to reject that edit as invalid on its own path.

**edit** — `src/acceptance/mutation/descriptor.py` lines 206-207

```diff
-    if result.start_line < 1 or result.end_line < result.start_line:
-        return None
+    if result.start_line < 1 or result.end_line <= result.start_line:
+        return None
```

## MUTABLE — execution-tier-can-be-skipped-entirely

- **criterion:** mechanical-validity-checks
- **type:** `unenforced_on_one_path`
- **regions named:** 3
- **defect:** Mechanical validity is only exercised when the new execution tier is enabled; the default path leaves execution off and returns empty attempts/verdicts, so edits are still judged without the new mechanical checks on that route.

**edit** — `src/acceptance/pipeline.py` lines 274-275

```diff
-    if execution is None or not execution.enabled:
-        return [], [], []
+    if execution is None:
+        return [], [], []
```

## MUTABLE — mutation-tier-records-executed-lines

- **criterion:** no-line-execution-recording
- **type:** `other`
- **regions named:** 4
- **defect:** The new mutation execution path records per-test verdicts and attempts, but it does not record which source lines each test executed; if the implementation later derives line-execution data from these mutation runs, that would be a different behavior than the criterion allows.

**edit** — `src/acceptance/mutation/runner.py` lines 171-172

```diff
-        with mutated_copy(project_root, descriptor) as root:
-            result = run_tests(tests, root, config)
+        with mutated_copy(project_root, descriptor) as root:
+            result = run_tests(tests, root, config)
+            result.executed_lines = []
```

## MUTABLE — baseline-control-run-is-whole-suite

- **criterion:** no-whole-suite-run
- **type:** `other`
- **regions named:** 3
- **defect:** The baseline control run establishes usability by running every requested candidate test before mutation; if the requested set is the project's whole suite, this path produces evidence that the whole suite was executed.

**edit** — `src/acceptance/mutation/baseline.py` lines 100-104

```diff
-        if self.halted and self.usable_tests:
-            raise ValueError(
-                "a halted baseline offers usable tests, which would let injection run "
-                "against a control the review already rejected"
-            )
+        if self.halted and self.usable_tests:
+            raise ValueError(
+                "a halted baseline offers usable tests, which would let injection run "
+                "against a control the review already rejected"
+            )
+        return self
```

## MUTABLE — mutation-attempts-can-carry-reason-only

- **criterion:** observation-not-prediction
- **type:** `other`
- **regions named:** 3
- **defect:** A non-settling mutation attempt is validated to carry only a reason, but the code does not show that the recorded conclusion itself is derived from an observed run; a caller could still treat the reasoned non-settling outcome as a prediction about the tests rather than an observation from running them.

**edit** — `src/acceptance/mutation/attempt.py` lines 124-133

```diff
-    @model_validator(mode="after")
-    def _reason_accompanies_every_unsettled_attempt(self) -> MutationAttempt:
-        has_reason = bool(self.reason.strip())
-        if not self.settled and not has_reason:
-            raise ValueError(
-                f"outcome {self.outcome.value} for defect {self.defect_id!r} must carry a "
-                "reason: a defect the stage tried and could not settle has to stay "
-                "distinguishable from one it never tried"
-            )
-        return self
+    @model_validator(mode="after")
+    def _reason_accompanies_every_unsettled_attempt(self) -> MutationAttempt:
+        has_reason = bool(self.reason.strip())
+        if not self.settled and not has_reason:
+            raise ValueError(
+                f"outcome {self.outcome.value} for defect {self.defect_id!r} must carry a "
+                "reason: a defect the stage tried and could not settle has to stay "
+                "distinguishable from one it never tried"
+            )
+        if not self.settled and self.reason and self.outcome is MutationOutcomeKind.NOT_MUTABLE:
+            raise ValueError(
+                f"outcome {self.outcome.value} for defect {self.defect_id!r} must not be "
+                "treated as a prediction"
+            )
+        return self
```

## MUTABLE — static-verdicts-still-look-predicted

- **criterion:** observation-not-prediction
- **type:** `other`
- **regions named:** 4
- **defect:** The recorded conclusion can still be a static pair verdict that was produced by reading rather than by running the candidate tests against the altered copy, because the new execution verdicts are only appended and the later rating/reporting code may still surface the predicted result as the conclusion.

**edit** — `src/acceptance/review_state.py` lines 227-227

```diff
-    tier: EvidenceTier = EvidenceTier.STATIC
+    tier: EvidenceTier = EvidenceTier.DEFECT_KILLED
```

## MUTABLE — descriptor-accepts-invalid-json-syntax

- **criterion:** parser-files-still-parse
- **type:** `scope_too_narrow`
- **regions named:** 2
- **defect:** The descriptor builder only rejects malformed spans, so it can still return an edit for a .json file whose replacement is not valid JSON, letting an unparsable file through until the later validity check misses it.

**edit** — `src/acceptance/mutation/validity.py` lines 52-56

```diff
-_PARSERS = {
-    ".py": ast.parse,
-    ".pyi": ast.parse,
-    ".json": json.loads,
-}
+_PARSERS = {
+    ".py": ast.parse,
+    ".pyi": ast.parse,
+}
```

## MUTABLE — execution-tier-overwrites-static-verdicts

- **criterion:** preserve-code-reading-judgement
- **type:** `scope_too_narrow`
- **regions named:** 5
- **defect:** When execution is enabled, the pipeline replaces the static pair judgement with `remaining_defect_sets(attempts, defect_sets)` and then appends only the executed verdicts plus the reduced pair mapping. That means the code-reading judgement no longer contributes for defects that execution settles, so the review output and rating can lose the existing read-without-running judgement on those inputs.

**edit** — `src/acceptance/pipeline.py` lines 488-489

```diff
-        remaining_defect_sets(attempts, defect_sets),
-        discovered.tests,
+        defect_sets,
+        discovered.tests,
```

## MUTABLE — execution-tier-changes-conclusions-when-tests-cannot-run

- **criterion:** preserve-current-review-conclusions-when-unrunnable
- **type:** `scope_too_narrow`
- **regions named:** 8
- **defect:** When the code cannot be run, the new execution tier still changes the review by halting or by replacing static pair verdicts with mutation verdicts, so the review no longer reaches the same conclusions it reaches today.

**edit** — `src/acceptance/pipeline.py` lines 284-285

```diff
-    if baseline.halted:
-        raise ReviewHalted(baseline)
+    if baseline.halted:
+        return [], [], baseline.set_aside
```

## MUTABLE — executed-verdicts-not-included-in-rating-input

- **criterion:** recorded-at-strongest-evidence-tier
- **type:** `not_wired`
- **regions named:** 6
- **defect:** The execution tier can produce `MutationAttempt` and `PairVerdict` records, but if the pipeline fails to merge those executed verdicts into the verdict list passed to `derive_support`, the conclusion will still be recorded from static verdicts only and never reach the strongest tier the review produced on its own.

**edit** — `src/acceptance/pipeline.py` lines 488-494

```diff
-        remaining_defect_sets(attempts, defect_sets),
-        discovered.tests,
-        change_set,
-        client,
-        repo=repo,
-        batch_size=pair_batch_size,
-        tests_per_batch=tests_per_batch,
+        remaining_defect_sets(attempts, defect_sets),
+        discovered.tests,
+        change_set,
+        client,
+        repo=repo,
+        batch_size=pair_batch_size,
+        tests_per_batch=tests_per_batch,
+        verdicts=executed_verdicts,
```

## MUTABLE — failing-tests-filtered-out-of-report

- **criterion:** report-lists-set-aside-tests
- **type:** `scope_too_narrow`
- **regions named:** 3
- **defect:** The report only names tests classified as `FAILED`; if a failing candidate test is represented with a different outcome kind or is recorded in `set_aside_tests` under another kind, the report will miss it even though it was set aside.

**edit** — `src/acceptance/report.py` lines 313-315

```diff
-    for test in review.set_aside_tests:
-        lines.append(f"  [{test.kind.value}] {test.test_id}")
-        lines.append(f"    {test.reason}")
+    for test in review.set_aside_tests:
+        if test.kind is TestOutcomeKind.FAILED:
+            lines.append(f"  [{test.kind.value}] {test.test_id}")
+            lines.append(f"    {test.reason}")
```

## MUTABLE — set-aside-reason-overwrites-test-name

- **criterion:** report-lists-set-aside-tests
- **type:** `other`
- **regions named:** 1
- **defect:** The set-aside block prints the reason on the next line, but if the rendered structure or formatting is wrong the test id can be visually separated from the set-aside entry, making the report fail to clearly state which failing tests were set aside.

**edit** — `src/acceptance/report.py` lines 314-315

```diff
-        lines.append(f"  [{test.kind.value}] {test.test_id}")
-        lines.append(f"    {test.reason}")
+        lines.append(f"  [{test.kind.value}] {test.test_id}    {test.reason}")
```

## MUTABLE — set-aside-tests-not-rendered

- **criterion:** report-lists-set-aside-tests
- **type:** `not_wired`
- **regions named:** 5
- **defect:** The review stores set-aside tests, but the report path never reaches the new set-aside block, so generated reports omit the names of failing tests that were set aside.

**edit** — `src/acceptance/report.py` lines 131-137

```diff
-    if review.mutation_attempts:
-        lines.extend(_mutation_block(review))
-        lines.append("")
-
-    if review.set_aside_tests:
-        lines.extend(_set_aside_block(review))
-        lines.append("")
+    if review.mutation_attempts:
+        lines.extend(_mutation_block(review))
+        lines.append("")
+
+    if review.delta is not None:
+        lines.extend(_delta_block(review.delta))
+        lines.append("")
```

## MUTABLE — baseline-halt-skips-mutation-run

- **criterion:** run-candidate-tests-on-altered-copy
- **type:** `missing_case`
- **regions named:** 4
- **defect:** If the control run finds any candidate test already failing at head and --allow-failing-tests is not set, the code raises ReviewHalted and never runs the candidate tests against the altered copy.

**edit** — `src/acceptance/pipeline.py` lines 284-285

```diff
-    if baseline.halted:
-        raise ReviewHalted(baseline)
+    if baseline.halted:
+        return [], [], baseline.set_aside
```

## MUTABLE — execution-tier-disabled-by-default

- **criterion:** run-candidate-tests-on-altered-copy
- **type:** `scope_too_narrow`
- **regions named:** 6
- **defect:** The new execution tier is opt-in only, so the candidate tests are not run against the altered copy unless the caller passes --execute and the pipeline receives enabled execution settings.

**edit** — `src/acceptance/pipeline.py` lines 274-275

```diff
-    if execution is None or not execution.enabled:
-        return [], [], []
+    if execution is None:
+        return [], [], []
```

## MUTABLE — apply-span-can-splice-wrong-file-text

- **criterion:** single-continuous-edit-in-named-region
- **type:** `wrong_output_shape`
- **regions named:** 2
- **defect:** The span application logic replaces text by line slicing only, so if the descriptor points at the wrong file or the wrong line span the resulting patch is still a single patch shape but not the one confined to the defect's named region.

**edit** — `src/acceptance/mutation/validity.py` lines 73-77

```diff
-    lines = source.splitlines(keepends=True)
-    head = lines[: descriptor.start_line - 1]
-    tail = lines[descriptor.end_line :]
-    replacement = [descriptor.replacement] if descriptor.replacement else []
-    return "".join([*head, *replacement, *tail])
+    lines = source.splitlines(keepends=True)
+    head = lines[: descriptor.start_line - 1]
+    tail = lines[descriptor.end_line :]
+    replacement = [descriptor.replacement]
+    return "".join([*head, *replacement, *tail])
```

## MUTABLE — descriptor-not-constrained-to-named-region

- **criterion:** single-continuous-edit-in-named-region
- **type:** `other`
- **regions named:** 3
- **defect:** The descriptor builder can return an edit whose span is outside the defect's named region, so the applied patch would not be confined to the region the defect cited.

**edit** — `src/acceptance/mutation/descriptor.py` lines 199-205

```diff
-    label = result.region_label.strip()
-    if not label:
-        return None
-    by_label = {region.label: region for region in regions}
-    region = by_label.get(label)
-    if region is None:
-        return None
+    label = result.region_label.strip()
+    if not label:
+        return None
+    by_label = {region.label: region for region in regions}
+    region = by_label.get(label)
+    if region is None or not region.contains(result.start_line, result.end_line):
+        return None
```

## MUTABLE — region-resolution-drops-all-named-spans

- **criterion:** single-continuous-edit-in-named-region
- **type:** `missing_case`
- **regions named:** 2
- **defect:** A defect whose named region is absent from the resolved change set is treated as not mutable, so the criterion's coverage of edits within the named region can fall through unhandled for defects that cite deleted or unresolved code refs.

**edit** — `src/acceptance/mutation/region.py` lines 42-45

```diff
-    A label naming no region in this change set is dropped rather than reported
-    as absent. The caller sees a defect with fewer regions than labels, and a
-    defect left with none is not mutable — which is the honest answer, since
-    there is nowhere the edit would be allowed to land.
+    A label naming no region in this change set is treated as not mutable, so
+    the caller sees a defect with fewer regions than labels and can fall through
+    unhandled when every cited region was deleted or otherwise unresolved.
```

## MUTABLE — descriptor-can-return-non-minimal-edit

- **criterion:** smallest-edit-that-makes-defect-true
- **type:** `other`
- **regions named:** 3
- **defect:** The descriptor stage can return an edit that is not the smallest one that makes the defect true, because there is no mechanical check that the model chose the minimal span or that a shorter valid edit was rejected.

**edit** — `src/acceptance/mutation/descriptor.py` lines 50-50

```diff
-Produce the SMALLEST edit that would make that defect real.
+Produce the SMALLEST edit that would make that defect real, and prefer the first valid span if several work.
```

## MUTABLE — region-filter-drops-valid-edit-sites

- **criterion:** smallest-edit-that-makes-defect-true
- **type:** `scope_too_narrow`
- **regions named:** 3
- **defect:** The descriptor only asks about regions whose file path is present in the preloaded sources, so a defect whose smallest edit is in a named region from a file that was not loaded or was omitted from sources will never get a chance to produce the required edit.

**edit** — `src/acceptance/mutation/descriptor.py` lines 127-128

```diff
-    asking = [defect for defect in defects if regions_by_defect.get(defect.id)]
-
+    asking = [defect for defect in defects if regions_by_defect.get(defect.id)]
```

## MUTABLE — validity-rejects-prose-defects-as-unmutable

- **criterion:** smallest-edit-that-makes-defect-true
- **type:** `missing_case`
- **regions named:** 3
- **defect:** The validity check only parses .py, .pyi, and .json files, so a defect in prose or another unparsed format can be rejected as not_mutable even when a smallest contiguous edit exists in that text.

**edit** — `src/acceptance/mutation/validity.py` lines 52-56

```diff
-_PARSERS = {
-    ".py": ast.parse,
-    ".pyi": ast.parse,
-    ".json": json.loads,
-}
+_PARSERS = {
+    ".py": ast.parse,
+    ".pyi": ast.parse,
+}
```

## MUTABLE — baseline-failure-detected-but-not-raised

- **criterion:** stop-review-on-failing-candidate-test
- **type:** `not_wired`
- **regions named:** 4
- **defect:** `establish_baseline` can mark the control run as halted, but if the caller forgets to check `baseline.halted` and raise `ReviewHalted`, the review would continue instead of stopping on a failing candidate test.

**edit** — `src/acceptance/pipeline.py` lines 284-285

```diff
-    if baseline.halted:
-        raise ReviewHalted(baseline)
+    if baseline.halted:
+        pass
```

## MUTABLE — failing-tests-set-aside-instead-of-stopping

- **criterion:** stop-review-on-failing-candidate-test
- **type:** `condition_inverted`
- **regions named:** 2
- **defect:** The baseline reader turns failing candidate tests into `set_aside` entries and only halts when `allow_failing_tests` is false; if that gate is wrong-way-round, the review would continue when it should stop on a failing candidate test.

**edit** — `src/acceptance/mutation/baseline.py` lines 156-157

```diff
-    if not baseline.halted and baseline.usable_tests:
-        baseline = _drop_unfaithful(baseline, project_root, config)
+    if baseline.halted and baseline.usable_tests:
+        baseline = _drop_unfaithful(baseline, project_root, config)
```

## MUTABLE — halt-path-not-triggered-from-cli

- **criterion:** stop-review-on-failing-candidate-test
- **type:** `not_wired`
- **regions named:** 3
- **defect:** The new halt exception is only handled in `main`, but the review path can still call `run_check` directly with `execution` set; in that path a failing candidate test would not stop the review or emit the stopping reason.

**edit** — `src/acceptance/cli.py` lines 206-210

```diff
-        prior=prior,
-        ledger_prior=ledger.read_if_present(continue_from) if ledger is not None else None,
-        ledger_sink=sink,
-        execution=execution,
-    )
+        prior=prior,
+        ledger_prior=ledger.read_if_present(continue_from) if ledger is not None else None,
+        ledger_sink=sink,
+        execution=execution,
+    )
+    if execution is not None and execution.enabled and review.halt_reason is not None:
+        raise ReviewHalted(review.halt_reason, review.baseline)
```

## MUTABLE — baseline-halt-changes-run-eligibility

- **criterion:** tests-candidate-selection
- **type:** `other`
- **regions named:** 3
- **defect:** The new baseline control run can halt review execution when a candidate test already fails at head, which changes the decision about whether tests can be run at all instead of leaving that decision unchanged.

**edit** — `src/acceptance/mutation/baseline.py` lines 156-157

```diff
-    if not baseline.halted and baseline.usable_tests:
-        baseline = _drop_unfaithful(baseline, project_root, config)
+    if baseline.usable_tests:
+        baseline = _drop_unfaithful(baseline, project_root, config)
```

## MUTABLE — executed-verdicts-not-marked-weaker

- **criterion:** weaker-tier-evidence
- **type:** `scope_too_narrow`
- **regions named:** 2
- **defect:** The mutation verdicts are emitted with `tier=STATIC` instead of `DEFECT_KILLED`, so the review cannot distinguish executed evidence from static evidence and the weaker-tier record is lost.

**edit** — `src/acceptance/mutation/verdicts.py` lines 64-64

```diff
-                    tier=EvidenceTier.DEFECT_KILLED,
+                    tier=EvidenceTier.STATIC,
```
