# Descriptor answers with typed declines — #45, head 518f876

71 defects from run `87896b868ce088e4`. Asked by the code at `6361e5d`.

- **already_present:** 1
- **mutable:** 35
- **refused by a check:** 35

---

## already_present — observation-not-prediction/executed-result-not-stored-as-conclusion

- **type:** `other`
- **defect:** The execution tier records attempts and verdicts, but nothing in the changed code shows the final stored conclusion being rewritten to the observed run result instead of leaving the old predicted conclusion in place, so the review can still conclude with a forecast.
- **reason:** The defect is already true: `src/acceptance/pipeline.py` stores the final review state with `review_state = review_state.model_copy(update={"verdicts": verdicts, "findings": findings, "recommendations": recommendations, "pair_verdicts": pair_mapping.verdicts, "unjudged_pairs": pair_mapping.unjudged_pairs, "mutation_attempts": attempts, "set_aside_tests": set_aside_tests})` and then returns that updated state, so the observed run result is already written into the stored conclusion rather than leaving only the predicted conclusion in place.

## mutable — candidate-tests-not-discriminate-when-none-fail/no-discrimination-report-when-execution-finds-no-kills

- **type:** `missing_case`
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

## mutable — candidate-tests-not-discriminate-when-none-fail/survival-with-partially-observed-run-treated-as-no-discrimination

- **type:** `scope_too_narrow`
- **defect:** A mutant run with no failing tests but with some tests not completed is classified as `not_attempted` instead of a non-discrimination result, so the criterion is only handled for fully observed no-fail runs and not for all no-fail executions the criterion could cover.

**edit** — `src/acceptance/mutation/runner.py` lines 177-185

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
+            outcome=MutationOutcomeKind.SURVIVED,
+            descriptor=descriptor,
+            tests_run=tests,
+        )
```

## mutable — candidate-tests-run-once-before-changes/halted-baseline-prevents-any-test-run

- **type:** `missing_case`
- **defect:** A halted baseline returns before mutation, but the criterion still requires the candidate tests to have been run once against the delivered code; if the halt path is taken without a prior run being guaranteed, the obligation is missed for that input.

**edit** — `src/acceptance/mutation/baseline.py` lines 97-104

```diff
-    @model_validator(mode="after")
-    def _a_halted_baseline_offers_no_tests(self) -> Baseline:
-        if self.halted and self.usable_tests:
-            raise ValueError(
-                "a halted baseline offers usable tests, which would let injection run "
-                "against a control the review already rejected"
-            )
-        return self
+    @model_validator(mode="after")
+    def _a_halted_baseline_offers_no_tests(self) -> Baseline:
+        if self.halted:
+            raise ValueError(
+                "a halted baseline offers usable tests, which would let injection run "
+                "against a control the review already rejected"
+            )
+        return self
```

## mutable — candidate-tests-run-once-before-changes/prechange-run-skipped-when-execution-disabled

- **type:** `not_wired`
- **defect:** The baseline control run is wired only through the new execution tier; if that tier is off, nothing on the delivered path calls `establish_baseline`, so no pre-change test run occurs.

**edit** — `src/acceptance/pipeline.py` lines 274-275

```diff
-    if execution is None or not execution.enabled:
-        return [], [], []
+    if execution is None:
+        return [], [], []
```

## mutable — carry-reason-for-non-settlement/halted-attempts-lose-specific-reason

- **type:** `unenforced_on_one_path`
- **defect:** When execution is halted before mutation runs, `run_mutations` returns `NOT_ATTEMPTED` attempts with a generic halt reason, but the code path that builds those attempts does not preserve any defect-specific non-settlement reason because no descriptor or per-defect outcome exists on that route.

**edit** — `src/acceptance/mutation/runner.py` lines 66-70

```diff
-    if baseline.halted:
-        return [
-            _not_attempted(defect, f"the review halted before injection: {baseline.halt_reason}")
-            for defect in defects
-        ]
+    if baseline.halted:
+        return [
+            _not_attempted(defect, "the review halted before injection: no defect-specific reason was recorded")
+            for defect in defects
+        ]
```

## mutable — carry-reason-for-non-settlement/missing-reason-on-not-attempted

- **type:** `scope_too_narrow`
- **defect:** `MutationAttempt` only requires a non-empty `reason` for unsettled outcomes in its validator, but the runner can still construct `NOT_ATTEMPTED` attempts with an empty reason if one of the helper paths bypasses the validator or if a future caller instantiates the model differently; the non-settlement reason is not guaranteed by the attempt-building code itself.

**edit** — `src/acceptance/mutation/attempt.py` lines 114-114

```diff
-    reason: str = ""
+    reason: str = Field(default_factory=str)
```

## mutable — carry-reason-for-non-settlement/not-attempted-from-copy-failure-may-be-unexplained

- **type:** `other`
- **defect:** If preparing the mutated copy fails, `_attempt` returns `NOT_ATTEMPTED` with an error string, but that reason comes from the filesystem exception rather than from the execution outcome itself; a reader checking the execution record would need to inspect whether this path always produces a meaningful non-settlement reason for every failure mode.

**edit** — `src/acceptance/mutation/runner.py` lines 139-145

```diff
-    except OSError as error:
-        return MutationAttempt(
-            defect_id=defect.id,
-            outcome=MutationOutcomeKind.NOT_ATTEMPTED,
-            descriptor=descriptor,
-            reason=f"the mutated copy could not be prepared: {error}",
-        )
+    except OSError:
+        return MutationAttempt(
+            defect_id=defect.id,
+            outcome=MutationOutcomeKind.NOT_ATTEMPTED,
+            descriptor=descriptor,
+            reason="the mutated copy could not be prepared, so this defect goes to the static judge",
+        )
```

## mutable — continue-with-set-aside-tests/failing-tests-still-count-in-support

- **type:** `other`
- **defect:** The executed verdicts are appended to the pair verdict list, but the support derivation still receives the full defect sets and may therefore let set-aside failing tests continue to influence the conclusion instead of being excluded from it.

**edit** — `src/acceptance/pipeline.py` lines 509-509

```diff
-    support = derive_support(needs_tests, defect_sets, verdicts, pair_mapping.unjudged)
+    support = derive_support(needs_tests, remaining_defect_sets(attempts, defect_sets), verdicts, pair_mapping.unjudged)
```

## mutable — does-not-run-first/execution-tier-disabled-by-default

- **type:** `not_wired`
- **defect:** The execution tier is added behind `ExecutionSettings.enabled`, and `ExecutionSettings` defaults `enabled` to false. In the normal CLI path, `run_review` now receives an `execution` object, but `_run_execution_tier` returns immediately when execution is absent or disabled, so the code-reading `judge_pairs` path still runs first unless the caller explicitly passes `--execute`.

**edit** — `src/acceptance/pipeline.py` lines 457-465

```diff
-    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
-        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
-    )
-
-    pair_mapping = judge_pairs(
-        # Only the defects injection could not reach. The FULL `defect_sets` still
-        # goes to `derive_support` below, so a criterion's denominator is
-        # unchanged — what shrinks is the question put to the model, not the bar.
-        remaining_defect_sets(attempts, defect_sets),
+    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
+        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
+    )
+
+    pair_mapping = judge_pairs(
+        defect_sets,
+        discovered.tests,
+        change_set,
+        client,
```

## mutable — does-not-run-first/static-judgement-still-runs-before-execution-when-execution-is-off

- **type:** `established_not_maintained`
- **defect:** `run_review` now calls `_run_execution_tier` before `judge_pairs`, but when execution is disabled that helper returns empty attempts and verdicts, so the later code-reading judgement is still the first substantive review pass on the default path. The ordering invariant is only established for the opt-in execution path, not maintained for the ordinary review flow.

**edit** — `src/acceptance/pipeline.py` lines 457-465

```diff
-    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
-        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
-    )
-
-    pair_mapping = judge_pairs(
-        # Only the defects injection could not reach. The FULL `defect_sets` still
-        # goes to `derive_support` below, so a criterion's denominator is
-        # unchanged — what shrinks is the question put to the model, not the bar.
-        remaining_defect_sets(attempts, defect_sets),
+    pair_mapping = judge_pairs(
+        # Only the defects injection could not reach. The FULL `defect_sets` still
+        # goes to `derive_support` below, so a criterion's denominator is
+        # unchanged — what shrinks is the question put to the model, not the bar.
+        remaining_defect_sets(attempts, defect_sets),
+        discovered.tests,
+        change_set,
+        client,
```

## mutable — injected-text-recorded-next-to-result/mutation-block-omits-injected-text-for-empty-replacement

- **type:** `wrong_output_shape`
- **defect:** The mutation report renders only the replacement lines, so when the injected text is an empty string the reader sees no injected text alongside the result even though the attempt was recorded.

**edit** — `src/acceptance/report.py` lines 291-292

```diff
-            for line in descriptor.replacement.splitlines() or [""]:
-                lines.append(f"      | {line}")
+            for line in descriptor.replacement.splitlines():
+                lines.append(f"      | {line}")
```

## mutable — mechanical-validity-checks/containment-check-only-looks-at-resolved-regions

- **type:** `scope_too_narrow`
- **defect:** The containment check only considers regions that were resolved from the current change set; if a defect names no region in the edited file, the code reports it as not mutable rather than mechanically validating the edit against that obligation.

**edit** — `src/acceptance/mutation/validity.py` lines 113-118

```diff
-    named = [region for region in regions if region.path == descriptor.path]
-    if not named:
-        return (
-            f"the defect names no region in {descriptor.path}, so an edit there could not be "
-            "credited to it"
-        )
+    named = [region for region in regions if region.path == descriptor.path]
+    if not named:
+        return None
```

## mutable — mechanical-validity-checks/execution-tier-can-be-skipped-entirely

- **type:** `unenforced_on_one_path`
- **defect:** Mechanical validity is only exercised when the new execution tier is enabled; the default path leaves execution off and returns empty attempts/verdicts, so edits are still judged without the new mechanical checks on that route.

**edit** — `src/acceptance/pipeline.py` lines 274-275

```diff
-    if execution is None or not execution.enabled:
-        return [], [], []
+    if execution is None:
+        return [], [], []
```

## mutable — mechanical-validity-checks/parse-check-still-applies-to-all-mutants

- **type:** `scope_too_narrow`
- **defect:** The new validity gate still rejects mutants by parsing the edited file for Python and JSON only, so edits to other file types can slip through without any mechanical parse check at all.

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

## mutable — no-edit-without-named-region/no-region-defects-silently-dropped

- **type:** `other`
- **defect:** When a defect has no resolved regions, the descriptor builder skips asking about it and returns None, but the surrounding pipeline could still end up with no explicit record that this defect was uneditable rather than merely unattempted.

**edit** — `src/acceptance/mutation/runner.py` lines 105-111

```diff
-    if not regions:
-        return _not_mutable(
-            defect,
-            "the defect names no changed region with text at head, so there is no span to "
-            "replace. This is the shape of an absence defect, where the implicated lines are "
-            "where behavior should be and is not.",
-        )
+    if not regions:
+        return _not_attempted(
+            defect,
+            "the defect names no changed region with text at head, so there is no span to "
+            "replace. This is the shape of an absence defect, where the implicated lines are "
+            "where behavior should be and is not.",
+        )
```

## mutable — no-parser-not-invalid/parser-check-still-applies-to-nonparsed-files

- **type:** `other`
- **defect:** The validity check still rejects a mutant for a file type that has no parser, so a documentation or other non-parsed file can be marked not_mutable just because it cannot be parsed.

**edit** — `src/acceptance/mutation/validity.py` lines 126-133

```diff
-    # Check 2 — the mutated file parses, when the file has a parser.
-    parse = _parser_for(descriptor.path)
-    if parse is not None:
-        mutated = apply_span(source, descriptor)
-        try:
-            parse(mutated)
-        except _PARSE_ERRORS as error:
-            return f"the mutated {descriptor.path} does not parse: {error}"
+    # Check 2 — the mutated file parses, when the file has a parser.
+    parse = _parser_for(descriptor.path)
+    if parse is not None:
+        mutated = apply_span(source, descriptor)
+        try:
+            parse(mutated)
+        except _PARSE_ERRORS as error:
+            return f"the mutated {descriptor.path} does not parse: {error}"
+
```

## mutable — no-whole-suite-run/baseline-control-run-is-whole-suite

- **type:** `other`
- **defect:** The baseline control run establishes usability by running every requested candidate test before mutation; if the requested set is the project's whole suite, this path produces evidence that the whole suite was executed.

**edit** — `src/acceptance/mutation/baseline.py` lines 125-130

```diff
-    requested = list(dict.fromkeys(test_ids))
-    if not requested:
-        return Baseline()
-
-    result = run_tests(requested, project_root, config)
-    return _read(result, allow_failing_tests=allow_failing_tests)
+    requested = list(dict.fromkeys(test_ids))
+    if not requested:
+        return Baseline()
+
+    result = run_tests(requested[:1], project_root, config)
+    return _read(result, allow_failing_tests=allow_failing_tests)
```

## mutable — observation-not-prediction/static-verdicts-still-look-predicted

- **type:** `other`
- **defect:** The recorded conclusion can still be a static pair verdict that was produced by reading rather than by running the candidate tests against the altered copy, because the new execution verdicts are only appended and the later rating/reporting code may still surface the predicted result as the conclusion.

**edit** — `src/acceptance/pipeline.py` lines 479-479

```diff
-    verdicts = executed_verdicts + pair_mapping.verdicts
+    verdicts = pair_mapping.verdicts + executed_verdicts
```

## mutable — parser-files-still-parse/descriptor-accepts-invalid-json-syntax

- **type:** `scope_too_narrow`
- **defect:** The descriptor builder only rejects malformed spans, so it can still return an edit for a .json file whose replacement is not valid JSON, letting an unparsable file through until the later validity check misses it.

**edit** — `src/acceptance/mutation/validity.py` lines 126-133

```diff
-    # Check 2 — the mutated file parses, when the file has a parser.
-    parse = _parser_for(descriptor.path)
-    if parse is not None:
-        mutated = apply_span(source, descriptor)
-        try:
-            parse(mutated)
-        except _PARSE_ERRORS as error:
-            return f"the mutated {descriptor.path} does not parse: {error}"
+    # Check 2 — the mutated file parses, when the file has a parser.
+    parse = _parser_for(descriptor.path)
+    if parse is not None:
+        mutated = apply_span(source, descriptor)
+        try:
+            parse(mutated)
+        except _PARSE_ERRORS as error:
+            return f"the mutated {descriptor.path} does not parse: {error}"
+
```

## mutable — preserve-code-reading-judgement/execution-tier-overwrites-static-verdicts

- **type:** `scope_too_narrow`
- **defect:** When execution is enabled, the pipeline replaces the static pair judgement with `remaining_defect_sets(attempts, defect_sets)` and then appends only the executed verdicts plus the reduced pair mapping. That means the code-reading judgement no longer contributes for defects that execution settles, so the review output and rating can lose the existing read-without-running judgement on those inputs.

**edit** — `src/acceptance/pipeline.py` lines 479-479

```diff
-    verdicts = executed_verdicts + pair_mapping.verdicts
+    verdicts = pair_mapping.verdicts
```

## mutable — preserve-code-reading-judgement/stored-reviews-drop-static-judgement-context

- **type:** `stored_form_unreadable`
- **defect:** The review model now stores `mutation_attempts`, `set_aside_tests`, and a mixed-tier `pair_verdicts`, but the diff does not show any compatibility layer for older stored reviews that only have the previous static judgement shape. If downstream reading expects the old code-reading judgement fields or assumes all verdicts are static, previously written reviews may no longer round-trip cleanly.

**edit** — `src/acceptance/review_state.py` lines 1251-1251

```diff
-    pair_verdicts: list[PairVerdict] = Field(default_factory=list)
+    pair_verdicts: list[PairVerdict] = Field(default_factory=list)
+    static_judgements: list[StaticJudgement] = Field(default_factory=list)
```

## mutable — preserve-current-review-conclusions-when-unrunnable/execution-tier-changes-conclusions-when-tests-cannot-run

- **type:** `scope_too_narrow`
- **defect:** When the code cannot be run, the new execution tier still changes the review by halting or by replacing static pair verdicts with mutation verdicts, so the review no longer reaches the same conclusions it reaches today.

**edit** — `src/acceptance/pipeline.py` lines 284-285

```diff
-    if baseline.halted:
-        raise ReviewHalted(baseline)
+    if baseline.halted:
+        return [], [], baseline.set_aside
```

## mutable — preserve-current-review-conclusions-when-unrunnable/mutation-verdicts-not-carried-into-support-on-unrunnable-path

- **type:** `unenforced_on_one_path`
- **defect:** The review can still run the static pair judgement on the full defect sets when execution is disabled or cannot settle a defect, but the derived support and stored review conclusions may ignore the executed verdict tier on that path, so unrunnable cases can produce different conclusions from today.

**edit** — `src/acceptance/pipeline.py` lines 509-510

```diff
-    support = derive_support(needs_tests, defect_sets, verdicts, pair_mapping.unjudged)
-    needs_tests = apply_derived_support(needs_tests, support)
+    support = derive_support(needs_tests, defect_sets, pair_mapping.verdicts, pair_mapping.unjudged)
+    needs_tests = apply_derived_support(needs_tests, support)
```

## mutable — recorded-at-strongest-evidence-tier/executed-verdicts-not-included-in-rating-input

- **type:** `not_wired`
- **defect:** The execution tier can produce `MutationAttempt` and `PairVerdict` records, but if the pipeline fails to merge those executed verdicts into the verdict list passed to `derive_support`, the conclusion will still be recorded from static verdicts only and never reach the strongest tier the review produced on its own.

**edit** — `src/acceptance/pipeline.py` lines 479-479

```diff
-    verdicts = executed_verdicts + pair_mapping.verdicts
+    verdicts = pair_mapping.verdicts
```

## mutable — report-lists-set-aside-tests/set-aside-reason-overwrites-test-name

- **type:** `other`
- **defect:** The set-aside block prints the reason on the next line, but if the rendered structure or formatting is wrong the test id can be visually separated from the set-aside entry, making the report fail to clearly state which failing tests were set aside.

**edit** — `src/acceptance/report.py` lines 314-315

```diff
-        lines.append(f"  [{test.kind.value}] {test.test_id}")
-        lines.append(f"    {test.reason}")
+        lines.append(f"  [{test.kind.value}] {test.test_id}: {test.reason}")
```

## mutable — report-lists-set-aside-tests/set-aside-tests-not-rendered

- **type:** `not_wired`
- **defect:** The review stores set-aside tests, but the report path never reaches the new set-aside block, so generated reports omit the names of failing tests that were set aside.

**edit** — `src/acceptance/report.py` lines 135-136

```diff
-    if review.set_aside_tests:
-        lines.extend(_set_aside_block(review))
+    if review.set_aside_tests:
+        lines.extend(_set_aside_block(review))
+        lines.append("")
```

## mutable — run-candidate-tests-on-altered-copy/baseline-halt-skips-mutation-run

- **type:** `missing_case`
- **defect:** If the control run finds any candidate test already failing at head and --allow-failing-tests is not set, the code raises ReviewHalted and never runs the candidate tests against the altered copy.

**edit** — `src/acceptance/pipeline.py` lines 284-285

```diff
-    if baseline.halted:
-        raise ReviewHalted(baseline)
+    if baseline.halted:
+        pass
```

## mutable — single-continuous-edit-in-named-region/descriptor-allows-multi-span-edit

- **type:** `other`
- **defect:** The mutation descriptor path can still describe an edit that is not a single continuous stretch in one file, so the injected change could be assembled from multiple disjoint spans instead of one contiguous patch.

**edit** — `src/acceptance/mutation/descriptor.py` lines 54-60

```diff
-Replace one contiguous run of lines in ONE file. Give:
-
-- `region_label`: which of the offered regions the edit lands in.
-- `start_line` and `end_line`: the first and last line to replace, inclusive,
-  using the line numbers shown. To change a single line, set both to it.
-- `replacement`: the text those lines become, including its indentation and its
-  trailing newline. An empty string deletes them.
+Replace one contiguous run of lines in ONE file. Give:
+
+- `region_label`: which of the offered regions the edit lands in.
+- `start_line` and `end_line`: the first and last line to replace, inclusive,
+  using the line numbers shown. To change a single line, set both to it.
+- `replacement`: the text those lines become, including its indentation and its
+  trailing newline. An empty string deletes them.
+
+The replacement must keep the file valid. For code that means it still parses and still loads — an edit that stops the module importing tests nothing, because every test then fails for a reason that has nothing to do with the defect.
+
+SMALLEST MEANS SMALLEST
+
+Change the behavior the defect names and nothing else. Do not rename anything, do not reformat, do not fix unrelated things you notice. The edit is read by a person deciding whether the defect it created is the one that was named, and a large edit makes that impossible.
```

## mutable — smallest-edit-that-makes-defect-true/descriptor-can-return-non-minimal-edit

- **type:** `other`
- **defect:** The descriptor stage can return an edit that is not the smallest one that makes the defect true, because there is no mechanical check that the model chose the minimal span or that a shorter valid edit was rejected.

**edit** — `src/acceptance/mutation/descriptor.py` lines 50-50

```diff
-Produce the SMALLEST edit that would make that defect real.
+Produce a valid edit that would make that defect real.
```

## mutable — smallest-edit-that-makes-defect-true/region-filter-drops-valid-edit-sites

- **type:** `scope_too_narrow`
- **defect:** The descriptor only asks about regions whose file path is present in the preloaded sources, so a defect whose smallest edit is in a named region from a file that was not loaded or was omitted from sources will never get a chance to produce the required edit.

**edit** — `src/acceptance/mutation/descriptor.py` lines 170-171

```diff
-    offered = [region for region in regions if region.path in sources]
-    allowed = {"region_label": [region.label for region in offered] + [""]}
+    offered = [region for region in regions if region.path in sources]
+    allowed = {"region_label": [region.label for region in regions] + [""]}
+    constrained = constrain(_Descriptor, allowed)
```

## mutable — stop-review-on-failing-candidate-test/baseline-failure-detected-but-not-raised

- **type:** `not_wired`
- **defect:** `establish_baseline` can mark the control run as halted, but if the caller forgets to check `baseline.halted` and raise `ReviewHalted`, the review would continue instead of stopping on a failing candidate test.

**edit** — `src/acceptance/pipeline.py` lines 284-285

```diff
-    if baseline.halted:
-        raise ReviewHalted(baseline)
+    if baseline.halted:
+        pass
```

## mutable — test-fails-discriminate-defect/executed-verdicts-may-not-reach-discrimination-record

- **type:** `not_wired`
- **defect:** The execution tier builds `executed_verdicts`, but the review only records discrimination if those verdicts are actually threaded into the same structures the rest of the pipeline uses; if any caller path bypasses `_run_execution_tier` or drops `executed_verdicts` before persistence, a failing test would not be shown as discriminating for the defect.

**edit** — `src/acceptance/pipeline.py` lines 479-479

```diff
-    verdicts = executed_verdicts + pair_mapping.verdicts
+    verdicts = pair_mapping.verdicts
```

## mutable — weaker-tier-evidence/achieved-tier-stays-static

- **type:** `scope_too_narrow`
- **defect:** The derived support record still writes `achieved_evidence_tier` as `STATIC` instead of using the weakest tier from the verdicts it rests on, so reviews that include executed verdicts are recorded at the wrong tier.

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
+                    # predicted defect uses the weakest tier from its verdicts.
+                    "achieved_evidence_tier": result.achieved_tier,
```

## mutable — weaker-tier-evidence/executed-verdicts-not-marked-weaker

- **type:** `scope_too_narrow`
- **defect:** The mutation verdicts are emitted with `tier=STATIC` instead of `DEFECT_KILLED`, so the review cannot distinguish executed evidence from static evidence and the weaker-tier record is lost.

**edit** — `src/acceptance/mutation/verdicts.py` lines 64-64

```diff
-                    tier=EvidenceTier.DEFECT_KILLED,
+                    tier=EvidenceTier.STATIC,
```

## mutable — weaker-tier-evidence/execution-tier-not-included-in-rating-input

- **type:** `not_wired`
- **defect:** The execution tier may run and produce attempts, but if those executed verdicts are not merged into the verdict list passed to `derive_support`, the rating still reflects only static pair judgments and never records the weaker tier from execution.

**edit** — `src/acceptance/pipeline.py` lines 479-479

```diff
-    verdicts = executed_verdicts + pair_mapping.verdicts
+    verdicts = pair_mapping.verdicts
```

## refused by a check — candidate-tests-not-discriminate-when-none-fail/executed-verdicts-not-marked-as-non-discriminating-in-support

- **type:** `wrong_output_shape`
- **defect:** Executed verdicts are stored with `tier=DEFECT_KILLED`, but the support derivation only records the weakest tier and never emits a distinct non-discrimination shape for the no-fail case, so downstream consumers cannot tell from the stored verdicts alone that the candidate tests did not discriminate.
- **reason:** the replacement for src/acceptance/defects/support.py lines 277..280 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/defects/support.py` lines 277-280

```diff
-    return min(
-        (tier_by_defect.get(defect.id, EvidenceTier.STATIC) for defect in defect_set.defects),
-        default=EvidenceTier.STATIC,
-    )
+    return min(
+        (tier_by_defect.get(defect.id, EvidenceTier.STATIC) for defect in defect_set.defects),
+        default=EvidenceTier.STATIC,
+    )
```

## refused by a check — candidate-tests-run-once-before-changes/prechange-run-only-when-execute-flag-set

- **type:** `scope_too_narrow`
- **defect:** The pre-change test run only happens when `--execute` is enabled, so the delivered code can skip the required once-before-changes run on the default path.
- **reason:** the replacement for src/acceptance/pipeline.py lines 457..459 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/pipeline.py` lines 457-459

```diff
-    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
-        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
-    )
+    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
+        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
+    )
```

## refused by a check — continue-with-set-aside-tests/set-aside-tests-not-rendered

- **type:** `wrong_output_shape`
- **defect:** The report never renders the list of set-aside candidate tests, so a caller cannot identify which failing tests were excluded from the conclusion.
- **reason:** the replacement for src/acceptance/report.py lines 135..137 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/report.py` lines 135-137

```diff
-    if review.set_aside_tests:
-        lines.extend(_set_aside_block(review))
-        lines.append("")
+    if review.set_aside_tests:
+        lines.extend(_set_aside_block(review))
+        lines.append("")
```

## refused by a check — execution-could-not-settle-defects/execution-disabled-by-default

- **type:** `scope_too_narrow`
- **defect:** The execution tier is opt-in only, so when the caller does not pass --execute the review never runs the mutation stage and cannot settle any defects by execution before the code-reading judgement.
- **reason:** the mutated src/acceptance/cli.py does not parse: unmatched ')' (<unknown>, line 956)

**edit** — `src/acceptance/cli.py` lines 951-953

```diff
-                execution=ExecutionSettings(
-                    enabled=args.execute,
-                    allow_failing_tests=args.allow_failing_tests,
+                execution=ExecutionSettings(
+                    enabled=True,
+                    allow_failing_tests=args.allow_failing_tests,
+                ),
```

## refused by a check — execution-could-not-settle-defects/halt-on-failing-baseline-tests

- **type:** `missing_case`
- **defect:** A candidate test that already fails at head raises ReviewHalted unless --allow-failing-tests is set, so defects are not handed to code-reading evidence in the case where execution could not settle them because the control run found red tests.
- **reason:** the mutated src/acceptance/mutation/baseline.py does not parse: unmatched ')' (<unknown>, line 162)

**edit** — `src/acceptance/mutation/baseline.py` lines 149-160

```diff
-    failing = [test for test in set_aside if test.kind is TestOutcomeKind.FAILED]
-    if failing and not allow_failing_tests:
-        names = ", ".join(test.test_id for test in failing)
-        return Baseline(
-            set_aside=set_aside,
-            halted=True,
-            halt_reason=(
-                f"{len(failing)} candidate test(s) fail against the code as delivered "
-                f"({names}). A test that is already red says nothing when it goes red under "
-                "an injected defect, so nothing would be learned by continuing. Re-run "
-                "allowing failing tests to proceed with these set aside."
-            ),
+    failing = [test for test in set_aside if test.kind is TestOutcomeKind.FAILED]
+    if failing and not allow_failing_tests:
+        names = ", ".join(test.test_id for test in failing)
+        return Baseline(
+            set_aside=set_aside,
+            halted=True,
+            halt_reason=(
+                f"{len(failing)} candidate test(s) fail against the code as delivered "
+                f"({names}). A test that is already red says nothing when it goes red under "
+                "an injected defect, so nothing would be learned by continuing. Re-run "
+                "allowing failing tests to proceed with these set aside."
+            ),
+        )
```

## refused by a check — execution-could-not-settle-defects/not-attempted-defects-may-never-reach-reading-judgement

- **type:** `missing_case`
- **defect:** When the mutant cannot be prepared or the run is incomplete, the attempt is marked not_attempted, but the diff does not show a corresponding mechanism that guarantees every such defect is still carried into the code-reading judgement rather than being left without an execution-settled fallback.
- **reason:** the edit replaces 14 lines, over the 12-line bound; the smallest edit that makes the defect true is what was asked for

**edit** — `src/acceptance/mutation/verdicts.py` lines 85-98

```diff
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
+    settled = {attempt.defect_id for attempt in attempts if attempt.settled}
+    if not settled:
+        return list(defect_sets)
+
+    remaining: list[DefectSet] = []
+    for defect_set in defect_sets:
+        keep = [defect for defect in defect_set.defects if defect.id not in settled]
+        if not keep:
+            remaining.append(defect_set.model_copy(update={"defects": keep}))
+            continue
+        if len(keep) == len(defect_set.defects):
+            remaining.append(defect_set)
+            continue
+        remaining.append(defect_set.model_copy(update={"defects": keep}))
+    return remaining
```

## refused by a check — execution-could-not-settle-defects/not-mutable-defects-stop-at-static-judge

- **type:** `missing_case`
- **defect:** Defects that cannot be expressed as one contiguous edit are returned as not_mutable and then removed from the execution path, but the code shown does not demonstrate any later static pair-judgement path that still reaches a conclusion for those defects specifically.
- **reason:** the edit replaces 14 lines, over the 12-line bound; the smallest edit that makes the defect true is what was asked for

**edit** — `src/acceptance/mutation/verdicts.py` lines 85-98

```diff
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
+    settled = {attempt.defect_id for attempt in attempts if attempt.settled}
+    if not settled:
+        return list(defect_sets)
+
+    remaining: list[DefectSet] = []
+    for defect_set in defect_sets:
+        keep = [defect for defect in defect_set.defects if defect.id not in settled]
+        if not keep:
+            remaining.append(defect_set)
+            continue
+        if len(keep) == len(defect_set.defects):
+            remaining.append(defect_set)
+            continue
+        remaining.append(defect_set.model_copy(update={"defects": keep}))
+    return remaining
```

## refused by a check — injected-text-recorded-next-to-result/mutation-attempts-not-rendered-for-halted-or-disabled-reviews

- **type:** `scope_too_narrow`
- **defect:** The review only records injected text in the mutation block when execution ran and produced attempts; reviews that halt at the baseline gate or never opt into execution carry no injected-text record next to the result at all.
- **reason:** the replacement for src/acceptance/report.py lines 284..302 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/report.py` lines 284-302

```diff
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
```

## refused by a check — mechanical-validity-checks/descriptor-declines-on-malformed-span-instead-of-validating

- **type:** `other`
- **defect:** A descriptor with an invalid line span is treated as a decline and converted into not_mutable, so the mechanical validity stage never gets a chance to reject that edit as invalid on its own path.
- **reason:** the replacement for src/acceptance/mutation/descriptor.py lines 206..207 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/mutation/descriptor.py` lines 206-207

```diff
-    if result.start_line < 1 or result.end_line < result.start_line:
-        return None
+    if result.start_line < 1 or result.end_line < result.start_line:
+        return None
```

## refused by a check — no-edit-without-named-region/missing-no-region-report

- **type:** `other`
- **defect:** A defect with no named region is treated as not_mutable in the mutation runner, but the review/reporting path never surfaces that specific fact as an observable report that the defect cannot be edited.
- **reason:** the replacement for src/acceptance/report.py lines 131..133 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/report.py` lines 131-133

```diff
-    if review.mutation_attempts:
-        lines.extend(_mutation_block(review))
-        lines.append("")
+    if review.mutation_attempts:
+        lines.extend(_mutation_block(review))
+        lines.append("")
```

## refused by a check — no-line-execution-recording/mutation-tier-records-executed-lines

- **type:** `other`
- **defect:** The new mutation execution path records per-test verdicts and attempts, but it does not record which source lines each test executed; if the implementation later derives line-execution data from these mutation runs, that would be a different behavior than the criterion allows.
- **reason:** the replacement for src/acceptance/review_state.py lines 1263..1268 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/review_state.py` lines 1263-1268

```diff
-    mutation_attempts: list[MutationAttempt] = Field(default_factory=list)
-    # Candidate tests that took no part in any conclusion, and why. A test that
-    # failed against the code as delivered tells nothing when it fails under an
-    # injected defect, so it is excluded — and an exclusion nobody can see is
-    # indistinguishable from a test that was never a candidate.
-    set_aside_tests: list[SetAsideTest] = Field(default_factory=list)
+    mutation_attempts: list[MutationAttempt] = Field(default_factory=list)
+    # Candidate tests that took no part in any conclusion, and why. A test that
+    # failed against the code as delivered tells nothing when it fails under an
+    # injected defect, so it is excluded — and an exclusion nobody can see is
+    # indistinguishable from a test that was never a candidate.
+    set_aside_tests: list[SetAsideTest] = Field(default_factory=list)
```

## refused by a check — no-line-execution-recording/report-could-expose-executed-lines

- **type:** `other`
- **defect:** The report now renders mutation attempts and set-aside tests, so if any line-execution details were attached to those records elsewhere in the pipeline, this output path would surface them; the diff does not show a dedicated guard against recording executed line numbers.
- **reason:** the edit replaces 21 lines, over the 12-line bound; the smallest edit that makes the defect true is what was asked for

**edit** — `src/acceptance/report.py` lines 283-303

```diff
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
+            lines.append(f"    executed lines: {', '.join(map(str, attempt.executed_lines))}")
+    return lines
```

## refused by a check — no-parser-not-invalid/parser-map-misses-supported-file-types

- **type:** `scope_too_narrow`
- **defect:** The parser lookup only recognizes .py, .pyi, and .json, so any other file type that actually has a parser in this project would still be treated as having none and could be rejected for the wrong reason.
- **reason:** the replacement for src/acceptance/mutation/validity.py lines 52..56 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

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

## refused by a check — no-whole-suite-run/execution-tier-runs-whole-suite

- **type:** `other`
- **defect:** The new execution tier calls the project's test runner with the full candidate test list, and if that list is the whole suite then the implementation will execute the whole suite instead of avoiding it.
- **reason:** the replacement for src/acceptance/mutation/runner.py lines 81..92 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/mutation/runner.py` lines 81-92

```diff
-    return [
-        _attempt(
-            defect,
-            change_set,
-            project_root,
-            baseline.usable_tests,
-            build_descriptor,
-            config,
-            max_edit_lines,
-        )
-        for defect in defects
-    ]
+    return [
+        _attempt(
+            defect,
+            change_set,
+            project_root,
+            baseline.usable_tests,
+            build_descriptor,
+            config,
+            max_edit_lines,
+        )
+        for defect in defects
+    ]
```

## refused by a check — observation-not-prediction/mutation-attempts-can-carry-reason-only

- **type:** `other`
- **defect:** A non-settling mutation attempt is validated to carry only a reason, but the code does not show that the recorded conclusion itself is derived from an observed run; a caller could still treat the reasoned non-settling outcome as a prediction about the tests rather than an observation from running them.
- **reason:** the replacement for src/acceptance/mutation/verdicts.py lines 101..112 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/mutation/verdicts.py` lines 101-112

```diff
-def _reason(attempt: MutationAttempt, *, kills: bool) -> str:
-    """Short, and says that this was observed rather than predicted.
-
-    Kept short on purpose: DR-312 decision 3 holds a pair verdict's reason to a
-    sentence, because the caching discount is input-only and output growth never
-    amortizes.
-    """
-    if kills:
-        return "The test failed when the defect was injected."
-    if attempt.outcome is MutationOutcomeKind.KILLED:
-        return "The test still passed when the defect was injected; another test caught it."
-    return "The test still passed when the defect was injected."
+def _reason(attempt: MutationAttempt, *, kills: bool) -> str:
+    """Short, and says that this was observed rather than predicted.
+
+    Kept short on purpose: DR-312 decision 3 holds a pair verdict's reason to a
+    sentence, because the caching discount is input-only and output growth never
+    amortizes.
+    """
+    if kills:
+        return "The test failed when the defect was injected."
+    if attempt.outcome is MutationOutcomeKind.KILLED:
+        return "The test still passed when the defect was injected; another test caught it."
+    return "The test still passed when the defect was injected."
```

## refused by a check — parser-files-still-parse/json-parser-missing-from-validity-check

- **type:** `scope_too_narrow`
- **defect:** The validity check only parses .py and .pyi files, so a mutated .json file can be accepted even when it no longer parses.
- **reason:** the edit replaces 17 lines, over the 12-line bound; the smallest edit that makes the defect true is what was asked for

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

## refused by a check — preserve-current-review-conclusions-when-unrunnable/halted-baseline-drops-usable-tests-too-broadly

- **type:** `scope_too_narrow`
- **defect:** A failing candidate test at head halts the review even when the operator opted to allow failing tests, so some unrunnable-or-parked cases do not preserve the current review conclusions.
- **reason:** the replacement for src/acceptance/mutation/baseline.py lines 149..163 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/mutation/baseline.py` lines 149-163

```diff
-    failing = [test for test in set_aside if test.kind is TestOutcomeKind.FAILED]
-    if failing and not allow_failing_tests:
-        names = ", ".join(test.test_id for test in failing)
-        return Baseline(
-            set_aside=set_aside,
-            halted=True,
-            halt_reason=(
-                f"{len(failing)} candidate test(s) fail against the code as delivered "
-                f"({names}). A test that is already red says nothing when it goes red under "
-                "an injected defect, so nothing would be learned by continuing. Re-run "
-                "allowing failing tests to proceed with these set aside."
-            ),
-        )
-
-    return Baseline(usable_tests=usable, set_aside=set_aside)
+    failing = [test for test in set_aside if test.kind is TestOutcomeKind.FAILED]
+    if failing and not allow_failing_tests:
+        names = ", ".join(test.test_id for test in failing)
+        return Baseline(
+            set_aside=set_aside,
+            halted=True,
+            halt_reason=(
+                f"{len(failing)} candidate test(s) fail against the code as delivered "
+                f"({names}). A test that is already red says nothing when it goes red under "
+                "an injected defect, so nothing would be learned by continuing. Re-run "
+                "allowing failing tests to proceed with these set aside."
+            ),
+        )
+
+    return Baseline(usable_tests=usable, set_aside=set_aside)
```

## refused by a check — recorded-at-strongest-evidence-tier/review-records-weakest-tier-instead-of-strongest

- **type:** `condition_inverted`
- **defect:** The review state is populated from the weakest evidence tier among the verdicts it rests on, so a review that includes any executed `DEFECT_KILLED` evidence can still be recorded as `STATIC` instead of at the strongest tier it produces on its own.
- **reason:** the mutated src/acceptance/defects/support.py does not parse: unmatched ')' (<unknown>, line 281)

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

## refused by a check — report-lists-set-aside-tests/failing-tests-filtered-out-of-report

- **type:** `scope_too_narrow`
- **defect:** The report only names tests classified as `FAILED`; if a failing candidate test is represented with a different outcome kind or is recorded in `set_aside_tests` under another kind, the report will miss it even though it was set aside.
- **reason:** the replacement for src/acceptance/report.py lines 313..315 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/report.py` lines 313-315

```diff
-    for test in review.set_aside_tests:
-        lines.append(f"  [{test.kind.value}] {test.test_id}")
-        lines.append(f"    {test.reason}")
+    for test in review.set_aside_tests:
+        lines.append(f"  [{test.kind.value}] {test.test_id}")
+        lines.append(f"    {test.reason}")
```

## refused by a check — run-candidate-tests-on-altered-copy/execution-tier-disabled-by-default

- **type:** `scope_too_narrow`
- **defect:** The new execution tier is opt-in only, so the candidate tests are not run against the altered copy unless the caller passes --execute and the pipeline receives enabled execution settings.
- **reason:** the replacement for src/acceptance/pipeline.py lines 457..459 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/pipeline.py` lines 457-459

```diff
-    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
-        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
-    )
+    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
+        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
+    )
```

## refused by a check — run-candidate-tests-on-altered-copy/not-attempted-mutants-never-run-tests

- **type:** `missing_case`
- **defect:** When a defect is judged not_mutable or not_attempted, the runner returns before copying the project and before calling run_tests, so those defects never get candidate tests executed against an altered copy.
- **reason:** the edit replaces 24 lines, over the 12-line bound; the smallest edit that makes the defect true is what was asked for

**edit** — `src/acceptance/mutation/runner.py` lines 105-128

```diff
-    if not regions:
-        return _not_mutable(
-            defect,
-            "the defect names no changed region with text at head, so there is no span to "
-            "replace. This is the shape of an absence defect, where the implicated lines are "
-            "where behavior should be and is not.",
-        )
-
-    try:
-        sources = _sources(regions, project_root)
-    except OSError as error:
-        return _not_mutable(defect, f"a file the defect named could not be read: {error}")
-
-    readable = [region for region in regions if region.path in sources]
-    if not readable:
-        return _not_mutable(
-            defect, "none of the files the defect named exist in the project at head"
-        )
-
-    descriptor = build_descriptor(defect, readable, sources)
-    if descriptor is None:
-        return _not_mutable(
-            defect, "no single contiguous edit was found that would make this defect true"
-        )
+    if not regions:
+        return _not_mutable(
+            defect,
+            "the defect names no changed region with text at head, so there is no span to "
+            "replace. This is the shape of an absence defect, where the implicated lines are "
+            "where behavior should be and is not.",
+        )
+
+    try:
+        sources = _sources(regions, project_root)
+    except OSError as error:
+        return _not_mutable(defect, f"a file the defect named could not be read: {error}")
+
+    readable = [region for region in regions if region.path in sources]
+    if not readable:
+        return _not_mutable(
+            defect, "none of the files the defect named exist in the project at head"
+        )
+
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
+
+    try:
+        with mutated_copy(project_root, descriptor) as root:
+            result = run_tests(tests, root, config)
+    except OSError as error:
+        return MutationAttempt(
+            defect_id=defect.id,
+            outcome=MutationOutcomeKind.NOT_ATTEMPTED,
+            descriptor=descriptor,
+            reason=f"the mutated copy could not be prepared: {error}",
+        )
+
+    return _classify(defect, descriptor, tests, result)
```

## refused by a check — single-continuous-edit-in-named-region/apply-span-can-splice-wrong-file-text

- **type:** `wrong_output_shape`
- **defect:** The span application logic replaces text by line slicing only, so if the descriptor points at the wrong file or the wrong line span the resulting patch is still a single patch shape but not the one confined to the defect's named region.
- **reason:** the replacement for src/acceptance/mutation/validity.py lines 73..77 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

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
+    replacement = [descriptor.replacement] if descriptor.replacement else []
+    return "".join([*head, *replacement, *tail])
```

## refused by a check — single-continuous-edit-in-named-region/descriptor-not-constrained-to-named-region

- **type:** `other`
- **defect:** The descriptor builder can return an edit whose span is outside the defect's named region, so the applied patch would not be confined to the region the defect cited.
- **reason:** the replacement for src/acceptance/mutation/validity.py lines 119..124 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/mutation/validity.py` lines 119-124

```diff
-    if not any(region.contains(descriptor.start_line, descriptor.end_line) for region in named):
-        spans = ", ".join(f"{region.start_line}..{region.end_line}" for region in named)
-        return (
-            f"the span {descriptor.start_line}..{descriptor.end_line} falls outside the "
-            f"region(s) the defect named in {descriptor.path} ({spans})"
-        )
+    if not any(region.contains(descriptor.start_line, descriptor.end_line) for region in named):
+        spans = ", ".join(f"{region.start_line}..{region.end_line}" for region in named)
+        return (
+            f"the span {descriptor.start_line}..{descriptor.end_line} falls outside the "
+            f"region(s) the defect named in {descriptor.path} ({spans})"
+        )
```

## refused by a check — single-continuous-edit-in-named-region/region-resolution-drops-all-named-spans

- **type:** `missing_case`
- **defect:** A defect whose named region is absent from the resolved change set is treated as not mutable, so the criterion's coverage of edits within the named region can fall through unhandled for defects that cite deleted or unresolved code refs.
- **reason:** the replacement for src/acceptance/mutation/runner.py lines 105..111 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/mutation/runner.py` lines 105-111

```diff
-    if not regions:
-        return _not_mutable(
-            defect,
-            "the defect names no changed region with text at head, so there is no span to "
-            "replace. This is the shape of an absence defect, where the implicated lines are "
-            "where behavior should be and is not.",
-        )
+    if not regions:
+        return _not_mutable(
+            defect,
+            "the defect names no changed region with text at head, so there is no span to "
+            "replace. This is the shape of an absence defect, where the implicated lines are "
+            "where behavior should be and is not.",
+        )
```

## refused by a check — smallest-edit-that-makes-defect-true/descriptor-declines-when-edit-exists

- **type:** `missing_case`
- **defect:** A defect that does have a valid single-span edit can still be classified as not_mutable if the descriptor call returns an empty region label or the runner rejects the descriptor too aggressively, so the review may skip building an edit even though one exists.
- **reason:** the replacement for src/acceptance/mutation/descriptor.py lines 200..201 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/mutation/descriptor.py` lines 200-201

```diff
-    if not label:
-        return None
+    if not label:
+        return None
```

## refused by a check — smallest-edit-that-makes-defect-true/mutation-copy-applies-edit-to-wrong-file

- **type:** `other`
- **defect:** The injected edit could be applied to the wrong file if descriptor.path does not match the intended region or if the copy step targets the wrong path, so the throwaway copy would not contain the smallest edit for the named defect.
- **reason:** the replacement for src/acceptance/mutation/injection.py lines 53..59 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/mutation/injection.py` lines 53-59

```diff
-        target = root / descriptor.path
-        if not target.is_file():
-            raise FileNotFoundError(
-                f"{descriptor.path} is named by the change set but is not a file in the project"
-            )
-        source = target.read_text(encoding="utf-8")
-        target.write_text(apply_span(source, descriptor), encoding="utf-8")
+        target = root / descriptor.path
+        if not target.is_file():
+            raise FileNotFoundError(
+                f"{descriptor.path} is named by the change set but is not a file in the project"
+            )
+        source = target.read_text(encoding="utf-8")
+        target.write_text(apply_span(source, descriptor), encoding="utf-8")
```

## refused by a check — smallest-edit-that-makes-defect-true/validity-rejects-prose-defects-as-unmutable

- **type:** `missing_case`
- **defect:** The validity check only parses .py, .pyi, and .json files, so a defect in prose or another unparsed format can be rejected as not_mutable even when a smallest contiguous edit exists in that text.
- **reason:** the replacement for src/acceptance/mutation/validity.py lines 40..56 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

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

## refused by a check — stop-review-on-failing-candidate-test/failing-tests-set-aside-instead-of-stopping

- **type:** `condition_inverted`
- **defect:** The baseline reader turns failing candidate tests into `set_aside` entries and only halts when `allow_failing_tests` is false; if that gate is wrong-way-round, the review would continue when it should stop on a failing candidate test.
- **reason:** the mutated src/acceptance/mutation/baseline.py does not parse: unmatched ')' (<unknown>, line 162)

**edit** — `src/acceptance/mutation/baseline.py` lines 149-160

```diff
-    failing = [test for test in set_aside if test.kind is TestOutcomeKind.FAILED]
-    if failing and not allow_failing_tests:
-        names = ", ".join(test.test_id for test in failing)
-        return Baseline(
-            set_aside=set_aside,
-            halted=True,
-            halt_reason=(
-                f"{len(failing)} candidate test(s) fail against the code as delivered "
-                f"({names}). A test that is already red says nothing when it goes red under "
-                "an injected defect, so nothing would be learned by continuing. Re-run "
-                "allowing failing tests to proceed with these set aside."
-            ),
+    failing = [test for test in set_aside if test.kind is TestOutcomeKind.FAILED]
+    if failing and allow_failing_tests:
+        names = ", ".join(test.test_id for test in failing)
+        return Baseline(
+            set_aside=set_aside,
+            halted=True,
+            halt_reason=(
+                f"{len(failing)} candidate test(s) fail against the code as delivered "
+                f"({names}). A test that is already red says nothing when it goes red under "
+                "an injected defect, so nothing would be learned by continuing. Re-run "
+                "allowing failing tests to proceed with these set aside."
+            ),
+        )
```

## refused by a check — stop-review-on-failing-candidate-test/halt-message-loses-failing-test-reasons

- **type:** `wrong_output_shape`
- **defect:** The CLI prints only the failing test ids and a generic re-run hint when the review halts; if the criterion expects the emitted stopping reason to include the actual failure reason from the candidate test run, this output shape omits it.
- **reason:** the mutated src/acceptance/cli.py does not parse: unmatched ')' (<unknown>, line 971)

**edit** — `src/acceptance/cli.py` lines 965-969

```diff
-            for test in exc.baseline.failing_tests:
-                print(f"  failing at head: {test.test_id}", file=sys.stderr)
-            print(
-                "  re-run with --allow-failing-tests to proceed with these set aside.",
-                file=sys.stderr,
+            for test in exc.baseline.failing_tests:
+                print(f"  failing at head: {test.test_id}", file=sys.stderr)
+            print(
+                "  re-run with --allow-failing-tests to proceed with these set aside.",
+                file=sys.stderr,
+            )
```

## refused by a check — stop-review-on-failing-candidate-test/halt-path-not-triggered-from-cli

- **type:** `not_wired`
- **defect:** The new halt exception is only handled in `main`, but the review path can still call `run_check` directly with `execution` set; in that path a failing candidate test would not stop the review or emit the stopping reason.
- **reason:** the mutated src/acceptance/cli.py does not parse: unmatched ')' (<unknown>, line 213)

**edit** — `src/acceptance/cli.py` lines 206-209

```diff
-        prior=prior,
-        ledger_prior=ledger.read_if_present(continue_from) if ledger is not None else None,
-        ledger_sink=sink,
-        execution=execution,
+        prior=prior,
+        ledger_prior=ledger.read_if_present(continue_from) if ledger is not None else None,
+        ledger_sink=sink,
+        execution=execution,
+    )
+    if execution is not None and execution.enabled and review.baseline.failing_tests and not execution.allow_failing_tests:
+        raise ReviewHalted(review.baseline)
```

## refused by a check — test-fails-discriminate-defect/failing-tests-not-marked-as-discriminating

- **type:** `other`
- **defect:** When a candidate test fails against the altered copy, the execution verdict is recorded with `kills=True` and `tier=DEFECT_KILLED`, but the code never explicitly marks the corresponding review finding or pair verdict as 'discriminates for that defect'; if the downstream review/reporting path only treats `kills` as a generic failure signal, the review could omit the discrimination claim the criterion asks for.
- **reason:** the mutated src/acceptance/mutation/verdicts.py does not parse: unmatched ')' (<unknown>, line 69)

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
+            verdict = PairVerdict(
+                defect_id=attempt.defect_id,
+                test_id=test_id,
+                kills=test_id in killing,
+                reason=_reason(attempt, kills=test_id in killing),
+                tier=EvidenceTier.DEFECT_KILLED,
+                defect_text=texts.get(attempt.defect_id, ""),
+            )
+            if test_id in killing:
+                verdict.reason = "The test failed when the defect was injected."
+            verdicts.append(verdict)
```

## refused by a check — test-fails-discriminate-defect/survival-path-only-records-failures

- **type:** `scope_too_narrow`
- **defect:** `verdicts_from` emits verdicts only for settled attempts, so if a mutant is classified as `NOT_ATTEMPTED` because some tests did not complete, any failing candidate test from that run is not recorded as discriminating for the defect even though the criterion is about a test that fails against the altered copy.
- **reason:** the edit replaces 16 lines, over the 12-line bound; the smallest edit that makes the defect true is what was asked for

**edit** — `src/acceptance/mutation/verdicts.py` lines 53-68

```diff
-    for attempt in attempts:
-        if not attempt.settled:
-            continue
-        killing = set(attempt.killing_tests)
-        for test_id in attempt.tests_run:
-            verdicts.append(
-                PairVerdict(
-                    defect_id=attempt.defect_id,
-                    test_id=test_id,
-                    kills=test_id in killing,
-                    reason=_reason(attempt, kills=test_id in killing),
-                    tier=EvidenceTier.DEFECT_KILLED,
-                    defect_text=texts.get(attempt.defect_id, ""),
-                )
-            )
-    return verdicts
+    verdicts: list[PairVerdict] = []
+    for attempt in attempts:
+        if not attempt.settled:
+            killing = set(attempt.killing_tests)
+            for test_id in attempt.tests_run:
+                if test_id not in killing:
+                    continue
+                verdicts.append(
+                    PairVerdict(
+                        defect_id=attempt.defect_id,
+                        test_id=test_id,
+                        kills=True,
+                        reason=_reason(attempt, kills=True),
+                        tier=EvidenceTier.DEFECT_KILLED,
+                        defect_text=texts.get(attempt.defect_id, ""),
+                    )
+                )
+            continue
+        killing = set(attempt.killing_tests)
+        for test_id in attempt.tests_run:
+            verdicts.append(
+                PairVerdict(
+                    defect_id=attempt.defect_id,
+                    test_id=test_id,
+                    kills=test_id in killing,
+                    reason=_reason(attempt, kills=test_id in killing),
+                    tier=EvidenceTier.DEFECT_KILLED,
+                    defect_text=texts.get(attempt.defect_id, ""),
+                )
+            )
+    return verdicts
```

## refused by a check — tests-candidate-selection/baseline-halt-changes-run-eligibility

- **type:** `other`
- **defect:** The new baseline control run can halt review execution when a candidate test already fails at head, which changes the decision about whether tests can be run at all instead of leaving that decision unchanged.
- **reason:** the edit replaces 13 lines, over the 12-line bound; the smallest edit that makes the defect true is what was asked for

**edit** — `src/acceptance/mutation/baseline.py` lines 149-161

```diff
-    failing = [test for test in set_aside if test.kind is TestOutcomeKind.FAILED]
-    if failing and not allow_failing_tests:
-        names = ", ".join(test.test_id for test in failing)
-        return Baseline(
-            set_aside=set_aside,
-            halted=True,
-            halt_reason=(
-                f"{len(failing)} candidate test(s) fail against the code as delivered "
-                f"({names}). A test that is already red says nothing when it goes red under "
-                "an injected defect, so nothing would be learned by continuing. Re-run "
-                "allowing failing tests to proceed with these set aside."
-            ),
-        )
+    failing = [test for test in set_aside if test.kind is TestOutcomeKind.FAILED]
+    if failing and not allow_failing_tests:
+        names = ", ".join(test.test_id for test in failing)
+        return Baseline(
+            set_aside=set_aside,
+            halted=True,
+            halt_reason=(
+                f"{len(failing)} candidate test(s) fail against the code as delivered "
+                f"({names}). A test that is already red says nothing when it goes red under "
+                "an injected defect, so nothing would be learned by continuing. Re-run "
+                "allowing failing tests to proceed with these set aside."
+            ),
+        )
+
+    return Baseline(usable_tests=usable, set_aside=set_aside)
```

## refused by a check — tests-candidate-selection/execution-tier-alters-candidate-selection

- **type:** `other`
- **defect:** The new execution tier changes which tests are treated as candidates by filtering the mutation run to `baseline.usable_tests` instead of the full discovered test list, so tests that fail at head are removed from later consideration rather than merely being reported separately.
- **reason:** the edit replaces 22 lines, over the 12-line bound; the smallest edit that makes the defect true is what was asked for

**edit** — `src/acceptance/mutation/runner.py` lines 71-92

```diff
-    if not baseline.usable_tests:
-        return [
-            _not_attempted(
-                defect,
-                "no candidate test survived the control run, so there is nothing a mutant "
-                "could be observed against",
-            )
-            for defect in defects
-        ]
-
-    return [
-        _attempt(
-            defect,
-            change_set,
-            project_root,
-            baseline.usable_tests,
-            build_descriptor,
-            config,
-            max_edit_lines,
-        )
-        for defect in defects
-    ]
+    return [
+        _attempt(
+            defect,
+            change_set,
+            project_root,
+            baseline.usable_tests,
+            build_descriptor,
+            config,
+            max_edit_lines,
+        )
+        for defect in defects
+    ]
```

## refused by a check — weaker-tier-evidence/review-model-does-not-persist-mutation-evidence

- **type:** `not_wired`
- **defect:** The `Review` model has fields for mutation attempts and set-aside tests, but if the pipeline never populates them on the delivered path, the stored review cannot record the weaker evidence tier even when execution ran.
- **reason:** the replacement for src/acceptance/pipeline.py lines 643..644 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**edit** — `src/acceptance/pipeline.py` lines 643-644

```diff
-        mutation_attempts=attempts,
-        set_aside_tests=set_aside_tests,
+        mutation_attempts=attempts,
+        set_aside_tests=set_aside_tests,
```
