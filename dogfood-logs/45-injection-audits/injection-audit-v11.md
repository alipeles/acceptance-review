# Defect injection audit v11 — #45, head 518f876

Audit v6's defects for 13 criteria (left out: candidate-tests-run-once-before-changes, recorded-at-strongest-evidence-tier, stop-review-on-failing-candidate-test). Edits by claude-code (claude-sonnet-5-5), the agent only, one run per defect; verification on, openai/gpt-5.4. (Header corrected by hand 2026-10-13: the script wrote the one-call builder's settings here.) Reasoning: none.

21 defects, 339 usable candidate tests.

- **killed:** 7
- **no_usable_edit:** 12
- **survived:** 2

## `killed` — carry-reason-for-non-settlement/not-attempted-missing-reason

- **type:** `other`
- **defect:** Unsettled mutation attempts can be created without any reason text, so a non-settling defect execution would be recorded with an empty reason.
- **expected:** Every MutationAttempt whose outcome is not settled must carry a non-empty reason explaining why execution did not settle the defect.
- **defective:** A non-settling MutationAttempt is accepted or constructed with an empty reason, so the record does not explain the non-settlement.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 2

**edit** — `src/acceptance/mutation/attempt.py` lines 127-127

```diff
-        if not self.settled and not has_reason:
+        if not self.settled and not has_reason and False:
```

## `killed` — continue-with-set-aside-tests/allow-failing-tests-not-propagated

- **type:** `not_wired`
- **defect:** The continue-anyway flag is accepted on the CLI but never reaches the execution tier, so failing candidate tests still halt the review instead of being set aside.
- **expected:** The CLI passes the configured continue-anyway setting into the review pipeline, and the baseline run uses it to decide whether failing candidate tests are set aside or halt the review.
- **defective:** The CLI parses the flag but does not pass it into the pipeline or baseline logic, so the baseline run always behaves as if continuing were disabled.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 2

**edit** — `src/acceptance/pipeline.py` lines 282-282

```diff
-        allow_failing_tests=execution.allow_failing_tests,
```

## `no_usable_edit` — continue-with-set-aside-tests/set-aside-tests-still-count-in-conclusions

- **type:** `other`
- **defect:** Set-aside failing candidate tests are still fed into later support or verdict aggregation, so they continue to influence the conclusion even though they were supposed to be excluded.
- **expected:** Once a candidate test is set aside for failing at head, it is removed from the evidence used to form conclusions and does not contribute to derived support or verdict-based ratings.
- **defective:** The code keeps set-aside failing tests in the verdict/support inputs, so they still affect the conclusion despite being marked excluded.
- **reason:** all 1 candidate edit(s) asked for were set aside (1 unusable_answer). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 1
- **candidate used:** None
- **candidate 1 set aside:** `unusable_answer` — the answer named no usable span to replace

## `no_usable_edit` — does-not-run-first/static-judgement-still-runs-before-execution

- **type:** `condition_inverted`
- **defect:** The review pipeline still reaches the code-reading judgement before the execution-based mutation stage, so the later-stage review is not actually deferred.
- **expected:** The execution-based review runs first, and only after it finishes does the code-reading judgement run on whatever execution could not settle.
- **defective:** The code-reading judgement runs before the execution-based review, making it the initial pass instead of a later-stage review.
- **reason:** all 1 candidate edit(s) asked for were set aside (1 unusable_answer). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 1
- **candidate used:** None
- **candidate 1 set aside:** `unusable_answer` — the answer named no usable span to replace

## `killed` — execution-could-not-settle-defects/execution-disabled-skips-static-judgement

- **type:** `not_wired`
- **defect:** The execution tier is gated off entirely, so defects that execution could not settle never reach the code-reading judgement.
- **expected:** When execution cannot settle a defect, the review still invokes the static judgement on that defect and records the resulting conclusion.
- **defective:** The pipeline returns with no static judgement for unsettled defects because the execution tier is disabled or bypassed before the code-reading stage runs.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 5

**edit** — `src/acceptance/pipeline.py` lines 465-465

```diff
-        remaining_defect_sets(attempts, defect_sets),
+        [],
```

## `killed` — execution-could-not-settle-defects/unsettled-defects-dropped-from-review-state

- **type:** `wrong_output_shape`
- **defect:** The review stores mutation attempts, but unsettled defects could be omitted or stored in a form the later judgement cannot consume, so the code-reading conclusion would never be recorded for them.
- **expected:** Every defect execution could not settle is represented in the review state in a form that the later static judgement can read and use.
- **defective:** Unsettled defects are either not stored at all or are stored only as execution-stage records that are never converted into the static judgement input.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 3

**edit** — `src/acceptance/mutation/verdicts.py` lines 85-85

```diff
-    settled = {attempt.defect_id for attempt in attempts if attempt.settled}
+    settled = {attempt.defect_id for attempt in attempts}
```

## `killed` — mechanical-validity-checks/containment-check-only-uses-resolved-regions

- **type:** `scope_too_narrow`
- **defect:** The containment check only looks at regions that were resolved from the change set, so a defect with no resolved region can still be treated as mutable instead of being rejected mechanically.
- **expected:** If a defect names no editable region, mechanical validity rejects the edit as not mutable before any execution happens.
- **defective:** A defect with no resolved region can still reach later validity steps or be treated as valid because the containment check only runs after regions are found.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 1

**edit** — `src/acceptance/mutation/validity.py` lines 114-119

```diff
-    if not named:
-        return (
-            f"the defect names no region in {descriptor.path}, so an edit there could not be "
-            "credited to it"
-        )
-    if not any(region.contains(descriptor.start_line, descriptor.end_line) for region in named):
+    if named and not any(
+        region.contains(descriptor.start_line, descriptor.end_line) for region in named
+    ):
```

## `killed` — mechanical-validity-checks/mechanical-checks-bypassable-through-execution-settings

- **type:** `other`
- **defect:** The new execution path can decide whether an edit is valid by running tests and halting or proceeding, so edit validity is no longer settled only by the mechanical validity checks.
- **expected:** Mechanical validity checks alone determine whether a mutation descriptor is valid, and execution settings only affect whether execution runs after validity is established.
- **defective:** The execution tier can short-circuit or override the validity decision by halting on baseline failures or proceeding past them, so validity depends on execution control flow as well as mechanical checks.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 3

**edit** — `src/acceptance/mutation/baseline.py` lines 150-150

```diff
-    if failing and not allow_failing_tests:
+    if failing:
```

## `no_usable_edit` — mechanical-validity-checks/parse-check-applies-only-to-some-file-types

- **type:** `scope_too_narrow`
- **defect:** The parse validity check only covers a small hardcoded set of suffixes, so files with another parser can be mutated without being checked for parse validity.
- **expected:** Any file type that has a parser must be re-parsed after the edit, so malformed mutants are rejected mechanically for every parseable file type the criterion covers.
- **defective:** Only .py, .pyi, and .json files are parsed after mutation, so other parseable file types can slip through validity checks even when the edit breaks them.
- **reason:** all 1 candidate edit(s) asked for were set aside (1 unusable_answer). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 1
- **candidate used:** None
- **candidate 1 set aside:** `unusable_answer` — the answer named no usable span to replace

## `no_usable_edit` — no-line-execution-recording/execution-tier-still-derives-line-coverage

- **type:** `other`
- **defect:** The new execution tier still feeds line-coverage-style evidence into support derivation, so the system continues to record which lines tests executed indirectly through evidence tier bookkeeping.
- **expected:** The delivered code should avoid recording executed lines as evidence and should only record test outcomes or mutation results relevant to the criterion.
- **defective:** The delivered code derives support from execution data that encodes line coverage or executed-line information, thereby preserving line-execution recording under a different name.
- **reason:** all 1 candidate edit(s) asked for were set aside (1 unusable_answer). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 1
- **candidate used:** None
- **candidate 1 set aside:** `unusable_answer` — the answer named no usable span to replace

## `killed` — no-parser-not-invalid/parser-check-applies-to-all-files

- **type:** `scope_too_narrow`
- **defect:** The parse check only covers a fixed set of extensions, so a file type that does have a parser but is not listed can still be rejected or mishandled as if lacking one.
- **expected:** Any file type that has a parser should be treated as valid when its mutated text still parses under that parser.
- **defective:** Only the hardcoded extensions in the parser table are recognized, and other parseable file types are treated as outside the rule or invalid by omission.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 1

**edit** — `src/acceptance/mutation/validity.py` lines 55-55

```diff
-    ".json": json.loads,
```

## `no_usable_edit` — no-whole-suite-run/baseline-control-run-uses-all-tests

- **type:** `other`
- **defect:** The control run before mutation can execute every discovered test instead of only the named candidates, so the review may observe whole-suite execution before any defect injection happens.
- **expected:** The baseline run should be limited to the candidate tests named for the review.
- **defective:** The baseline establishment takes the full test id list and runs them all, which can amount to executing the project's whole suite.
- **reason:** all 1 candidate edit(s) asked for were set aside (1 unusable_answer). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 1
- **candidate used:** None
- **candidate 1 set aside:** `unusable_answer` — the answer named no usable span to replace

## `no_usable_edit` — no-whole-suite-run/whole-suite-execution-flag

- **type:** `other`
- **defect:** The new execution path can still run the project's whole test suite because the runner is given the full discovered test list and there is no visible filter that limits execution to a named subset.
- **expected:** The execution tier should invoke only the named candidate tests, not the project's whole suite.
- **defective:** The execution tier passes the complete discovered test list into the sandbox runner, so the whole suite can be executed.
- **reason:** all 1 candidate edit(s) asked for were set aside (1 unusable_answer). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 1
- **candidate used:** None
- **candidate 1 set aside:** `unusable_answer` — the answer named no usable span to replace

## `no_usable_edit` — preserve-code-reading-judgement/static-judgement-skipped-when-execution-runs

- **type:** `scope_too_narrow`
- **defect:** When execution is enabled and produces mutation verdicts, the pipeline can bypass the existing code-reading judgement for those defects instead of still including it in the review's output and decision-making.
- **expected:** The review always retains the existing code-reading judgement as part of its output and as part of the decision path, even when execution runs first.
- **defective:** The review replaces the code-reading judgement with execution results for defects that execution settles, so those defects no longer go through the existing judgement.
- **reason:** all 1 candidate edit(s) asked for were set aside (1 unusable_answer). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 1
- **candidate used:** None
- **candidate 1 set aside:** `unusable_answer` — the answer named no usable span to replace

## `survived` — preserve-current-review-conclusions-when-unrunnable/execution-tier-overrides-static-when-run-is-unavailable

- **type:** `scope_too_narrow`
- **defect:** The review stops preserving the current conclusions when execution is enabled but the project cannot actually be run, because the execution tier is treated as mandatory instead of falling back to the existing static judgement.
- **expected:** When the code cannot be run, the review should still reach the same conclusions it reaches today by skipping execution and using the existing static judgement on the unrunnable cases.
- **defective:** When execution is enabled and the project cannot be run, the review should halt or replace the current conclusions instead of preserving them.
- **candidates asked:** 1
- **candidate used:** 1

**edit** — `src/acceptance/pipeline.py` lines 284-284

```diff
-    if baseline.halted:
+    if baseline.halted or not baseline.usable_tests:
```

## `no_usable_edit` — run-candidate-tests-on-altered-copy/baseline-halt-prevents-execution

- **type:** `missing_case`
- **defect:** A failing candidate test at head halts the review before any altered-copy execution happens, so the candidate tests are never run against the mutant in that case.
- **expected:** Even when the baseline run finds failing candidate tests, the implementation should still run the candidate tests against the altered copy if the criterion is meant to hold for those inputs.
- **defective:** `establish_baseline` returns a halted baseline and `run_review` raises `ReviewHalted`, stopping before `run_mutations` can execute the candidate tests on the altered copy.
- **reason:** all 1 candidate edit(s) asked for were set aside (1 unusable_answer). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 1
- **candidate used:** None
- **candidate 1 set aside:** `unusable_answer` — the answer named no usable span to replace

## `no_usable_edit` — run-candidate-tests-on-altered-copy/no-tests-after-empty-baseline

- **type:** `missing_case`
- **defect:** When the control run leaves no usable candidate tests, the mutation stage returns without running anything against the altered copy.
- **expected:** If the criterion covers this input, the implementation should still execute the candidate tests against the altered copy rather than short-circuiting because the baseline produced no usable tests.
- **defective:** `run_mutations` returns `not_attempted` attempts immediately when `baseline.usable_tests` is empty, so no candidate tests are executed on the altered copy.
- **reason:** all 1 candidate edit(s) asked for were set aside (1 unusable_answer). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 1
- **candidate used:** None
- **candidate 1 set aside:** `unusable_answer` — the answer named no usable span to replace

## `no_usable_edit` — run-candidate-tests-on-altered-copy/partial-run-treated-as-not-attempted

- **type:** `other`
- **defect:** If the altered-copy test run is only partially observed, the code records the attempt as `not_attempted` instead of as an execution of the candidate tests against the altered copy.
- **expected:** The candidate tests should be treated as executed against the altered copy whenever the runner actually starts them, even if some do not complete.
- **defective:** `_classify` converts any run with unobserved outcomes into `NOT_ATTEMPTED`, so a partially executed altered-copy run is not recorded as candidate tests having been executed.
- **reason:** all 1 candidate edit(s) asked for were set aside (1 unusable_answer). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 1
- **candidate used:** None
- **candidate 1 set aside:** `unusable_answer` — the answer named no usable span to replace

## `no_usable_edit` — single-continuous-edit-in-named-region/missing-region-rejected-as-mutable

- **type:** `missing_case`
- **defect:** A defect with no resolved region can still be sent through mutation instead of being rejected as uneditable, so the criterion is not enforced for defects whose named region is absent.
- **expected:** If the defect names no usable region in the delivered code, the mutation stage declines it and records that no single continuous edit can be made there.
- **defective:** The mutation stage proceeds anyway, fabricates or guesses an edit, and treats the defect as mutable despite having no named region to confine it to.
- **reason:** all 1 candidate edit(s) asked for were set aside (1 unusable_answer). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 1
- **candidate used:** None
- **candidate 1 set aside:** `unusable_answer` — the answer named no usable span to replace

## `survived` — weaker-tier-evidence/executed-verdicts-upgrade-support-tier

- **type:** `established_not_maintained`
- **defect:** Executed mutation verdicts are recorded at the stronger `DEFECT_KILLED` tier and then fed into support derivation, so the judgement can be upgraded above the weaker tier instead of staying there.
- **expected:** Any evidence that contributes to this judgement is recorded and retained at the weaker evidence tier throughout support derivation and review storage.
- **defective:** Executed verdicts are appended to the review as `DEFECT_KILLED` evidence and `derive_support` can propagate that stronger tier into `achieved_evidence_tier`.
- **candidates asked:** 1
- **candidate used:** 1

**edit** — `src/acceptance/defects/support.py` lines 196-196

```diff
-            verdict.tier if known is None else min(known, verdict.tier)
+            verdict.tier if known is None else max(known, verdict.tier)
```

## `no_usable_edit` — weaker-tier-evidence/report-shows-executed-verdicts-as-stronger-tier

- **type:** `other`
- **defect:** The report renders mutation attempts and set-aside tests, but the executed verdicts are still stored as stronger evidence, so the review output can reflect stronger-tier evidence instead of only the weaker tier.
- **expected:** The review record for this judgement should present only weaker-tier evidence.
- **defective:** `render_report()` includes the mutation block, and the underlying attempts/verdicts can carry `DEFECT_KILLED` rather than staying at the weaker tier.
- **reason:** all 1 candidate edit(s) asked for were set aside (1 unusable_answer). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 1
- **candidate used:** None
- **candidate 1 set aside:** `unusable_answer` — the answer named no usable span to replace

