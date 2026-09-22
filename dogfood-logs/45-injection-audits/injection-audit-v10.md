# Defect injection audit v10 — #45, head 518f876f7b8eb39860cd2d309b86abd6c07925eb

Audit v6's defects for 22 criteria (left out: candidate-tests-run-once-before-changes, recorded-at-strongest-evidence-tier, stop-review-on-failing-candidate-test). Edits on openai/gpt-5.4, up to 3 candidates each; verification on, openai/gpt-5.4.

64 defects, 339 usable candidate tests.

- **already_present:** 12
- **killed:** 38
- **survived:** 14

## `killed` — candidate-tests-not-discriminate-when-none-fail/no-discriminate-report-not-wired

- **type:** `not_wired`
- **defect:** The execution path can run the mutation stage and record injected attempts, but the review/reporting path never turns the all-survived case into the required 'candidate tests do not discriminate' conclusion, so a no-fail run can finish without that observation being reported.
- **expected:** When every candidate test survives the injected defect, the review path should emit the non-discrimination conclusion for that defect and record it in the review output.
- **defective:** The code records mutation attempts and verdicts, but the delivered review path omits or bypasses the specific no-fail conclusion, so the review can end without saying the candidate tests do not discriminate.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 2

**edit** — `src/acceptance/report.py` lines 131-133

```diff
-    if review.mutation_attempts:
-        lines.extend(_mutation_block(review))
-        lines.append("")
+    if review.mutation_attempts and review.set_aside_tests:
+        lines.extend(_mutation_block(review))
+        lines.append("")
```

## `killed` — candidate-tests-not-discriminate-when-none-fail/survival-classified-as-set-aside

- **type:** `condition_inverted`
- **defect:** A mutant run with no red tests can be classified as not_attempted instead of survived if the unobserved-test check is treated as the deciding condition, so the code may fail to report non-discrimination even though every candidate test completed and passed.
- **expected:** When the mutant run completes and no candidate test fails, the attempt should be classified as survived so the review can report that the candidate tests did not discriminate.
- **defective:** The code treats the absence of red tests as a non-settling or incomplete run and routes the attempt to not_attempted instead of survived, preventing the non-discrimination conclusion from being recorded.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 15

**edit** — `src/acceptance/mutation/runner.py` lines 178-178

```diff
-    if unobserved:
+    if not unobserved:
```

## `killed` — candidate-tests-not-discriminate-when-none-fail/survival-not-propagated-to-review-state

- **type:** `not_wired`
- **defect:** The mutation runner can produce survived attempts, but those attempts may not be propagated into the stored review state or rendered report in a way that the no-fail conclusion is visible to callers.
- **expected:** Survived mutation attempts should be carried through the pipeline into the review object and report so that a no-fail run is observable as non-discrimination.
- **defective:** The pipeline may compute attempts and verdicts but fail to wire them into the final review/report path that the caller sees, so the review does not actually show the non-discrimination result.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 4

**edit** — `src/acceptance/pipeline.py` lines 643-643

```diff
-        mutation_attempts=attempts,
+        mutation_attempts=[],
```

## `killed` — carry-reason-for-non-settlement/baseline-set-aside-reason-defaults-to-generic-text

- **type:** `other`
- **defect:** The baseline control run fabricates a generic reason for every failing or otherwise non-passing candidate test, so the recorded reason may not actually explain the non-settlement that occurred.
- **expected:** When a defect execution does not settle, the recorded reason should be the actual reason returned by the execution stage for that attempt.
- **defective:** The code substitutes a canned fallback reason instead of preserving the execution-stage reason, so the record can misstate why the attempt did not settle.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 1

**edit** — `src/acceptance/mutation/baseline.py` lines 145-145

```diff
-                reason=outcome.reason or "the test failed against the code as delivered",
+                reason="the test failed against the code as delivered",
```

## `killed` — carry-reason-for-non-settlement/not-attempted-missing-reason

- **type:** `other`
- **defect:** Unsettled mutation attempts can be created without any reason text, so a non-settling defect execution would be recorded with an empty reason.
- **expected:** Every MutationAttempt whose outcome is not settled must carry a non-empty reason explaining why execution did not settle the defect.
- **defective:** A non-settling MutationAttempt is accepted or constructed with an empty reason, so the record does not explain the non-settlement.
- **candidates asked:** 2
- **candidate used:** 2
- **candidate 1 set aside:** `refused_after_run` — 46 of the 339 candidate tests failed under the edit, more than 7.5% of them. An edit that makes one defect true fails the tests near it; one that fails this many has broken something shared, so the failures say nothing about the named defect and no kill is counted.
- **tests failing:** 21

**refused candidate 1** — `src/acceptance/mutation/attempt.py` lines 127-127

```diff
-        if not self.settled and not has_reason:
+        if self.settled and not has_reason:
```

**edit** — `src/acceptance/mutation/attempt.py` lines 127-127

```diff
-        if not self.settled and not has_reason:
+        if self.outcome is MutationOutcomeKind.KILLED and not has_reason:
```

## `killed` — carry-reason-for-non-settlement/not-attempted-path-loses-reason

- **type:** `other`
- **defect:** The mutation runner can return a not_attempted outcome with a reason, but the classification path for partially observed runs may drop or replace that reason before the attempt is stored.
- **expected:** Any defect execution classified as not_attempted must be stored with the reason produced by the runner.
- **defective:** The runner or its caller records the non-settlement outcome without preserving the reason, leaving the attempt reason empty or replaced.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 3

**edit** — `src/acceptance/mutation/runner.py` lines 184-184

```diff
-            reason=_why_unobserved(unobserved, result.outcomes),
+            reason="",
```

## `survived` — continue-with-set-aside-tests/allow-failing-tests-not-propagated

- **type:** `not_wired`
- **defect:** The continue-anyway flag is accepted on the CLI but never reaches the execution tier, so failing candidate tests still halt the review instead of being set aside.
- **expected:** The CLI passes the configured continue-anyway setting into the review pipeline, and the baseline run uses it to decide whether failing candidate tests are set aside or halt the review.
- **defective:** The CLI parses the flag but does not pass it into the pipeline or baseline logic, so the baseline run always behaves as if continuing were disabled.
- **candidates asked:** 1
- **candidate used:** 1

**edit** — `src/acceptance/cli.py` lines 209-209

```diff
-        execution=execution,
+        execution=None,
```

## `killed` — continue-with-set-aside-tests/failing-tests-not-listed-in-report

- **type:** `wrong_output_shape`
- **defect:** The review records set-aside tests internally but the report does not identify which failing candidate tests were set aside, so the observable output does not show the exclusion list.
- **expected:** When failing candidate tests are set aside, the report renders those tests by name and reason so a reader can see exactly which tests took no part in the conclusion.
- **defective:** The report either omits the set-aside tests entirely or renders them only as a generic note without naming the tests that were excluded.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 1

**edit** — `src/acceptance/report.py` lines 313-315

```diff
-    for test in review.set_aside_tests:
-        lines.append(f"  [{test.kind.value}] {test.test_id}")
-        lines.append(f"    {test.reason}")
+    lines.append(f"  {len(review.set_aside_tests)} test(s) were set aside")
```

## `survived` — continue-with-set-aside-tests/set-aside-tests-still-count-in-conclusions

- **type:** `other`
- **defect:** Set-aside failing candidate tests are still fed into later support or verdict aggregation, so they continue to influence the conclusion even though they were supposed to be excluded.
- **expected:** Once a candidate test is set aside for failing at head, it is removed from the evidence used to form conclusions and does not contribute to derived support or verdict-based ratings.
- **defective:** The code keeps set-aside failing tests in the verdict/support inputs, so they still affect the conclusion despite being marked excluded.
- **candidates asked:** 1
- **candidate used:** 1

**edit** — `src/acceptance/pipeline.py` lines 509-509

```diff
-    support = derive_support(needs_tests, defect_sets, verdicts, pair_mapping.unjudged)
+    support = derive_support(needs_tests, defect_sets, verdicts + [v for v in pair_mapping.verdicts if v.test_id in set_aside_tests], pair_mapping.unjudged)
```

## `killed` — does-not-run-first/execution-path-not-wired-into-review-flow

- **type:** `not_wired`
- **defect:** The execution-stage machinery exists, but the review flow may never call it on the delivered path, leaving the code-reading judgement as the effective first stage.
- **expected:** The review pipeline should invoke the execution-based stage before the static judgement whenever execution is enabled for a review.
- **defective:** The execution-stage functions are defined, but the review path does not actually route through them before the code-reading judgement runs.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 16

**edit** — `src/acceptance/pipeline.py` lines 457-459

```diff
-    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
-        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
-    )
+    attempts, executed_verdicts, set_aside_tests = [], [], []
```

## `already_present` — does-not-run-first/execution-tier-only-runs-when-explicitly-enabled

- **type:** `scope_too_narrow`
- **defect:** The execution-based review is gated behind an opt-in flag, so the code-reading judgement still runs first on the default path where execution is disabled.
- **expected:** For the criterion to hold, execution-based review must precede the code-reading judgement on the normal review flow, not only when an explicit execution flag is supplied.
- **defective:** Execution-based review happens before the code-reading judgement only when `--execute` is set; otherwise the static judgement remains the first pass.
- **reason:** The current CLI passes `enabled=args.execute` at src/acceptance/cli.py lines 951-953, so execution-based review runs before static judgement only when `--execute` is explicitly supplied; otherwise execution is disabled on the normal path.
- **candidates asked:** 1
- **candidate used:** None

- **repair corroboration:** a_test_asserts_defective
- **tests failing on the repair:** 1

**repair** — `src/acceptance/cli.py` lines 952-952

```diff
-                    enabled=args.execute,
+                    enabled=True,
```

## `killed` — does-not-run-first/static-judgement-still-runs-before-execution

- **type:** `condition_inverted`
- **defect:** The review pipeline still reaches the code-reading judgement before the execution-based mutation stage, so the later-stage review is not actually deferred.
- **expected:** The execution-based review runs first, and only after it finishes does the code-reading judgement run on whatever execution could not settle.
- **defective:** The code-reading judgement runs before the execution-based review, making it the initial pass instead of a later-stage review.
- **candidates asked:** 2
- **candidate used:** 2
- **candidate 1 set aside:** `refused_after_run` — every one of the 82 tests that failed under the edit failed with NameError, which means the edited code no longer loads or names something that does not exist. Those failures say nothing about the named defect, so this is not counted as a kill and the defect goes to the static judge.
- **tests failing:** 16

**refused candidate 1** — `src/acceptance/pipeline.py` lines 457-468

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
-        discovered.tests,
-        change_set,
-        client,
+    pair_mapping = judge_pairs(
+        # Only the defects injection could not reach. The FULL `defect_sets` still
+        # goes to `derive_support` below, so a criterion's denominator is
+        # unchanged — what shrinks is the question put to the model, not the bar.
+        remaining_defect_sets(attempts, defect_sets),
+        discovered.tests,
+        change_set,
+        client,
```

**edit** — `src/acceptance/pipeline.py` lines 457-459

```diff
-    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
-        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
-    )
+    attempts, executed_verdicts, set_aside_tests = [], [], []
```

## `killed` — execution-could-not-settle-defects/execution-disabled-skips-static-judgement

- **type:** `not_wired`
- **defect:** The execution tier is gated off entirely, so defects that execution could not settle never reach the code-reading judgement.
- **expected:** When execution cannot settle a defect, the review still invokes the static judgement on that defect and records the resulting conclusion.
- **defective:** The pipeline returns with no static judgement for unsettled defects because the execution tier is disabled or bypassed before the code-reading stage runs.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 3

**edit** — `src/acceptance/pipeline.py` lines 465-465

```diff
-        remaining_defect_sets(attempts, defect_sets),
+        defect_sets,
```

## `already_present` — execution-could-not-settle-defects/halted-baseline-prevents-static-fallback

- **type:** `condition_inverted`
- **defect:** A baseline failure stops the review instead of routing the unsettled defects to the static judgement, so the code-reading conclusion is lost when execution cannot settle because the candidate tests already fail.
- **expected:** When the control run cannot support execution, the review still reaches the static judgement for the defects execution could not settle, or otherwise records that code-reading evidence was used.
- **defective:** Any failing candidate test at head halts the review before the static judgement runs, so unsettled defects never receive a code-reading conclusion.
- **reason:** The code already halts the review before static judgement when the baseline is halted: src/acceptance/pipeline.py lines 284-285 raise ReviewHalted(baseline), and run_review calls _run_execution_tier before judge_pairs at lines 457-474, so unsettled defects do not reach static judgement.
- **candidates asked:** 1
- **candidate used:** None

- **repair corroboration:** a_test_asserts_defective
- **tests failing on the repair:** 16

**repair** — `src/acceptance/pipeline.py` lines 284-285

```diff
-    if baseline.halted:
-        raise ReviewHalted(baseline)
+    if not baseline.halted:
+        raise ReviewHalted(baseline)
```

## `survived` — execution-could-not-settle-defects/not-attempted-defects-never-fed-to-static-judge

- **type:** `missing_case`
- **defect:** Defects that execution could not settle because the edit could not be built, or because the code could not be run, may be recorded as terminal outcomes but never handed to the code-reading judgement.
- **expected:** Defects whose edit could not be built, and defects that could not be run, are still passed to the static judgement so the review can conclude from code-reading evidence.
- **defective:** Those not_mutable and not_attempted defects are recorded as execution outcomes only, but the remaining defect set given to the static judgement omits them or drops them from consideration.
- **candidates asked:** 1
- **candidate used:** 1

**edit** — `src/acceptance/mutation/verdicts.py` lines 85-85

```diff
-    settled = {attempt.defect_id for attempt in attempts if attempt.settled}
+    settled = {
+        attempt.defect_id
+        for attempt in attempts
+        if attempt.settled or attempt.outcome is MutationOutcomeKind.NOT_ATTEMPTED
+    }
```

## `killed` — execution-could-not-settle-defects/unsettled-defects-dropped-from-review-state

- **type:** `wrong_output_shape`
- **defect:** The review stores mutation attempts, but unsettled defects could be omitted or stored in a form the later judgement cannot consume, so the code-reading conclusion would never be recorded for them.
- **expected:** Every defect execution could not settle is represented in the review state in a form that the later static judgement can read and use.
- **defective:** Unsettled defects are either not stored at all or are stored only as execution-stage records that are never converted into the static judgement input.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 6

**edit** — `src/acceptance/mutation/verdicts.py` lines 85-85

```diff
-    settled = {attempt.defect_id for attempt in attempts if attempt.settled}
+    settled = {attempt.defect_id for attempt in attempts if attempt.outcome is MutationOutcomeKind.KILLED}
```

## `killed` — injected-text-recorded-next-to-result/mutation-attempts-without-descriptor-cannot-record-injected-text

- **type:** `missing_case`
- **defect:** A settled mutation attempt can be created without a descriptor, which means the review can record an outcome without any injected text to display next to it.
- **expected:** Any settled mutation attempt should carry the descriptor for the injected edit so the result can include the exact injected text.
- **defective:** The attempt record allows a settled outcome to exist with no descriptor, so the review can store the result but has no injected text to show beside it.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 1

**edit** — `src/acceptance/mutation/attempt.py` lines 151-155

```diff
-        if self.settled and self.descriptor is None:
-            raise ValueError(
-                f"defect {self.defect_id!r} is recorded as {self.outcome.value} with no "
-                "descriptor, so there is no record of what was injected"
-            )
+        if self.settled and self.descriptor is None and self.outcome is MutationOutcomeKind.KILLED:
+            raise ValueError(
+                f"defect {self.defect_id!r} is recorded as {self.outcome.value} with no "
+                "descriptor, so there is no record of what was injected"
+            )
```

## `survived` — injected-text-recorded-next-to-result/mutation-block-omits-injected-text-for-unsettled-attempts

- **type:** `scope_too_narrow`
- **defect:** The report only shows the injected text when an attempt is settled, so not-mutable or not-attempted defects can be listed without the injected text that explains what was injected or why the attempt could not be settled.
- **expected:** Every mutation attempt that is recorded in the review should render the injected text alongside the result entry, including attempts that end as not_mutable or not_attempted when they have a descriptor.
- **defective:** The mutation report skips the injected text for attempts that are not settled and only prints the reason, leaving the result without the injected text next to it.
- **candidates asked:** 1
- **candidate used:** 1

**edit** — `src/acceptance/report.py` lines 288-292

```diff
-        if descriptor is not None:
-            span = f"{descriptor.start_line}-{descriptor.end_line}"
-            lines.append(f"    injected at {descriptor.path} lines {span}:")
-            for line in descriptor.replacement.splitlines() or [""]:
-                lines.append(f"      | {line}")
+        if descriptor is not None and attempt.settled:
+            span = f"{descriptor.start_line}-{descriptor.end_line}"
+            lines.append(f"    injected at {descriptor.path} lines {span}:")
+            for line in descriptor.replacement.splitlines() or [""]:
+                lines.append(f"      | {line}")
```

## `killed` — mechanical-validity-checks/containment-check-only-uses-resolved-regions

- **type:** `scope_too_narrow`
- **defect:** The containment check only looks at regions that were resolved from the change set, so a defect with no resolved region can still be treated as mutable instead of being rejected mechanically.
- **expected:** If a defect names no editable region, mechanical validity rejects the edit as not mutable before any execution happens.
- **defective:** A defect with no resolved region can still reach later validity steps or be treated as valid because the containment check only runs after regions are found.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 1

**edit** — `src/acceptance/mutation/runner.py` lines 105-111

```diff
-    if not regions:
-        return _not_mutable(
-            defect,
-            "the defect names no changed region with text at head, so there is no span to "
-            "replace. This is the shape of an absence defect, where the implicated lines are "
-            "where behavior should be and is not.",
-        )
```

## `already_present` — mechanical-validity-checks/descriptor-declines-are-not-mechanically-enforced

- **type:** `unenforced_on_one_path`
- **defect:** A descriptor that declines by returning an empty region label is converted to None, but the runner still has to rely on later control flow to mark the defect not mutable, so the mechanical validity decision is not enforced at the descriptor boundary itself.
- **expected:** A declined descriptor is mechanically rejected as not mutable at the point the descriptor is interpreted, with no later stage able to treat it as a valid edit.
- **defective:** The descriptor builder can return None for a decline, and the runner separately turns that into not_mutable, leaving the validity decision unenforced at the descriptor stage.
- **reason:** The current code matches the DEFECTIVE behavior: in src/acceptance/mutation/descriptor.py lines 199-201, `_descriptor_from` strips `result.region_label` and returns `None` when it is empty, so a decline is converted to `None` at the descriptor stage. The runner then separately interprets `None` as not mutable in src/acceptance/mutation/runner.py lines 124-128.
- **candidates asked:** 1
- **candidate used:** None

- **repair corroboration:** a_test_asserts_defective
- **tests failing on the repair:** 3

**repair** — `src/acceptance/mutation/descriptor.py` lines 200-201

```diff
-    if not label:
-        return None
+    if not label:
+        raise ValueError("declined descriptor is not mutable")
```

## `survived` — mechanical-validity-checks/mechanical-checks-bypassable-through-execution-settings

- **type:** `other`
- **defect:** The new execution path can decide whether an edit is valid by running tests and halting or proceeding, so edit validity is no longer settled only by the mechanical validity checks.
- **expected:** Mechanical validity checks alone determine whether a mutation descriptor is valid, and execution settings only affect whether execution runs after validity is established.
- **defective:** The execution tier can short-circuit or override the validity decision by halting on baseline failures or proceeding past them, so validity depends on execution control flow as well as mechanical checks.
- **candidates asked:** 1
- **candidate used:** 1

**edit** — `src/acceptance/pipeline.py` lines 284-285

```diff
-    if baseline.halted:
-        raise ReviewHalted(baseline)
+    if baseline.halted and not execution.allow_failing_tests:
+        raise ReviewHalted(baseline)
```

## `survived` — mechanical-validity-checks/parse-check-applies-only-to-some-file-types

- **type:** `scope_too_narrow`
- **defect:** The parse validity check only covers a small hardcoded set of suffixes, so files with another parser can be mutated without being checked for parse validity.
- **expected:** Any file type that has a parser must be re-parsed after the edit, so malformed mutants are rejected mechanically for every parseable file type the criterion covers.
- **defective:** Only .py, .pyi, and .json files are parsed after mutation, so other parseable file types can slip through validity checks even when the edit breaks them.
- **candidates asked:** 2
- **candidate used:** 2
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/mutation/validity.py lines 52..56 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**refused candidate 1** — `src/acceptance/mutation/validity.py` lines 52-56

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

**edit** — `src/acceptance/mutation/validity.py` lines 138-142

```diff
-def _parser_for(path: str):
-    for suffix, parse in _PARSERS.items():
-        if path.endswith(suffix):
-            return parse
-    return None
+def _parser_for(path: str):
+    for suffix, parse in _PARSERS.items():
+        if suffix in {".py", ".pyi", ".json"} and path.endswith(suffix):
+            return parse
+    return None
```

## `killed` — no-edit-without-named-region/missing-region-not-reported-as-not-editable

- **type:** `other`
- **defect:** A defect that names no region is treated as if it were merely missing a descriptor and is routed to the generic 'not mutable' path without explicitly reporting that it cannot be edited because no region was named.
- **expected:** When a defect has no named region, the review should report that the defect cannot be edited because there is no region to edit within.
- **defective:** When a defect has no named region, the review only reports a generic inability to mutate or a missing edit span, without stating that the defect is not editable for lack of a named region.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 1

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
+            "no single contiguous edit was found that would make this defect true",
+        )
```

## `killed` — no-line-execution-recording/execution-tier-still-derives-line-coverage

- **type:** `other`
- **defect:** The new execution tier still feeds line-coverage-style evidence into support derivation, so the system continues to record which lines tests executed indirectly through evidence tier bookkeeping.
- **expected:** The delivered code should avoid recording executed lines as evidence and should only record test outcomes or mutation results relevant to the criterion.
- **defective:** The delivered code derives support from execution data that encodes line coverage or executed-line information, thereby preserving line-execution recording under a different name.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 3

**edit** — `src/acceptance/pipeline.py` lines 479-479

```diff
-    verdicts = executed_verdicts + pair_mapping.verdicts
+    verdicts = pair_mapping.verdicts
```

## `survived` — no-line-execution-recording/line-execution-recording-still-present

- **type:** `other`
- **defect:** The review report or review state still includes a field or block that records executed line information, so the change continues to persist or render line execution data.
- **expected:** The delivered code should not store or display which lines of code a test executed anywhere in the review output or persisted review state.
- **defective:** The delivered code stores or renders line-execution information such as executed line spans, coverage line records, or a report section that lists executed lines.
- **candidates asked:** 1
- **candidate used:** 1

**edit** — `src/acceptance/report.py` lines 293-295

```diff
-        if attempt.killing_tests:
-            lines.append(f"    caught by ({len(attempt.killing_tests)}):")
-            lines.extend(f"      {test_id}" for test_id in attempt.killing_tests)
+        if attempt.killing_tests:
+            lines.append(f"    caught by ({len(attempt.killing_tests)}):")
+            lines.extend(f"      {test_id} lines {span}" for test_id in attempt.killing_tests)
```

## `killed` — no-parser-not-invalid/parse-failure-becomes-not-mutable

- **type:** `other`
- **defect:** A malformed parse is converted into a generic not-mutable rejection, so the code can still be treating parser absence as an invalidity path instead of merely skipping the parse check for files that have no parser.
- **expected:** A file with no parser should pass validity on that ground alone, with parse-related rejection reserved for files that actually have a parser and fail it.
- **defective:** The validity path collapses parser-related cases into a not-mutable rejection, making parser absence function like a violation instead of a non-issue.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 2

**edit** — `src/acceptance/mutation/validity.py` lines 128-134

```diff
-    if parse is not None:
-        mutated = apply_span(source, descriptor)
-        try:
-            parse(mutated)
-        except _PARSE_ERRORS as error:
-            return f"the mutated {descriptor.path} does not parse: {error}"
-
+    if parse is None:
+        return "the mutated file is not mutable because it has no parser"
+    mutated = apply_span(source, descriptor)
+    try:
+        parse(mutated)
+    except _PARSE_ERRORS as error:
+        return f"the mutated {descriptor.path} does not parse: {error}"
```

## `survived` — no-parser-not-invalid/parser-check-applies-to-all-files

- **type:** `scope_too_narrow`
- **defect:** The parse check only covers a fixed set of extensions, so a file type that does have a parser but is not listed can still be rejected or mishandled as if lacking one.
- **expected:** Any file type that has a parser should be treated as valid when its mutated text still parses under that parser.
- **defective:** Only the hardcoded extensions in the parser table are recognized, and other parseable file types are treated as outside the rule or invalid by omission.
- **candidates asked:** 1
- **candidate used:** 1

**edit** — `src/acceptance/mutation/validity.py` lines 138-142

```diff
-def _parser_for(path: str):
-    for suffix, parse in _PARSERS.items():
-        if path.endswith(suffix):
-            return parse
-    return None
+def _parser_for(path: str):
+    return _PARSERS.get(path[path.rfind(".") :])
```

## `killed` — no-parser-not-invalid/parserless-files-still-rejected

- **type:** `condition_inverted`
- **defect:** Files without a parser are still treated as invalid, so the new validity check rejects them instead of allowing prose-only files to be mutated.
- **expected:** When a file has no parser, the validity check should skip the parse requirement and treat the file as valid on that ground.
- **defective:** When a file has no parser, the validity check reports the file invalid solely because no parser is available.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 2

**edit** — `src/acceptance/mutation/validity.py` lines 128-134

```diff
-    if parse is not None:
-        mutated = apply_span(source, descriptor)
-        try:
-            parse(mutated)
-        except _PARSE_ERRORS as error:
-            return f"the mutated {descriptor.path} does not parse: {error}"
-
+    if parse is None:
+        return f"the mutated {descriptor.path} does not parse: no parser available"
+    mutated = apply_span(source, descriptor)
+    try:
+        parse(mutated)
+    except _PARSE_ERRORS as error:
+        return f"the mutated {descriptor.path} does not parse: {error}"
```

## `survived` — no-whole-suite-run/baseline-control-run-uses-all-tests

- **type:** `other`
- **defect:** The control run before mutation can execute every discovered test instead of only the named candidates, so the review may observe whole-suite execution before any defect injection happens.
- **expected:** The baseline run should be limited to the candidate tests named for the review.
- **defective:** The baseline establishment takes the full test id list and runs them all, which can amount to executing the project's whole suite.
- **candidates asked:** 2
- **candidate used:** 2
- **candidate 1 set aside:** `refused_after_run` — 33 of the 339 candidate tests failed under the edit, more than 7.5% of them. An edit that makes one defect true fails the tests near it; one that fails this many has broken something shared, so the failures say nothing about the named defect and no kill is counted.

**refused candidate 1** — `src/acceptance/mutation/baseline.py` lines 129-129

```diff
-    result = run_tests(requested, project_root, config)
+    result = run_tests([], project_root, config)
```

**edit** — `src/acceptance/mutation/baseline.py` lines 129-129

```diff
-    result = run_tests(requested, project_root, config)
+    result = run_tests(test_ids, project_root, config)
```

## `killed` — no-whole-suite-run/whole-suite-execution-flag

- **type:** `other`
- **defect:** The new execution path can still run the project's whole test suite because the runner is given the full discovered test list and there is no visible filter that limits execution to a named subset.
- **expected:** The execution tier should invoke only the named candidate tests, not the project's whole suite.
- **defective:** The execution tier passes the complete discovered test list into the sandbox runner, so the whole suite can be executed.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 15

**edit** — `src/acceptance/mutation/runner.py` lines 138-138

```diff
-            result = run_tests(tests, root, config)
+            result = run_tests(list(_sources(regions, root).keys()), root, config)
```

## `killed` — observation-not-prediction/execution-verdicts-not-marked-as-observed

- **type:** `other`
- **defect:** The mutation verdicts can be stored without any field that distinguishes them as observed execution results, so later reporting may not be able to tell them apart from predicted pair verdicts.
- **expected:** Execution-derived conclusions are recorded with metadata that identifies them as results of running the candidate tests against the mutant.
- **defective:** Execution-derived conclusions are recorded in the same shape as predicted verdicts, with no distinguishing evidence tier or equivalent marker.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 2

**edit** — `src/acceptance/review_state.py` lines 227-227

```diff
-    tier: EvidenceTier = EvidenceTier.STATIC
+    tier: EvidenceTier = EvidenceTier.DEFECT_KILLED
```

## `survived` — observation-not-prediction/prediction-language-still-used-in-recorded-conclusion

- **type:** `other`
- **defect:** The execution-tier record can still be written in predictive language, so the stored conclusion may describe what the candidate tests would do rather than what they did.
- **expected:** The recorded conclusion text states that the candidate tests were run against the altered copy and reports the observed result.
- **defective:** The recorded conclusion text is phrased as a forecast or expectation about how the candidate tests would behave.
- **candidates asked:** 1
- **candidate used:** 1

**edit** — `src/acceptance/mutation/verdicts.py` lines 109-112

```diff
-        return "The test failed when the defect was injected."
-    if attempt.outcome is MutationOutcomeKind.KILLED:
-        return "The test still passed when the defect was injected; another test caught it."
-    return "The test still passed when the defect was injected."
+        return "The test would fail if the defect were injected."
+    if attempt.outcome is MutationOutcomeKind.KILLED:
+        return "The test would still pass if the defect were injected; another test would catch it."
+    return "The test would still pass if the defect were injected."
```

## `killed` — parser-files-still-parse/parse-check-only-covers-python

- **type:** `scope_too_narrow`
- **defect:** The validity check only parses Python-like files, so edited files with another parser can be accepted even when they no longer parse.
- **expected:** Every file type that has a parser in the mutation validity check is parsed after the edit, and malformed output for any such file is rejected.
- **defective:** Only `.py` and `.pyi` files are parsed, while other parseable file types are left to the non-parse checks and can pass validity even if they are syntactically broken.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 1

**edit** — `src/acceptance/mutation/validity.py` lines 55-55

```diff
-    ".json": json.loads,
```

## `killed` — parser-files-still-parse/parse-errors-treated-as-acceptance

- **type:** `condition_inverted`
- **defect:** A parse failure from the mutated file is not rejected, so an invalid edit can still be treated as valid.
- **expected:** If the mutated file has a parser and parsing raises a syntax/value error, the edit is marked invalid.
- **defective:** If parsing raises a syntax/value error, the edit is still accepted as valid instead of being rejected.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 2

**edit** — `src/acceptance/mutation/validity.py` lines 132-133

```diff
-        except _PARSE_ERRORS as error:
-            return f"the mutated {descriptor.path} does not parse: {error}"
+        except _PARSE_ERRORS:
+            pass
```

## `killed` — preserve-code-reading-judgement/execution-off-path-skips-static-judgement

- **type:** `not_wired`
- **defect:** The new execution tier may be wired into the main review path in a way that leaves the existing code-reading judgement unreachable whenever execution is disabled or halted, so the judgement no longer participates in the delivered review flow.
- **expected:** The existing code-reading judgement remains wired into the review path and still runs for the cases the criterion covers.
- **defective:** The review path only invokes the new execution-related logic and never reaches the existing code-reading judgement on the delivered path.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 5

**edit** — `src/acceptance/pipeline.py` lines 461-465

```diff
-    pair_mapping = judge_pairs(
-        # Only the defects injection could not reach. The FULL `defect_sets` still
-        # goes to `derive_support` below, so a criterion's denominator is
-        # unchanged — what shrinks is the question put to the model, not the bar.
-        remaining_defect_sets(attempts, defect_sets),
+    pair_mapping = judge_pairs(
+        [],
```

## `killed` — preserve-code-reading-judgement/static-judgement-skipped-when-execution-runs

- **type:** `scope_too_narrow`
- **defect:** When execution is enabled and produces mutation verdicts, the pipeline can bypass the existing code-reading judgement for those defects instead of still including it in the review's output and decision-making.
- **expected:** The review always retains the existing code-reading judgement as part of its output and as part of the decision path, even when execution runs first.
- **defective:** The review replaces the code-reading judgement with execution results for defects that execution settles, so those defects no longer go through the existing judgement.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 3

**edit** — `src/acceptance/pipeline.py` lines 465-465

```diff
-        remaining_defect_sets(attempts, defect_sets),
+        defect_sets,
```

## `already_present` — preserve-current-review-conclusions-when-unrunnable/baseline-halt-changes-review-conclusions

- **type:** `unenforced_on_one_path`
- **defect:** The control-run halt path can change the review's conclusions by stopping before the existing review logic runs, so unrunnable cases do not necessarily preserve today's conclusions.
- **expected:** When the code cannot be run, the review should still produce the same conclusions it produces today, even if the control run finds failing candidate tests or cannot complete them.
- **defective:** When the control run cannot complete or finds failing candidate tests, the review halts and returns a different outcome instead of preserving the current conclusions.
- **reason:** The code already halts the review on the control-run path instead of preserving the existing review conclusions: src/acceptance/pipeline.py lines 284-285 raise ReviewHalted when the baseline is halted, and run_review calls _run_execution_tier before static pair judgement at lines 457-459, so the existing review logic does not run. (the repair was refused: the replacement for src/acceptance/pipeline.py lines 284..285 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced)
- **candidates asked:** 1
- **candidate used:** None

- **repair corroboration:** not_run
- **tests failing on the repair:** 0

**repair** — `src/acceptance/pipeline.py` lines 284-285

```diff
-    if baseline.halted:
-        raise ReviewHalted(baseline)
+    if baseline.halted:
+        raise ReviewHalted(baseline)
```

## `killed` — preserve-current-review-conclusions-when-unrunnable/execution-tier-overrides-static-when-run-is-unavailable

- **type:** `scope_too_narrow`
- **defect:** The review stops preserving the current conclusions when execution is enabled but the project cannot actually be run, because the execution tier is treated as mandatory instead of falling back to the existing static judgement.
- **expected:** When the code cannot be run, the review should still reach the same conclusions it reaches today by skipping execution and using the existing static judgement on the unrunnable cases.
- **defective:** When execution is enabled and the project cannot be run, the review should halt or replace the current conclusions instead of preserving them.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 3

**edit** — `src/acceptance/pipeline.py` lines 284-285

```diff
-    if baseline.halted:
-        raise ReviewHalted(baseline)
+    if baseline.halted:
+        return [], [], baseline.set_aside
```

## `killed` — preserve-current-review-conclusions-when-unrunnable/unrunnable-defects-return-not-attempted-instead-of-static

- **type:** `established_not_maintained`
- **defect:** A defect that execution could not settle is recorded as a mutation-stage outcome, but the later support calculation may no longer preserve the pre-existing static conclusions for those unrunnable cases.
- **expected:** When nothing can be run, defects that execution cannot settle should be handed to the existing static judgement so the review keeps the conclusions it would have reached today.
- **defective:** When execution cannot settle a defect, the code records a mutation outcome and lets that replace or alter the static conclusion instead of preserving it.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 3

**edit** — `src/acceptance/mutation/runner.py` lines 179-185

```diff
-        return MutationAttempt(
-            defect_id=defect.id,
-            outcome=MutationOutcomeKind.NOT_ATTEMPTED,
-            descriptor=descriptor,
-            tests_run=tests,
-            reason=_why_unobserved(unobserved, result.outcomes),
-        )
+        return MutationAttempt(
+            defect_id=defect.id,
+            outcome=MutationOutcomeKind.SURVIVED,
+            descriptor=descriptor,
+            tests_run=tests,
+        )
```

## `killed` — report-lists-set-aside-tests/report-omits-set-aside-tests

- **type:** `explanation_absent`
- **defect:** The report can render the set-aside section without naming the failing tests that were excluded, so a reader cannot tell which tests were set aside.
- **expected:** When failing candidate tests are set aside, the generated report names those tests in the set-aside section.
- **defective:** The report shows that some tests were set aside but does not include their test ids or names.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 1

**edit** — `src/acceptance/report.py` lines 314-314

```diff
-        lines.append(f"  [{test.kind.value}] {test.test_id}")
+        lines.append(f"  [{test.kind.value}]")
```

## `killed` — report-lists-set-aside-tests/set-aside-tests-never-populated

- **type:** `not_wired`
- **defect:** The baseline/control-run path can record failing tests, but the review may never carry them through to the report, so the report has nothing to name.
- **expected:** When the control run finds failing candidate tests and the project is configured to continue, those failing tests are stored on the review and passed to report rendering.
- **defective:** The control-run results are computed, but the failing tests are not wired into the review state or report path, so the report cannot list them.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 1

**edit** — `src/acceptance/pipeline.py` lines 644-644

```diff
-        set_aside_tests=set_aside_tests,
+        set_aside_tests=[],
```

## `killed` — run-candidate-tests-on-altered-copy/baseline-halt-prevents-execution

- **type:** `missing_case`
- **defect:** A failing candidate test at head halts the review before any altered-copy execution happens, so the candidate tests are never run against the mutant in that case.
- **expected:** Even when the baseline run finds failing candidate tests, the implementation should still run the candidate tests against the altered copy if the criterion is meant to hold for those inputs.
- **defective:** `establish_baseline` returns a halted baseline and `run_review` raises `ReviewHalted`, stopping before `run_mutations` can execute the candidate tests on the altered copy.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 3

**edit** — `src/acceptance/pipeline.py` lines 284-285

```diff
-    if baseline.halted:
-        raise ReviewHalted(baseline)
+    if baseline.halted and execution.allow_failing_tests:
+        raise ReviewHalted(baseline)
```

## `already_present` — run-candidate-tests-on-altered-copy/execution-flag-off-by-default

- **type:** `scope_too_narrow`
- **defect:** The mutation runner is only invoked when the new execution setting is enabled, so the candidate tests are not run against the altered copy on ordinary review runs.
- **expected:** The review should execute the candidate tests against the altered copy whenever this criterion applies, not only when an opt-in flag is set.
- **defective:** The review skips the mutation stage unless `execution.enabled` is true, returning empty mutation results instead of running the candidate tests.
- **reason:** Lines 274-275 already skip the mutation stage whenever `execution.enabled` is false: `if execution is None or not execution.enabled: return [], [], []`. Replacing that guard so only `None` gets defaulted repairs the defect by running execution on ordinary review runs.
- **candidates asked:** 1
- **candidate used:** None

- **repair corroboration:** a_test_asserts_defective
- **tests failing on the repair:** 4

**repair** — `src/acceptance/pipeline.py` lines 274-275

```diff
-    if execution is None or not execution.enabled:
-        return [], [], []
+    if execution is None:
+        execution = ExecutionSettings()
```

## `killed` — run-candidate-tests-on-altered-copy/no-tests-after-empty-baseline

- **type:** `missing_case`
- **defect:** When the control run leaves no usable candidate tests, the mutation stage returns without running anything against the altered copy.
- **expected:** If the criterion covers this input, the implementation should still execute the candidate tests against the altered copy rather than short-circuiting because the baseline produced no usable tests.
- **defective:** `run_mutations` returns `not_attempted` attempts immediately when `baseline.usable_tests` is empty, so no candidate tests are executed on the altered copy.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 3

**edit** — `src/acceptance/mutation/runner.py` lines 71-79

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
```

## `survived` — run-candidate-tests-on-altered-copy/partial-run-treated-as-not-attempted

- **type:** `other`
- **defect:** If the altered-copy test run is only partially observed, the code records the attempt as `not_attempted` instead of as an execution of the candidate tests against the altered copy.
- **expected:** The candidate tests should be treated as executed against the altered copy whenever the runner actually starts them, even if some do not complete.
- **defective:** `_classify` converts any run with unobserved outcomes into `NOT_ATTEMPTED`, so a partially executed altered-copy run is not recorded as candidate tests having been executed.
- **candidates asked:** 1
- **candidate used:** 1

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
+            outcome=MutationOutcomeKind.NOT_ATTEMPTED,
+            descriptor=descriptor,
+            reason=_why_unobserved(unobserved, result.outcomes),
+        )
```

## `killed` — single-continuous-edit-in-named-region/descriptor-allows-multi-file-edit

- **type:** `other`
- **defect:** The mutation descriptor path can point at one file while the injected replacement is assembled from text that does not stay confined to a single continuous span in that file, so the recorded edit is not a single patch in one file.
- **expected:** The injected edit is represented as one contiguous line span in exactly one file, and the recorded descriptor/replacement pair corresponds to that single span only.
- **defective:** The implementation records or applies an edit that spans multiple disjoint regions or effectively changes more than one file, so the result is not a single continuous patch in one file.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 1

**edit** — `src/acceptance/mutation/validity.py` lines 113-119

```diff
-    named = [region for region in regions if region.path == descriptor.path]
-    if not named:
-        return (
-            f"the defect names no region in {descriptor.path}, so an edit there could not be "
-            "credited to it"
-        )
-    if not any(region.contains(descriptor.start_line, descriptor.end_line) for region in named):
+    named = list(regions)
+    if not named:
+        return (
+            f"the defect names no region in {descriptor.path}, so an edit there could not be "
+            "credited to it"
+        )
+    if not any(region.contains(descriptor.start_line, descriptor.end_line) for region in named):
```

## `survived` — single-continuous-edit-in-named-region/descriptor-response-shape-can-lose-span-bounds

- **type:** `wrong_output_shape`
- **defect:** The descriptor path can return an answer shape that does not preserve the exact single-span bounds needed to prove the edit is one continuous replacement in one file.
- **expected:** The descriptor records one file path, one start line, one end line, and one replacement text for the edit, so the injected change can be checked as a single contiguous span.
- **defective:** The implementation returns or stores the edit in a shape that drops or obscures the span boundaries, nests multiple spans, or otherwise prevents checking that it is one continuous patch in one file.
- **candidates asked:** 1
- **candidate used:** 1

**edit** — `src/acceptance/mutation/descriptor.py` lines 208-214

```diff
-    return MutationDescriptor(
-        path=region.path,
-        start_line=result.start_line,
-        end_line=result.end_line,
-        replacement=result.replacement,
-        region_label=label,
-    )
+    return MutationDescriptor(
+        path=region.path,
+        start_line=result.start_line,
+        end_line=result.start_line,
+        replacement=result.replacement,
+        region_label=label,
+    )
```

## `killed` — single-continuous-edit-in-named-region/missing-region-rejected-as-mutable

- **type:** `missing_case`
- **defect:** A defect with no resolved region can still be sent through mutation instead of being rejected as uneditable, so the criterion is not enforced for defects whose named region is absent.
- **expected:** If the defect names no usable region in the delivered code, the mutation stage declines it and records that no single continuous edit can be made there.
- **defective:** The mutation stage proceeds anyway, fabricates or guesses an edit, and treats the defect as mutable despite having no named region to confine it to.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 1

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
+        regions = [
+            Region(label="", path="", start_line=1, end_line=1)
+        ]
```

## `killed` — single-continuous-edit-in-named-region/region-containment-check-too-permissive

- **type:** `condition_inverted`
- **defect:** The containment check can accept an edit whose span is not actually inside the defect's named region, so the injected change is not confined to the region the defect names.
- **expected:** An edit is accepted only when its start and end lines lie wholly inside one of the defect's named regions for the same file.
- **defective:** An edit is accepted even when its span falls outside the named region, or the containment test is effectively reversed so outside spans pass and inside spans are rejected.
- **candidates asked:** 3
- **candidate used:** 3
- **candidate 1 set aside:** `refused_after_run` — 26 of the 339 candidate tests failed under the edit, more than 7.5% of them. An edit that makes one defect true fails the tests near it; one that fails this many has broken something shared, so the failures say nothing about the named defect and no kill is counted.
- **candidate 2 set aside:** `refused_after_run` — 27 of the 339 candidate tests failed under the edit, more than 7.5% of them. An edit that makes one defect true fails the tests near it; one that fails this many has broken something shared, so the failures say nothing about the named defect and no kill is counted.
- **tests failing:** 3

**refused candidate 1** — `src/acceptance/mutation/region.py` lines 36-36

```diff
-        return self.start_line <= start_line and end_line <= self.end_line
+        return start_line <= self.start_line and self.end_line <= end_line
```

**refused candidate 2** — `src/acceptance/mutation/region.py` lines 36-36

```diff
-        return self.start_line <= start_line and end_line <= self.end_line
+        return self.start_line >= start_line and end_line <= self.end_line
```

**edit** — `src/acceptance/mutation/region.py` lines 36-36

```diff
-        return self.start_line <= start_line and end_line <= self.end_line
+        return self.start_line <= start_line or end_line <= self.end_line
```

## `killed` — single-continuous-edit-in-named-region/span-validation-not-applied-before-injection

- **type:** `not_wired`
- **defect:** The mechanical validity checks that should enforce single-span, single-file injection may exist but not actually gate the mutation path, allowing invalid edits to be applied.
- **expected:** Before a mutant is written, the runner checks the descriptor mechanically and refuses any edit that is not one contiguous span in one file within the named region.
- **defective:** The runner builds or applies the mutant without consulting the validity gate, so an out-of-region or non-contiguous edit can still be injected.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 1

**edit** — `src/acceptance/mutation/runner.py` lines 133-134

```diff
-    if reason is not None:
-        return _not_mutable(defect, reason)
+    if reason is not None:
+        pass
```

## `survived` — smallest-edit-that-makes-defect-true/descriptor-can-return-non-minimal-edit

- **type:** `other`
- **defect:** The mutation descriptor stage can return an edit that is valid but not the smallest edit that makes the named defect true, because the code only checks mechanical validity and accepts whatever span the model supplies.
- **expected:** For each named plausible defect, the review should choose the smallest contiguous edit that makes that defect true in the throwaway copy.
- **defective:** The review accepts a larger or otherwise non-minimal edit that still makes the defect true.
- **candidates asked:** 1
- **candidate used:** 1

**edit** — `src/acceptance/mutation/validity.py` lines 104-108

```diff
-    if descriptor.line_count > max_edit_lines:
-        return (
-            f"the edit replaces {descriptor.line_count} lines, over the {max_edit_lines}-line "
-            "bound; the smallest edit that makes the defect true is what was asked for"
-        )
+    if descriptor.line_count > max_edit_lines + 1:
+        return (
+            f"the edit replaces {descriptor.line_count} lines, over the {max_edit_lines}-line "
+            "bound; the smallest edit that makes the defect true is what was asked for"
+        )
```

## `already_present` — smallest-edit-that-makes-defect-true/mutation-stage-not-invoked

- **type:** `not_wired`
- **defect:** The execution tier that is supposed to build and apply the smallest edit is gated behind opt-in settings, so the review can run without ever constructing the edit at all.
- **expected:** When the criterion is being exercised, the review should actually invoke the mutation stage and build the edit in a throwaway copy.
- **defective:** The review leaves execution disabled and falls back to the static path, so no edit is built or applied.
- **reason:** The CLI passes `ExecutionSettings(enabled=args.execute, ...)` at src/acceptance/cli.py lines 951-954, so execution is disabled unless the operator opts in with `--execute`. That matches the DEFECTIVE behaviour: the review can fall back to the static path without invoking the mutation stage.
- **candidates asked:** 1
- **candidate used:** None

- **repair corroboration:** a_test_asserts_defective
- **tests failing on the repair:** 1

**repair** — `src/acceptance/cli.py` lines 952-952

```diff
-                    enabled=args.execute,
+                    enabled=True,
```

## `already_present` — smallest-edit-that-makes-defect-true/no-search-for-smaller-edit

- **type:** `other`
- **defect:** The implementation does not appear to search among multiple candidate spans or otherwise minimize the edit after the model response, so a plausible larger edit could be used even when a smaller one exists.
- **expected:** The review should compare candidate edits and retain the smallest one that makes the defect true.
- **defective:** The review uses the first acceptable edit returned by the descriptor stage, without proving it is minimal.
- **reason:** The code already uses a single descriptor-stage model response and does not compare multiple candidate edits or minimize after the response. In src/acceptance/mutation/descriptor.py lines 129-132, `build_descriptors` makes one `_ask_about` call per defect; lines 180-188 make one `client.complete(...)` call; and lines 188 plus 124-128 of src/acceptance/mutation/runner.py accept that single returned descriptor (or `None`) with no search among alternatives.
- **candidates asked:** 1
- **candidate used:** None

- **repair corroboration:** no_test_pins_expected
- **tests failing on the repair:** 0

**repair** — `src/acceptance/mutation/descriptor.py` lines 50-50

```diff
-Produce the SMALLEST edit that would make that defect real.
+Produce an edit that would make that defect real.
```

## `already_present` — smallest-edit-that-makes-defect-true/region-bounds-can-overconstrain-minimality

- **type:** `scope_too_narrow`
- **defect:** The descriptor stage only considers regions already resolved from the defect's code refs, so a smaller edit outside those regions would never be found even if it would make the defect true.
- **expected:** The review should be able to build the smallest edit that makes the defect true wherever that edit must land in the throwaway copy.
- **defective:** The review restricts candidate edits to predeclared regions and may miss a smaller valid edit elsewhere in the file or project.
- **reason:** The code already restricts descriptor answers to predeclared regions: lines 170-172 build `offered` from resolved regions and then constrain `region_label` to `[region.label for region in offered] + [""]`, making edits outside those regions unrepresentable. (the repair was refused: the replacement for src/acceptance/mutation/descriptor.py lines 171..171 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced)
- **candidates asked:** 1
- **candidate used:** None

- **repair corroboration:** not_run
- **tests failing on the repair:** 0

**repair** — `src/acceptance/mutation/descriptor.py` lines 171-171

```diff
-    allowed = {"region_label": [region.label for region in offered] + [""]}
+    allowed = {"region_label": [region.label for region in offered] + [""]}
```

## `killed` — test-fails-discriminate-defect/baseline-failure-halts-before-discrimination

- **type:** `missing_case`
- **defect:** A candidate test that already fails at head prevents the mutant run from ever reaching the point where a later failure could be recorded as discriminating for the defect.
- **expected:** When the control run finds failing candidate tests and the project does not allow them to be set aside, the review stops before mutation and reports why.
- **defective:** The review proceeds into mutation anyway, so a test that already failed at head can later be treated as discriminating for the defect.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 3

**edit** — `src/acceptance/pipeline.py` lines 284-285

```diff
-    if baseline.halted:
-        raise ReviewHalted(baseline)
+    if baseline.halted and execution.allow_failing_tests:
+        raise ReviewHalted(baseline)
```

## `killed` — test-fails-discriminate-defect/killed-tests-not-marked-as-killing

- **type:** `wrong_output_shape`
- **defect:** A failing test under mutation is recorded, but not in the form that says it discriminates for the defect, so downstream support logic cannot treat it as a kill.
- **expected:** A failing candidate test is recorded as a settled mutation outcome with the failing test listed among the defect's killing tests and a verdict marked as killing that defect.
- **defective:** A failing candidate test is recorded without the killing-test linkage or with the wrong tier/kills shape, so it does not read as a discriminating verdict for that defect.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 4

**edit** — `src/acceptance/mutation/verdicts.py` lines 62-64

```diff
-                    kills=test_id in killing,
-                    reason=_reason(attempt, kills=test_id in killing),
-                    tier=EvidenceTier.DEFECT_KILLED,
+                    kills=False,
+                    reason=_reason(attempt, kills=False),
+                    tier=EvidenceTier.DEFECT_KILLED,
```

## `killed` — test-fails-discriminate-defect/mutation-kill-not-recorded-as-discriminating

- **type:** `not_wired`
- **defect:** A candidate test can fail against the injected mutant, but that failure is not turned into a recorded discriminating verdict for the named defect.
- **expected:** When a mutant run produces a failing candidate test, the review records a verdict for that defect/test pair showing the test discriminates for the defect.
- **defective:** The mutant run may detect the failing test, but the result is only kept as an attempt or baseline note and never becomes a recorded discriminating verdict.
- **candidates asked:** 2
- **candidate used:** 2
- **candidate 1 set aside:** `refused_after_run` — 26 of the 339 candidate tests failed under the edit, more than 7.5% of them. An edit that makes one defect true fails the tests near it; one that fails this many has broken something shared, so the failures say nothing about the named defect and no kill is counted.
- **tests failing:** 3

**refused candidate 1** — `src/acceptance/mutation/verdicts.py` lines 54-55

```diff
-        if not attempt.settled:
-            continue
+        if not attempt.killed:
+            continue
```

**edit** — `src/acceptance/pipeline.py` lines 479-479

```diff
-    verdicts = executed_verdicts + pair_mapping.verdicts
+    verdicts = pair_mapping.verdicts
```

## `killed` — test-fails-discriminate-defect/mutation-verdicts-dropped-from-review

- **type:** `not_wired`
- **defect:** The execution stage can produce discriminating verdicts, but they are not carried into the review record that the report and support code read.
- **expected:** Executed discriminating verdicts are appended into the review's pair verdicts and used by support/reporting so the review records that the test discriminates for the defect.
- **defective:** The execution stage computes verdicts, but the review continues to use only the static pair-judgement verdicts, so the failing test is not recorded as discriminating for the defect.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 1

**edit** — `src/acceptance/pipeline.py` lines 641-641

```diff
-        pair_verdicts=verdicts,
+        pair_verdicts=pair_mapping.verdicts,
```

## `already_present` — tests-candidate-selection/execution-tier-alters-candidate-selection

- **type:** `other`
- **defect:** The new execution tier can stop the review after the control run and remove failing candidate tests from later mutation and rating, so the set of tests treated as candidates is no longer the same as before.
- **expected:** The code that decides whether tests are candidates should remain unchanged by the new execution path; candidate selection should still be determined only by the existing discovery logic.
- **defective:** The code establishes a baseline run, halts on failing candidate tests unless overridden, and filters those tests out of later stages, changing which tests are treated as candidates.
- **reason:** The code already establishes a baseline over discovered candidate tests in src/acceptance/pipeline.py lines 277-283, then at lines 284-301 halts on failing candidate tests and passes the filtered baseline into later mutation/rating stages. That is the DEFECTIVE behaviour described. (the repair was refused: the replacement for src/acceptance/pipeline.py lines 277..283 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced)
- **candidates asked:** 1
- **candidate used:** None

- **repair corroboration:** not_run
- **tests failing on the repair:** 0

**repair** — `src/acceptance/pipeline.py` lines 277-283

```diff
-    test_ids = [test.test_id for test in tests]
-    baseline = establish_baseline(
-        test_ids,
-        repo,
-        execution.sandbox,
-        allow_failing_tests=execution.allow_failing_tests,
-    )
+    test_ids = [test.test_id for test in tests]
+    baseline = establish_baseline(
+        test_ids,
+        repo,
+        execution.sandbox,
+        allow_failing_tests=execution.allow_failing_tests,
+    )
```

## `already_present` — tests-candidate-selection/execution-tier-changes-test-run-eligibility

- **type:** `other`
- **defect:** The new execution settings introduce a path that decides whether the review can run tests at all, instead of leaving that decision to the existing review flow.
- **expected:** The code should not add any new decision about whether the project's tests can be run at all; that decision should stay where it already was.
- **defective:** The pipeline now calls a baseline control run and can raise ReviewHalted when candidate tests fail at head, so the review itself decides whether tests may run.
- **reason:** The code already does the DEFECTIVE behaviour at src/acceptance/pipeline.py lines 278-285: it calls establish_baseline(...) and then raises ReviewHalted when baseline.halted is true, introducing a new decision in the pipeline about whether tests may run at all. (the repair broke the code)
- **candidates asked:** 1
- **candidate used:** None

- **repair corroboration:** not_run
- **tests failing on the repair:** 0

**repair** — `src/acceptance/pipeline.py` lines 278-285

```diff
-    baseline = establish_baseline(
-        test_ids,
-        repo,
-        execution.sandbox,
-        allow_failing_tests=execution.allow_failing_tests,
-    )
-    if baseline.halted:
-        raise ReviewHalted(baseline)
```

## `survived` — weaker-tier-evidence/executed-verdicts-upgrade-support-tier

- **type:** `established_not_maintained`
- **defect:** Executed mutation verdicts are recorded at the stronger `DEFECT_KILLED` tier and then fed into support derivation, so the judgement can be upgraded above the weaker tier instead of staying there.
- **expected:** Any evidence that contributes to this judgement is recorded and retained at the weaker evidence tier throughout support derivation and review storage.
- **defective:** Executed verdicts are appended to the review as `DEFECT_KILLED` evidence and `derive_support` can propagate that stronger tier into `achieved_evidence_tier`.
- **candidates asked:** 1
- **candidate used:** 1

**edit** — `src/acceptance/pipeline.py` lines 479-479

```diff
-    verdicts = executed_verdicts + pair_mapping.verdicts
+    verdicts = [*executed_verdicts, *(v.model_copy(update={"tier": EvidenceTier.DEFECT_KILLED}) for v in pair_mapping.verdicts)]
```

## `already_present` — weaker-tier-evidence/mutation-attempt-tier-returns-stronger-evidence

- **type:** `other`
- **defect:** The mutation attempt tier helper maps settling outcomes to `DEFECT_KILLED`, so the execution path can produce stronger-than-weaker evidence for this judgement.
- **expected:** The mutation execution path must record this judgement using the weaker evidence tier.
- **defective:** `tier_for()` returns `EvidenceTier.DEFECT_KILLED` for `killed` and `survived` outcomes, and `MutationAttempt.tier` exposes that stronger tier.
- **reason:** The code already does the DEFECTIVE behaviour at line 60: `tier_for()` maps settling outcomes (`kind in SETTLING_KINDS`) to `EvidenceTier.DEFECT_KILLED`, and `MutationAttempt.tier` exposes that via line 122.
- **candidates asked:** 1
- **candidate used:** None

- **repair corroboration:** a_test_asserts_defective
- **tests failing on the repair:** 2

**repair** — `src/acceptance/mutation/attempt.py` lines 60-60

```diff
-    tier = EvidenceTier.DEFECT_KILLED if kind in SETTLING_KINDS else EvidenceTier.STATIC
+    tier = EvidenceTier.WEAK if kind in SETTLING_KINDS else EvidenceTier.STATIC
```

## `already_present` — weaker-tier-evidence/pair-verdict-tier-default-stays-static

- **type:** `scope_too_narrow`
- **defect:** Only the new `PairVerdict.tier` field defaults to `STATIC`; the execution path can still create verdicts at `DEFECT_KILLED`, so the weaker tier is not enforced for all records that feed this judgement.
- **expected:** Every record that contributes to this judgement should be stored at the weaker evidence tier.
- **defective:** `PairVerdict` defaults to `STATIC`, but `verdicts_from()` explicitly emits `PairVerdict(..., tier=EvidenceTier.DEFECT_KILLED)` for settled mutation attempts.
- **reason:** The code already does the DEFECTIVE behaviour: in src/acceptance/mutation/verdicts.py line 64, verdicts_from() explicitly sets tier=EvidenceTier.DEFECT_KILLED for emitted PairVerdict records, overriding the PairVerdict default of STATIC.
- **candidates asked:** 2
- **candidate used:** None
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/mutation/verdicts.py lines 64..64 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**refused candidate 1** — `src/acceptance/mutation/verdicts.py` lines 64-64

```diff
-                    tier=EvidenceTier.DEFECT_KILLED,
+                    tier=EvidenceTier.DEFECT_KILLED,
```

- **repair corroboration:** a_test_asserts_defective
- **tests failing on the repair:** 6

**repair** — `src/acceptance/mutation/verdicts.py` lines 64-64

```diff
-                    tier=EvidenceTier.DEFECT_KILLED,
+                    tier=EvidenceTier.STATIC,
```

## `killed` — weaker-tier-evidence/report-shows-executed-verdicts-as-stronger-tier

- **type:** `other`
- **defect:** The report renders mutation attempts and set-aside tests, but the executed verdicts are still stored as stronger evidence, so the review output can reflect stronger-tier evidence instead of only the weaker tier.
- **expected:** The review record for this judgement should present only weaker-tier evidence.
- **defective:** `render_report()` includes the mutation block, and the underlying attempts/verdicts can carry `DEFECT_KILLED` rather than staying at the weaker tier.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 6

**edit** — `src/acceptance/mutation/verdicts.py` lines 64-64

```diff
-                    tier=EvidenceTier.DEFECT_KILLED,
+                    tier=EvidenceTier.STATIC,
```

