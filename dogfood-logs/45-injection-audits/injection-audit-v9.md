# Defect injection audit v9 — #45, head 518f876f7b8eb39860cd2d309b86abd6c07925eb

Audit v6's defects for 22 criteria. Edits on openai/gpt-5.4-mini, up to 3 candidates each; verification on, openai/gpt-5.4.

64 defects, 339 usable candidate tests.

- **already_present:** 3
- **killed:** 31
- **no_usable_edit:** 19
- **not_attempted:** 1
- **survived:** 10

## `survived` — candidate-tests-not-discriminate-when-none-fail/no-discriminate-report-not-wired

- **type:** `not_wired`
- **defect:** The execution path can run the mutation stage and record injected attempts, but the review/reporting path never turns the all-survived case into the required 'candidate tests do not discriminate' conclusion, so a no-fail run can finish without that observation being reported.
- **expected:** When every candidate test survives the injected defect, the review path should emit the non-discrimination conclusion for that defect and record it in the review output.
- **defective:** The code records mutation attempts and verdicts, but the delivered review path omits or bypasses the specific no-fail conclusion, so the review can end without saying the candidate tests do not discriminate.
- **candidates asked:** 2
- **candidate used:** 2
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/report.py lines 131..133 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**refused candidate 1** — `src/acceptance/report.py` lines 131-133

```diff
-    if review.mutation_attempts:
-        lines.extend(_mutation_block(review))
-        lines.append("")
+    if review.mutation_attempts:
+        lines.extend(_mutation_block(review))
+        lines.append("")
```

**edit** — `src/acceptance/report.py` lines 131-133

```diff
-    if review.mutation_attempts:
-        lines.extend(_mutation_block(review))
-        lines.append("")
+    if review.mutation_attempts:
+        lines.extend(_mutation_block(review))
+        lines.append("")
+        if not review.set_aside_tests:
+            lines.extend(_set_aside_block(review))
+            lines.append("")
```

## `killed` — candidate-tests-not-discriminate-when-none-fail/survival-classified-as-set-aside

- **type:** `condition_inverted`
- **defect:** A mutant run with no red tests can be classified as not_attempted instead of survived if the unobserved-test check is treated as the deciding condition, so the code may fail to report non-discrimination even though every candidate test completed and passed.
- **expected:** When the mutant run completes and no candidate test fails, the attempt should be classified as survived so the review can report that the candidate tests did not discriminate.
- **defective:** The code treats the absence of red tests as a non-settling or incomplete run and routes the attempt to not_attempted instead of survived, preventing the non-discrimination conclusion from being recorded.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 3

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

## `killed` — candidate-tests-not-discriminate-when-none-fail/survival-not-propagated-to-review-state

- **type:** `not_wired`
- **defect:** The mutation runner can produce survived attempts, but those attempts may not be propagated into the stored review state or rendered report in a way that the no-fail conclusion is visible to callers.
- **expected:** Survived mutation attempts should be carried through the pipeline into the review object and report so that a no-fail run is observable as non-discrimination.
- **defective:** The pipeline may compute attempts and verdicts but fail to wire them into the final review/report path that the caller sees, so the review does not actually show the non-discrimination result.
- **candidates asked:** 2
- **candidate used:** 2
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/pipeline.py lines 643..643 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **tests failing:** 4

**refused candidate 1** — `src/acceptance/pipeline.py` lines 643-643

```diff
-        mutation_attempts=attempts,
+        mutation_attempts=attempts,
```

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
- **tests failing:** 13

**edit** — `src/acceptance/mutation/baseline.py` lines 145-145

```diff
-                reason=outcome.reason or "the test failed against the code as delivered",
+                reason=outcome.reason,
```

## `no_usable_edit` — carry-reason-for-non-settlement/not-attempted-missing-reason

- **type:** `other`
- **defect:** Unsettled mutation attempts can be created without any reason text, so a non-settling defect execution would be recorded with an empty reason.
- **expected:** Every MutationAttempt whose outcome is not settled must carry a non-empty reason explaining why execution did not settle the defect.
- **defective:** A non-settling MutationAttempt is accepted or constructed with an empty reason, so the record does not explain the non-settlement.
- **reason:** all 3 candidate edit(s) asked for were set aside (1 changed_nothing, 2 refused_after_run). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 3
- **candidate used:** None
- **candidate 1 set aside:** `refused_after_run` — 45 of the 339 candidate tests failed under the edit, more than 7.5% of them. An edit that makes one defect true fails the tests near it; one that fails this many has broken something shared, so the failures say nothing about the named defect and no kill is counted.
- **candidate 2 set aside:** `changed_nothing` — the replacement for src/acceptance/mutation/attempt.py lines 114..114 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 3 set aside:** `refused_after_run` — 45 of the 339 candidate tests failed under the edit, more than 7.5% of them. An edit that makes one defect true fails the tests near it; one that fails this many has broken something shared, so the failures say nothing about the named defect and no kill is counted.

**refused candidate 1** — `src/acceptance/mutation/attempt.py` lines 114-114

```diff
-    reason: str = ""
+    reason: str = Field(min_length=1)
```

**refused candidate 2** — `src/acceptance/mutation/attempt.py` lines 114-114

```diff
-    reason: str = ""
+    reason: str = ""
```

**refused candidate 3** — `src/acceptance/mutation/attempt.py` lines 114-114

```diff
-    reason: str = ""
+    reason: str = Field(min_length=1)
```

## `killed` — carry-reason-for-non-settlement/not-attempted-path-loses-reason

- **type:** `other`
- **defect:** The mutation runner can return a not_attempted outcome with a reason, but the classification path for partially observed runs may drop or replace that reason before the attempt is stored.
- **expected:** Any defect execution classified as not_attempted must be stored with the reason produced by the runner.
- **defective:** The runner or its caller records the non-settlement outcome without preserving the reason, leaving the attempt reason empty or replaced.
- **candidates asked:** 2
- **candidate used:** 2
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/pipeline.py lines 479..479 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **tests failing:** 3

**refused candidate 1** — `src/acceptance/pipeline.py` lines 479-479

```diff
-    verdicts = executed_verdicts + pair_mapping.verdicts
+    verdicts = executed_verdicts + pair_mapping.verdicts
```

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
+            outcome=MutationOutcomeKind.NOT_ATTEMPTED,
+            descriptor=descriptor,
+            tests_run=tests,
+            reason=descriptor.reason,
+        )
```

## `no_usable_edit` — continue-with-set-aside-tests/allow-failing-tests-not-propagated

- **type:** `not_wired`
- **defect:** The continue-anyway flag is accepted on the CLI but never reaches the execution tier, so failing candidate tests still halt the review instead of being set aside.
- **expected:** The CLI passes the configured continue-anyway setting into the review pipeline, and the baseline run uses it to decide whether failing candidate tests are set aside or halt the review.
- **defective:** The CLI parses the flag but does not pass it into the pipeline or baseline logic, so the baseline run always behaves as if continuing were disabled.
- **reason:** all 3 candidate edit(s) asked for were set aside (3 failed_check). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 3
- **candidate used:** None
- **candidate 1 set aside:** `failed_check` — the edit replaces 17 lines, over the 12-line bound; the smallest edit that makes the defect true is what was asked for
- **candidate 2 set aside:** `failed_check` — the edit replaces 17 lines, over the 12-line bound; the smallest edit that makes the defect true is what was asked for
- **candidate 3 set aside:** `failed_check` — the edit replaces 17 lines, over the 12-line bound; the smallest edit that makes the defect true is what was asked for

**refused candidate 1** — `src/acceptance/cli.py` lines 193-209

```diff
-    review = run_review(
-        task_text=task_text,
-        change_set=change_set,
-        repo=repo_path,
-        client=client if client is not None else config.build_client(),
-        reviewed_revision=reviewed_revision,
-        declaration_text=declaration_text,
-        policy=config.scope_expansion_policy,
-        pair_batch_size=config.pair_batch_size,
-        tests_per_batch=config.tests_per_batch,
-        link_pair_batch_size=config.link_pair_batch_size,
-        link_distance_threshold=config.link_distance_threshold,
-        task_identifier=task,
-        prior=prior,
-        ledger_prior=ledger.read_if_present(continue_from) if ledger is not None else None,
-        ledger_sink=sink,
-        execution=execution,
+    review = run_review(
+        task_text=task_text,
+        change_set=change_set,
+        repo=repo_path,
+        client=client if client is not None else config.build_client(),
+        reviewed_revision=reviewed_revision,
+        declaration_text=declaration_text,
+        policy=config.scope_expansion_policy,
+        pair_batch_size=config.pair_batch_size,
+        tests_per_batch=config.tests_per_batch,
+        link_pair_batch_size=config.link_pair_batch_size,
+        link_distance_threshold=config.link_distance_threshold,
+        task_identifier=task,
+        prior=prior,
+        ledger_prior=ledger.read_if_present(continue_from) if ledger is not None else None,
+        ledger_sink=sink,
+        execution=execution,
+    )
```

**refused candidate 2** — `src/acceptance/cli.py` lines 193-209

```diff
-    review = run_review(
-        task_text=task_text,
-        change_set=change_set,
-        repo=repo_path,
-        client=client if client is not None else config.build_client(),
-        reviewed_revision=reviewed_revision,
-        declaration_text=declaration_text,
-        policy=config.scope_expansion_policy,
-        pair_batch_size=config.pair_batch_size,
-        tests_per_batch=config.tests_per_batch,
-        link_pair_batch_size=config.link_pair_batch_size,
-        link_distance_threshold=config.link_distance_threshold,
-        task_identifier=task,
-        prior=prior,
-        ledger_prior=ledger.read_if_present(continue_from) if ledger is not None else None,
-        ledger_sink=sink,
-        execution=execution,
+    review = run_review(
+        task_text=task_text,
+        change_set=change_set,
+        repo=repo_path,
+        client=client if client is not None else config.build_client(),
+        reviewed_revision=reviewed_revision,
+        declaration_text=declaration_text,
+        policy=config.scope_expansion_policy,
+        pair_batch_size=config.pair_batch_size,
+        tests_per_batch=config.tests_per_batch,
+        link_pair_batch_size=config.link_pair_batch_size,
+        link_distance_threshold=config.link_distance_threshold,
+        task_identifier=task,
+        prior=prior,
+        ledger_prior=ledger.read_if_present(continue_from) if ledger is not None else None,
+        ledger_sink=sink,
+        execution=execution,
+    )
```

**refused candidate 3** — `src/acceptance/cli.py` lines 193-209

```diff
-    review = run_review(
-        task_text=task_text,
-        change_set=change_set,
-        repo=repo_path,
-        client=client if client is not None else config.build_client(),
-        reviewed_revision=reviewed_revision,
-        declaration_text=declaration_text,
-        policy=config.scope_expansion_policy,
-        pair_batch_size=config.pair_batch_size,
-        tests_per_batch=config.tests_per_batch,
-        link_pair_batch_size=config.link_pair_batch_size,
-        link_distance_threshold=config.link_distance_threshold,
-        task_identifier=task,
-        prior=prior,
-        ledger_prior=ledger.read_if_present(continue_from) if ledger is not None else None,
-        ledger_sink=sink,
-        execution=execution,
+    review = run_review(
+        task_text=task_text,
+        change_set=change_set,
+        repo=repo_path,
+        client=client if client is not None else config.build_client(),
+        reviewed_revision=reviewed_revision,
+        declaration_text=declaration_text,
+        policy=config.scope_expansion_policy,
+        pair_batch_size=config.pair_batch_size,
+        tests_per_batch=config.tests_per_batch,
+        link_pair_batch_size=config.link_pair_batch_size,
+        link_distance_threshold=config.link_distance_threshold,
+        task_identifier=task,
+        prior=prior,
+        ledger_prior=ledger.read_if_present(continue_from) if ledger is not None else None,
+        ledger_sink=sink,
+        execution=execution,
+    )
```

## `survived` — continue-with-set-aside-tests/failing-tests-not-listed-in-report

- **type:** `wrong_output_shape`
- **defect:** The review records set-aside tests internally but the report does not identify which failing candidate tests were set aside, so the observable output does not show the exclusion list.
- **expected:** When failing candidate tests are set aside, the report renders those tests by name and reason so a reader can see exactly which tests took no part in the conclusion.
- **defective:** The report either omits the set-aside tests entirely or renders them only as a generic note without naming the tests that were excluded.
- **candidates asked:** 2
- **candidate used:** 2
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/report.py lines 312..315 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**refused candidate 1** — `src/acceptance/report.py` lines 312-315

```diff
-    lines = ["Candidate tests set aside (no conclusion rests on these):"]
-    for test in review.set_aside_tests:
-        lines.append(f"  [{test.kind.value}] {test.test_id}")
-        lines.append(f"    {test.reason}")
+    lines = ["Candidate tests set aside (no conclusion rests on these):"]
+    for test in review.set_aside_tests:
+        lines.append(f"  [{test.kind.value}] {test.test_id}")
+        lines.append(f"    {test.reason}")
```

**edit** — `src/acceptance/report.py` lines 135-136

```diff
-    if review.set_aside_tests:
-        lines.extend(_set_aside_block(review))
+    if review.set_aside_tests:
+        lines.extend(_set_aside_block(review))
+        lines.append("")
```

## `killed` — continue-with-set-aside-tests/set-aside-tests-still-count-in-conclusions

- **type:** `other`
- **defect:** Set-aside failing candidate tests are still fed into later support or verdict aggregation, so they continue to influence the conclusion even though they were supposed to be excluded.
- **expected:** Once a candidate test is set aside for failing at head, it is removed from the evidence used to form conclusions and does not contribute to derived support or verdict-based ratings.
- **defective:** The code keeps set-aside failing tests in the verdict/support inputs, so they still affect the conclusion despite being marked excluded.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 3

**edit** — `src/acceptance/pipeline.py` lines 479-479

```diff
-    verdicts = executed_verdicts + pair_mapping.verdicts
+    verdicts = pair_mapping.verdicts
```

## `no_usable_edit` — does-not-run-first/execution-path-not-wired-into-review-flow

- **type:** `not_wired`
- **defect:** The execution-stage machinery exists, but the review flow may never call it on the delivered path, leaving the code-reading judgement as the effective first stage.
- **expected:** The review pipeline should invoke the execution-based stage before the static judgement whenever execution is enabled for a review.
- **defective:** The execution-stage functions are defined, but the review path does not actually route through them before the code-reading judgement runs.
- **reason:** all 3 candidate edit(s) asked for were set aside (3 changed_nothing). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 3
- **candidate used:** None
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/pipeline.py lines 457..459 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 2 set aside:** `changed_nothing` — the replacement for src/acceptance/pipeline.py lines 457..459 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 3 set aside:** `changed_nothing` — the replacement for src/acceptance/pipeline.py lines 457..459 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**refused candidate 1** — `src/acceptance/pipeline.py` lines 457-459

```diff
-    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
-        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
-    )
+    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
+        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
+    )
```

**refused candidate 2** — `src/acceptance/pipeline.py` lines 457-459

```diff
-    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
-        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
-    )
+    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
+        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
+    )
```

**refused candidate 3** — `src/acceptance/pipeline.py` lines 457-459

```diff
-    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
-        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
-    )
+    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
+        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
+    )
```

## `killed` — does-not-run-first/execution-tier-only-runs-when-explicitly-enabled

- **type:** `scope_too_narrow`
- **defect:** The execution-based review is gated behind an opt-in flag, so the code-reading judgement still runs first on the default path where execution is disabled.
- **expected:** For the criterion to hold, execution-based review must precede the code-reading judgement on the normal review flow, not only when an explicit execution flag is supplied.
- **defective:** Execution-based review happens before the code-reading judgement only when `--execute` is set; otherwise the static judgement remains the first pass.
- **candidates asked:** 2
- **candidate used:** 2
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/pipeline.py lines 455..459 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **tests failing:** 16

**refused candidate 1** — `src/acceptance/pipeline.py` lines 455-459

```diff
-    # Off unless the caller opted in: §8.3 makes execution conditional on a
-    # feasibility probe, and #42 (M8.1) is that probe and does not exist yet.
-    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
-        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
-    )
+    # Off unless the caller opted in: §8.3 makes execution conditional on a
+    # feasibility probe, and #42 (M8.1) is that probe and does not exist yet.
+    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
+        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
+    )
```

**edit** — `src/acceptance/pipeline.py` lines 455-459

```diff
-    # Off unless the caller opted in: §8.3 makes execution conditional on a
-    # feasibility probe, and #42 (M8.1) is that probe and does not exist yet.
-    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
-        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
-    )
+    # Off unless the caller opted in: §8.3 makes execution conditional on a
+    # feasibility probe, and #42 (M8.1) is that probe and does not exist yet.
+    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
+        defect_sets, discovered.tests, change_set, repo, client, unusable, None
+    )
```

## `no_usable_edit` — does-not-run-first/static-judgement-still-runs-before-execution

- **type:** `condition_inverted`
- **defect:** The review pipeline still reaches the code-reading judgement before the execution-based mutation stage, so the later-stage review is not actually deferred.
- **expected:** The execution-based review runs first, and only after it finishes does the code-reading judgement run on whatever execution could not settle.
- **defective:** The code-reading judgement runs before the execution-based review, making it the initial pass instead of a later-stage review.
- **reason:** all 3 candidate edit(s) asked for were set aside (3 failed_check). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 3
- **candidate used:** None
- **candidate 1 set aside:** `failed_check` — the mutated src/acceptance/pipeline.py does not parse: unexpected indent (<unknown>, line 483)
- **candidate 2 set aside:** `failed_check` — the edit replaces 13 lines, over the 12-line bound; the smallest edit that makes the defect true is what was asked for
- **candidate 3 set aside:** `failed_check` — the mutated src/acceptance/pipeline.py does not parse: unexpected indent (<unknown>, line 477)

**refused candidate 1** — `src/acceptance/pipeline.py` lines 457-461

```diff
-    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
-        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
-    )
-
-    pair_mapping = judge_pairs(
+    pair_mapping = judge_pairs(
+        # Only the defects injection could not reach. The FULL `defect_sets` still
+        # goes to `derive_support` below, so a criterion's denominator is
+        # unchanged — what shrinks is the question put to the model, not the bar.
+        remaining_defect_sets(attempts, defect_sets),
+        discovered.tests,
+        change_set,
+        client,
+        repo=repo,
+        batch_size=pair_batch_size,
+        tests_per_batch=tests_per_batch,
+        unusable=unusable,
+        prior=list(ledger_prior.pair_verdicts) if ledger_prior is not None else None,
+    )
+    # One list, two provenances. `PairVerdict.tier` is what tells them apart, and
+    # `derive_support` reduces both with the same arithmetic — which is what
+    # keeps the rating a single implementation rather than a static one and an
+    # executed one that can drift.
+    verdicts = executed_verdicts + pair_mapping.verdicts
+
+    # Handed back rather than written here: the pipeline does not own the run id,
+    # the parent pointer or the file, and a stage that wrote to disk on the way
+    # past would make the benchmark's own runs leave ledger entries behind.
```

**refused candidate 2** — `src/acceptance/pipeline.py` lines 447-459

```diff
-    # The execution tier runs HERE, BEFORE the static pair judgement, and the
-    # order is the whole point of M8.4 (DR-171 Decision 7, revised 2026-09-14).
-    # The original decision had injection "overwrite" static verdicts, which
-    # means judging all 23,808 pairs by model and then discarding the answers
-    # execution supersedes — paying the pair stage's $6.02 in full and adding
-    # the test runs on top. Inverted, the model is asked only about what
-    # execution could not settle.
-    #
-    # Off unless the caller opted in: §8.3 makes execution conditional on a
-    # feasibility probe, and #42 (M8.1) is that probe and does not exist yet.
-    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
-        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
-    )
+    # The execution tier runs HERE, BEFORE the static pair judgement, and the
+    # order is the whole point of M8.4 (DR-171 Decision 7, revised 2026-09-14).
+    # The original decision had injection "overwrite" static verdicts, which
+    # means judging all 23,808 pairs by model and then discarding the answers
+    # execution supersedes — paying the pair stage's $6.02 in full and adding
+    # the test runs on top. Inverted, the model is asked only about what
+    # execution could not settle.
+    #
+    # Off unless the caller opted in: §8.3 makes execution conditional on a
+    # feasibility probe, and #42 (M8.1) is that probe and does not exist yet.
+    pair_mapping = judge_pairs(
+        # Only the defects injection could not reach. The FULL `defect_sets` still
+        # goes to `derive_support` below, so a criterion's denominator is
+        # unchanged — what shrinks is the question put to the model, not the bar.
+        remaining_defect_sets(attempts, defect_sets),
+        discovered.tests,
+        change_set,
+        client,
+        repo=repo,
+        batch_size=pair_batch_size,
+        tests_per_batch=tests_per_batch,
+        unusable=unusable,
+        prior=list(ledger_prior.pair_verdicts) if ledger_prior is not None else None,
+    )
+    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
+        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
+    )
```

**refused candidate 3** — `src/acceptance/pipeline.py` lines 457-461

```diff
-    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
-        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
-    )
-
-    pair_mapping = judge_pairs(
+    pair_mapping = judge_pairs(
+        # Only the defects injection could not reach. The FULL `defect_sets` still
+        # goes to `derive_support` below, so a criterion's denominator is
+        # unchanged — what shrinks is the question put to the model, not the bar.
+        remaining_defect_sets(attempts, defect_sets),
+        discovered.tests,
+        change_set,
+        client,
+        repo=repo,
+        batch_size=pair_batch_size,
+        tests_per_batch=tests_per_batch,
+        unusable=unusable,
+        prior=list(ledger_prior.pair_verdicts) if ledger_prior is not None else None,
+    )
+    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
+        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
+    )
```

## `killed` — execution-could-not-settle-defects/execution-disabled-skips-static-judgement

- **type:** `not_wired`
- **defect:** The execution tier is gated off entirely, so defects that execution could not settle never reach the code-reading judgement.
- **expected:** When execution cannot settle a defect, the review still invokes the static judgement on that defect and records the resulting conclusion.
- **defective:** The pipeline returns with no static judgement for unsettled defects because the execution tier is disabled or bypassed before the code-reading stage runs.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 1

**edit** — `src/acceptance/pipeline.py` lines 274-275

```diff
-    if execution is None or not execution.enabled:
-        return [], [], []
+    if execution is None:
+        return [], [], []
```

## `killed` — execution-could-not-settle-defects/halted-baseline-prevents-static-fallback

- **type:** `condition_inverted`
- **defect:** A baseline failure stops the review instead of routing the unsettled defects to the static judgement, so the code-reading conclusion is lost when execution cannot settle because the candidate tests already fail.
- **expected:** When the control run cannot support execution, the review still reaches the static judgement for the defects execution could not settle, or otherwise records that code-reading evidence was used.
- **defective:** Any failing candidate test at head halts the review before the static judgement runs, so unsettled defects never receive a code-reading conclusion.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 3

**edit** — `src/acceptance/pipeline.py` lines 284-285

```diff
-    if baseline.halted:
-        raise ReviewHalted(baseline)
+    if baseline.halted:
+        pass
```

## `killed` — execution-could-not-settle-defects/not-attempted-defects-never-fed-to-static-judge

- **type:** `missing_case`
- **defect:** Defects that execution could not settle because the edit could not be built, or because the code could not be run, may be recorded as terminal outcomes but never handed to the code-reading judgement.
- **expected:** Defects whose edit could not be built, and defects that could not be run, are still passed to the static judgement so the review can conclude from code-reading evidence.
- **defective:** Those not_mutable and not_attempted defects are recorded as execution outcomes only, but the remaining defect set given to the static judgement omits them or drops them from consideration.
- **candidates asked:** 2
- **candidate used:** 2
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/mutation/verdicts.py lines 85..87 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **tests failing:** 7

**refused candidate 1** — `src/acceptance/mutation/verdicts.py` lines 85-87

```diff
-    settled = {attempt.defect_id for attempt in attempts if attempt.settled}
-    if not settled:
-        return list(defect_sets)
+    settled = {attempt.defect_id for attempt in attempts if attempt.settled}
+    if not settled:
+        return list(defect_sets)
```

**edit** — `src/acceptance/mutation/verdicts.py` lines 85-87

```diff
-    settled = {attempt.defect_id for attempt in attempts if attempt.settled}
-    if not settled:
-        return list(defect_sets)
+    settled = {attempt.defect_id for attempt in attempts if attempt.settled}
+    if not settled:
+        return []
```

## `no_usable_edit` — execution-could-not-settle-defects/unsettled-defects-dropped-from-review-state

- **type:** `wrong_output_shape`
- **defect:** The review stores mutation attempts, but unsettled defects could be omitted or stored in a form the later judgement cannot consume, so the code-reading conclusion would never be recorded for them.
- **expected:** Every defect execution could not settle is represented in the review state in a form that the later static judgement can read and use.
- **defective:** Unsettled defects are either not stored at all or are stored only as execution-stage records that are never converted into the static judgement input.
- **reason:** all 3 candidate edit(s) asked for were set aside (2 changed_nothing, 1 failed_check). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 3
- **candidate used:** None
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/pipeline.py lines 641..643 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 2 set aside:** `changed_nothing` — the replacement for src/acceptance/review_state.py lines 1263..1263 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 3 set aside:** `failed_check` — the span 641..643 falls outside the region(s) the defect named in src/acceptance/pipeline.py (472..482)

**refused candidate 1** — `src/acceptance/pipeline.py` lines 641-643

```diff
-        pair_verdicts=verdicts,
-        unjudged_pairs=pair_mapping.unjudged,
-        mutation_attempts=attempts,
+        pair_verdicts=verdicts,
+        unjudged_pairs=pair_mapping.unjudged,
+        mutation_attempts=attempts,
```

**refused candidate 2** — `src/acceptance/review_state.py` lines 1263-1263

```diff
-    mutation_attempts: list[MutationAttempt] = Field(default_factory=list)
+    mutation_attempts: list[MutationAttempt] = Field(default_factory=list)
```

**refused candidate 3** — `src/acceptance/pipeline.py` lines 641-643

```diff
-        pair_verdicts=verdicts,
-        unjudged_pairs=pair_mapping.unjudged,
-        mutation_attempts=attempts,
+        pair_verdicts=verdicts,
+        unjudged_pairs=pair_mapping.unjudged,
+        mutation_attempts=[attempt for attempt in attempts if attempt.settled],
```

## `killed` — injected-text-recorded-next-to-result/mutation-attempts-without-descriptor-cannot-record-injected-text

- **type:** `missing_case`
- **defect:** A settled mutation attempt can be created without a descriptor, which means the review can record an outcome without any injected text to display next to it.
- **expected:** Any settled mutation attempt should carry the descriptor for the injected edit so the result can include the exact injected text.
- **defective:** The attempt record allows a settled outcome to exist with no descriptor, so the review can store the result but has no injected text to show beside it.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 1

**edit** — `src/acceptance/mutation/attempt.py` lines 149-156

```diff
-    @model_validator(mode="after")
-    def _a_settled_attempt_injected_something(self) -> MutationAttempt:
-        if self.settled and self.descriptor is None:
-            raise ValueError(
-                f"defect {self.defect_id!r} is recorded as {self.outcome.value} with no "
-                "descriptor, so there is no record of what was injected"
-            )
-        return self
+    @model_validator(mode="after")
+    def _a_settled_attempt_injected_something(self) -> MutationAttempt:
+        return self
```

## `survived` — injected-text-recorded-next-to-result/mutation-block-omits-injected-text-for-unsettled-attempts

- **type:** `scope_too_narrow`
- **defect:** The report only shows the injected text when an attempt is settled, so not-mutable or not-attempted defects can be listed without the injected text that explains what was injected or why the attempt could not be settled.
- **expected:** Every mutation attempt that is recorded in the review should render the injected text alongside the result entry, including attempts that end as not_mutable or not_attempted when they have a descriptor.
- **defective:** The mutation report skips the injected text for attempts that are not settled and only prints the reason, leaving the result without the injected text next to it.
- **candidates asked:** 1
- **candidate used:** 1

**edit** — `src/acceptance/report.py` lines 296-302

```diff
-        elif attempt.settled:
-            lines.append(
-                f"    no test caught it; {len(attempt.tests_run)} candidate test(s) ran "
-                "and none failed"
-            )
-        if attempt.reason:
-            lines.append(f"    {attempt.reason}")
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

## `no_usable_edit` — mechanical-validity-checks/containment-check-only-uses-resolved-regions

- **type:** `scope_too_narrow`
- **defect:** The containment check only looks at regions that were resolved from the change set, so a defect with no resolved region can still be treated as mutable instead of being rejected mechanically.
- **expected:** If a defect names no editable region, mechanical validity rejects the edit as not mutable before any execution happens.
- **defective:** A defect with no resolved region can still reach later validity steps or be treated as valid because the containment check only runs after regions are found.
- **reason:** all 3 candidate edit(s) asked for were set aside (3 changed_nothing). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 3
- **candidate used:** None
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/mutation/validity.py lines 114..118 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 2 set aside:** `changed_nothing` — the replacement for src/acceptance/mutation/runner.py lines 104..111 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 3 set aside:** `changed_nothing` — the replacement for src/acceptance/mutation/validity.py lines 113..124 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**refused candidate 1** — `src/acceptance/mutation/validity.py` lines 114-118

```diff
-    if not named:
-        return (
-            f"the defect names no region in {descriptor.path}, so an edit there could not be "
-            "credited to it"
-        )
+    if not named:
+        return (
+            f"the defect names no region in {descriptor.path}, so an edit there could not be "
+            "credited to it"
+        )
```

**refused candidate 2** — `src/acceptance/mutation/runner.py` lines 104-111

```diff
-    regions = regions_for(defect, change_set)
-    if not regions:
-        return _not_mutable(
-            defect,
-            "the defect names no changed region with text at head, so there is no span to "
-            "replace. This is the shape of an absence defect, where the implicated lines are "
-            "where behavior should be and is not.",
-        )
+    regions = regions_for(defect, change_set)
+    if not regions:
+        return _not_mutable(
+            defect,
+            "the defect names no changed region with text at head, so there is no span to "
+            "replace. This is the shape of an absence defect, where the implicated lines are "
+            "where behavior should be and is not.",
+        )
```

**refused candidate 3** — `src/acceptance/mutation/validity.py` lines 113-124

```diff
-    named = [region for region in regions if region.path == descriptor.path]
-    if not named:
-        return (
-            f"the defect names no region in {descriptor.path}, so an edit there could not be "
-            "credited to it"
-        )
-    if not any(region.contains(descriptor.start_line, descriptor.end_line) for region in named):
-        spans = ", ".join(f"{region.start_line}..{region.end_line}" for region in named)
-        return (
-            f"the span {descriptor.start_line}..{descriptor.end_line} falls outside the "
-            f"region(s) the defect named in {descriptor.path} ({spans})"
-        )
+    named = [region for region in regions if region.path == descriptor.path]
+    if not named:
+        return (
+            f"the defect names no region in {descriptor.path}, so an edit there could not be "
+            "credited to it"
+        )
+    if not any(region.contains(descriptor.start_line, descriptor.end_line) for region in named):
+        spans = ", ".join(f"{region.start_line}..{region.end_line}" for region in named)
+        return (
+            f"the span {descriptor.start_line}..{descriptor.end_line} falls outside the "
+            f"region(s) the defect named in {descriptor.path} ({spans})"
+        )
```

## `killed` — mechanical-validity-checks/descriptor-declines-are-not-mechanically-enforced

- **type:** `unenforced_on_one_path`
- **defect:** A descriptor that declines by returning an empty region label is converted to None, but the runner still has to rely on later control flow to mark the defect not mutable, so the mechanical validity decision is not enforced at the descriptor boundary itself.
- **expected:** A declined descriptor is mechanically rejected as not mutable at the point the descriptor is interpreted, with no later stage able to treat it as a valid edit.
- **defective:** The descriptor builder can return None for a decline, and the runner separately turns that into not_mutable, leaving the validity decision unenforced at the descriptor stage.
- **candidates asked:** 2
- **candidate used:** 2
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/mutation/descriptor.py lines 199..201 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **tests failing:** 3

**refused candidate 1** — `src/acceptance/mutation/descriptor.py` lines 199-201

```diff
-    label = result.region_label.strip()
-    if not label:
-        return None
+    label = result.region_label.strip()
+    if not label:
+        return None
```

**edit** — `src/acceptance/mutation/descriptor.py` lines 199-201

```diff
-    label = result.region_label.strip()
-    if not label:
-        return None
+    label = result.region_label.strip()
+    if not label:
+        raise ValueError("declined descriptors are not mutable")
```

## `killed` — mechanical-validity-checks/mechanical-checks-bypassable-through-execution-settings

- **type:** `other`
- **defect:** The new execution path can decide whether an edit is valid by running tests and halting or proceeding, so edit validity is no longer settled only by the mechanical validity checks.
- **expected:** Mechanical validity checks alone determine whether a mutation descriptor is valid, and execution settings only affect whether execution runs after validity is established.
- **defective:** The execution tier can short-circuit or override the validity decision by halting on baseline failures or proceeding past them, so validity depends on execution control flow as well as mechanical checks.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 3

**edit** — `src/acceptance/pipeline.py` lines 274-285

```diff
-    if execution is None or not execution.enabled:
-        return [], [], []
-
-    test_ids = [test.test_id for test in tests]
-    baseline = establish_baseline(
-        test_ids,
-        repo,
-        execution.sandbox,
-        allow_failing_tests=execution.allow_failing_tests,
-    )
-    if baseline.halted:
-        raise ReviewHalted(baseline)
+    if execution is None or not execution.enabled:
+        return [], [], []
+
+    test_ids = [test.test_id for test in tests]
+    baseline = establish_baseline(
+        test_ids,
+        repo,
+        execution.sandbox,
+        allow_failing_tests=execution.allow_failing_tests,
+    )
```

## `killed` — mechanical-validity-checks/parse-check-applies-only-to-some-file-types

- **type:** `scope_too_narrow`
- **defect:** The parse validity check only covers a small hardcoded set of suffixes, so files with another parser can be mutated without being checked for parse validity.
- **expected:** Any file type that has a parser must be re-parsed after the edit, so malformed mutants are rejected mechanically for every parseable file type the criterion covers.
- **defective:** Only .py, .pyi, and .json files are parsed after mutation, so other parseable file types can slip through validity checks even when the edit breaks them.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 1

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
+            "the defect names no changed region with text at head, so there is no span to "
+            "replace. This defect cannot be edited because it names no region to edit within.",
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

**edit** — `src/acceptance/pipeline.py` lines 475-479

```diff
-    # One list, two provenances. `PairVerdict.tier` is what tells them apart, and
-    # `derive_support` reduces both with the same arithmetic — which is what
-    # keeps the rating a single implementation rather than a static one and an
-    # executed one that can drift.
-    verdicts = executed_verdicts + pair_mapping.verdicts
+    # One list, two provenances. `PairVerdict.tier` is what tells them apart, and
+    # `derive_support` reduces both with the same arithmetic — which is what
+    # keeps the rating a single implementation rather than a static one and an
+    # executed one that can drift.
+    verdicts = pair_mapping.verdicts
```

## `no_usable_edit` — no-line-execution-recording/line-execution-recording-still-present

- **type:** `other`
- **defect:** The review report or review state still includes a field or block that records executed line information, so the change continues to persist or render line execution data.
- **expected:** The delivered code should not store or display which lines of code a test executed anywhere in the review output or persisted review state.
- **defective:** The delivered code stores or renders line-execution information such as executed line spans, coverage line records, or a report section that lists executed lines.
- **reason:** all 3 candidate edit(s) asked for were set aside (1 changed_nothing, 2 refused_after_run). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 3
- **candidate used:** None
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/report.py lines 270..303 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 2 set aside:** `refused_after_run` — every one of the 3 tests that failed under the edit failed with NameError, which means the edited code no longer loads or names something that does not exist. Those failures say nothing about the named defect, so this is not counted as a kill and the defect goes to the static judge.
- **candidate 3 set aside:** `refused_after_run` — every one of the 3 tests that failed under the edit failed with NameError, which means the edited code no longer loads or names something that does not exist. Those failures say nothing about the named defect, so this is not counted as a kill and the defect goes to the static judge.

**refused candidate 1** — `src/acceptance/report.py` lines 270-303

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
+    return lines
```

**refused candidate 2** — `src/acceptance/report.py` lines 289-292

```diff
-            span = f"{descriptor.start_line}-{descriptor.end_line}"
-            lines.append(f"    injected at {descriptor.path} lines {span}:")
-            for line in descriptor.replacement.splitlines() or [""]:
-                lines.append(f"      | {line}")
+            lines.append(f"    injected at {descriptor.path} lines {span}:")
+            for line in descriptor.replacement.splitlines() or [""]:
+                lines.append(f"      | {line}")
```

**refused candidate 3** — `src/acceptance/report.py` lines 289-292

```diff
-            span = f"{descriptor.start_line}-{descriptor.end_line}"
-            lines.append(f"    injected at {descriptor.path} lines {span}:")
-            for line in descriptor.replacement.splitlines() or [""]:
-                lines.append(f"      | {line}")
+            lines.append(f"    injected at {descriptor.path} lines {span}:")
+            for line in descriptor.replacement.splitlines() or [""]:
+                lines.append(f"      | {line}")
```

## `no_usable_edit` — no-parser-not-invalid/parse-failure-becomes-not-mutable

- **type:** `other`
- **defect:** A malformed parse is converted into a generic not-mutable rejection, so the code can still be treating parser absence as an invalidity path instead of merely skipping the parse check for files that have no parser.
- **expected:** A file with no parser should pass validity on that ground alone, with parse-related rejection reserved for files that actually have a parser and fail it.
- **defective:** The validity path collapses parser-related cases into a not-mutable rejection, making parser absence function like a violation instead of a non-issue.
- **reason:** all 3 candidate edit(s) asked for were set aside (3 refused_after_run). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 3
- **candidate used:** None
- **candidate 1 set aside:** `refused_after_run` — every one of the 2 tests that failed under the edit failed with NameError, which means the edited code no longer loads or names something that does not exist. Those failures say nothing about the named defect, so this is not counted as a kill and the defect goes to the static judge.
- **candidate 2 set aside:** `refused_after_run` — every one of the 2 tests that failed under the edit failed with NameError, which means the edited code no longer loads or names something that does not exist. Those failures say nothing about the named defect, so this is not counted as a kill and the defect goes to the static judge.
- **candidate 3 set aside:** `refused_after_run` — every one of the 2 tests that failed under the edit failed with NameError, which means the edited code no longer loads or names something that does not exist. Those failures say nothing about the named defect, so this is not counted as a kill and the defect goes to the static judge.

**refused candidate 1** — `src/acceptance/mutation/validity.py` lines 126-134

```diff
-    # Check 2 — the mutated file parses, when the file has a parser.
-    parse = _parser_for(descriptor.path)
-    if parse is not None:
-        mutated = apply_span(source, descriptor)
-        try:
-            parse(mutated)
-        except _PARSE_ERRORS as error:
-            return f"the mutated {descriptor.path} does not parse: {error}"
-
+    # Check 2 — the mutated file parses, when the file has a parser.
+    parse = _parser_for(descriptor.path)
+    if parse is not None:
+        mutated = apply_span(source, descriptor)
+        try:
+            parse(mutated)
+        except _PARSE_ERRORS as error:
+            return _not_mutable(defect, f"the mutated {descriptor.path} does not parse: {error}")
+
+    return None
```

**refused candidate 2** — `src/acceptance/mutation/validity.py` lines 126-133

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
+            return _not_mutable(defect, f"the mutated {descriptor.path} does not parse: {error}")
+
+    return None
```

**refused candidate 3** — `src/acceptance/mutation/validity.py` lines 126-133

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
+            return _not_mutable(defect, f"the mutated {descriptor.path} does not parse: {error}")
+
+    return None
```

## `not_attempted` — no-parser-not-invalid/parser-check-applies-to-all-files

- **type:** `scope_too_narrow`
- **defect:** The parse check only covers a fixed set of extensions, so a file type that does have a parser but is not listed can still be rejected or mishandled as if lacking one.
- **expected:** Any file type that has a parser should be treated as valid when its mutated text still parses under that parser.
- **defective:** Only the hardcoded extensions in the parser table are recognized, and other parseable file types are treated as outside the rule or invalid by omission.
- **reason:** none of the 339 candidate tests ran at all under the mutant, which is what a mutant that breaks the module rather than its behavior looks like: the file fails during collection and no test is reached. Nothing was learned about the tests, so this defect goes to the static judge.
- **candidates asked:** 1
- **candidate used:** 1

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
+    ".toml": __import__("tomllib").loads,
+}
```

## `killed` — no-parser-not-invalid/parserless-files-still-rejected

- **type:** `condition_inverted`
- **defect:** Files without a parser are still treated as invalid, so the new validity check rejects them instead of allowing prose-only files to be mutated.
- **expected:** When a file has no parser, the validity check should skip the parse requirement and treat the file as valid on that ground.
- **defective:** When a file has no parser, the validity check reports the file invalid solely because no parser is available.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 2

**edit** — `src/acceptance/mutation/validity.py` lines 127-133

```diff
-    parse = _parser_for(descriptor.path)
-    if parse is not None:
-        mutated = apply_span(source, descriptor)
-        try:
-            parse(mutated)
-        except _PARSE_ERRORS as error:
-            return f"the mutated {descriptor.path} does not parse: {error}"
+    parse = _parser_for(descriptor.path)
+    if parse is None:
+        return f"the mutated {descriptor.path} does not parse: no parser is available"
+    mutated = apply_span(source, descriptor)
+    try:
+        parse(mutated)
+    except _PARSE_ERRORS as error:
+        return f"the mutated {descriptor.path} does not parse: {error}"
```

## `killed` — no-whole-suite-run/baseline-control-run-uses-all-tests

- **type:** `other`
- **defect:** The control run before mutation can execute every discovered test instead of only the named candidates, so the review may observe whole-suite execution before any defect injection happens.
- **expected:** The baseline run should be limited to the candidate tests named for the review.
- **defective:** The baseline establishment takes the full test id list and runs them all, which can amount to executing the project's whole suite.
- **candidates asked:** 3
- **candidate used:** 3
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/pipeline.py lines 277..283 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 2 set aside:** `changed_nothing` — the replacement for src/acceptance/pipeline.py lines 277..277 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **tests failing:** 4

**refused candidate 1** — `src/acceptance/pipeline.py` lines 277-283

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

**refused candidate 2** — `src/acceptance/pipeline.py` lines 277-277

```diff
-    test_ids = [test.test_id for test in tests]
+    test_ids = [test.test_id for test in tests]
```

**edit** — `src/acceptance/pipeline.py` lines 277-277

```diff
-    test_ids = [test.test_id for test in tests]
+    test_ids = [test.test_id for test in tests[:1]]
```

## `survived` — no-whole-suite-run/whole-suite-execution-flag

- **type:** `other`
- **defect:** The new execution path can still run the project's whole test suite because the runner is given the full discovered test list and there is no visible filter that limits execution to a named subset.
- **expected:** The execution tier should invoke only the named candidate tests, not the project's whole suite.
- **defective:** The execution tier passes the complete discovered test list into the sandbox runner, so the whole suite can be executed.
- **candidates asked:** 2
- **candidate used:** 2
- **candidate 1 set aside:** `failed_check` — the mutated src/acceptance/pipeline.py does not parse: unexpected indent (<unknown>, line 284)

**refused candidate 1** — `src/acceptance/pipeline.py` lines 277-279

```diff
-    test_ids = [test.test_id for test in tests]
-    baseline = establish_baseline(
-        test_ids,
+    test_ids = [test.test_id for test in tests]
+    baseline = establish_baseline(
+        test_ids,
+        repo,
+        execution.sandbox,
+        allow_failing_tests=execution.allow_failing_tests,
+    )
```

**edit** — `src/acceptance/mutation/runner.py` lines 136-138

```diff
-    try:
-        with mutated_copy(project_root, descriptor) as root:
-            result = run_tests(tests, root, config)
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
```

## `no_usable_edit` — observation-not-prediction/execution-verdicts-not-marked-as-observed

- **type:** `other`
- **defect:** The mutation verdicts can be stored without any field that distinguishes them as observed execution results, so later reporting may not be able to tell them apart from predicted pair verdicts.
- **expected:** Execution-derived conclusions are recorded with metadata that identifies them as results of running the candidate tests against the mutant.
- **defective:** Execution-derived conclusions are recorded in the same shape as predicted verdicts, with no distinguishing evidence tier or equivalent marker.
- **reason:** all 3 candidate edit(s) asked for were set aside (3 changed_nothing). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 3
- **candidate used:** None
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/review_state.py lines 214..227 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 2 set aside:** `changed_nothing` — the replacement for src/acceptance/review_state.py lines 214..227 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 3 set aside:** `changed_nothing` — the replacement for src/acceptance/review_state.py lines 214..227 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**refused candidate 1** — `src/acceptance/review_state.py` lines 214-227

```diff
-    # How well this one answer is known (DR-171 Decision 7). `STATIC` is a
-    # prediction the pair-judgement stage made by reading; `DEFECT_KILLED` is
-    # what the mutation runner observed by injecting the defect and running the
-    # test. One record type for both, so the rating has one implementation: a
-    # parallel record for executed verdicts would fork that arithmetic and the
-    # two copies would drift, which is the failure CLAUDE.md records against the
-    # CLI and the benchmark.
-    #
-    # A review is therefore a mixture of tiers, and a repository where the tests
-    # cannot be run is simply the case where every verdict stays `STATIC`. That
-    # makes §8.3's graceful degradation structural rather than a promise.
-    #
-    # Defaulted, so adding it orphans no recorded transcript.
-    tier: EvidenceTier = EvidenceTier.STATIC
+    # How well this one answer is known (DR-171 Decision 7). `STATIC` is a
+    # prediction the pair-judgement stage made by reading; `DEFECT_KILLED` is
+    # what the mutation runner observed by injecting the defect and running the
+    # test. One record type for both, so the rating has one implementation: a
+    # parallel record for executed verdicts would fork that arithmetic and the
+    # two copies would drift, which is the failure CLAUDE.md records against the
+    # CLI and the benchmark.
+    #
+    # A review is therefore a mixture of tiers, and a repository where the tests
+    # cannot be run is simply the case where every verdict stays `STATIC`. That
+    # makes §8.3's graceful degradation structural rather than a promise.
+    #
+    # Defaulted, so adding it orphans no recorded transcript.
+    tier: EvidenceTier = EvidenceTier.STATIC
```

**refused candidate 2** — `src/acceptance/review_state.py` lines 214-227

```diff
-    # How well this one answer is known (DR-171 Decision 7). `STATIC` is a
-    # prediction the pair-judgement stage made by reading; `DEFECT_KILLED` is
-    # what the mutation runner observed by injecting the defect and running the
-    # test. One record type for both, so the rating has one implementation: a
-    # parallel record for executed verdicts would fork that arithmetic and the
-    # two copies would drift, which is the failure CLAUDE.md records against the
-    # CLI and the benchmark.
-    #
-    # A review is therefore a mixture of tiers, and a repository where the tests
-    # cannot be run is simply the case where every verdict stays `STATIC`. That
-    # makes §8.3's graceful degradation structural rather than a promise.
-    #
-    # Defaulted, so adding it orphans no recorded transcript.
-    tier: EvidenceTier = EvidenceTier.STATIC
+    # How well this one answer is known (DR-171 Decision 7). `STATIC` is a
+    # prediction the pair-judgement stage made by reading; `DEFECT_KILLED` is
+    # what the mutation runner observed by injecting the defect and running the
+    # test. One record type for both, so the rating has one implementation: a
+    # parallel record for executed verdicts would fork that arithmetic and the
+    # two copies would drift, which is the failure CLAUDE.md records against the
+    # CLI and the benchmark.
+    #
+    # A review is therefore a mixture of tiers, and a repository where the tests
+    # cannot be run is simply the case where every verdict stays `STATIC`. That
+    # makes §8.3's graceful degradation structural rather than a promise.
+    #
+    # Defaulted, so adding it orphans no recorded transcript.
+    tier: EvidenceTier = EvidenceTier.STATIC
```

**refused candidate 3** — `src/acceptance/review_state.py` lines 214-227

```diff
-    # How well this one answer is known (DR-171 Decision 7). `STATIC` is a
-    # prediction the pair-judgement stage made by reading; `DEFECT_KILLED` is
-    # what the mutation runner observed by injecting the defect and running the
-    # test. One record type for both, so the rating has one implementation: a
-    # parallel record for executed verdicts would fork that arithmetic and the
-    # two copies would drift, which is the failure CLAUDE.md records against the
-    # CLI and the benchmark.
-    #
-    # A review is therefore a mixture of tiers, and a repository where the tests
-    # cannot be run is simply the case where every verdict stays `STATIC`. That
-    # makes §8.3's graceful degradation structural rather than a promise.
-    #
-    # Defaulted, so adding it orphans no recorded transcript.
-    tier: EvidenceTier = EvidenceTier.STATIC
+    # How well this one answer is known (DR-171 Decision 7). `STATIC` is a
+    # prediction the pair-judgement stage made by reading; `DEFECT_KILLED` is
+    # what the mutation runner observed by injecting the defect and running the
+    # test. One record type for both, so the rating has one implementation: a
+    # parallel record for executed verdicts would fork that arithmetic and the
+    # two copies would drift, which is the failure CLAUDE.md records against the
+    # CLI and the benchmark.
+    #
+    # A review is therefore a mixture of tiers, and a repository where the tests
+    # cannot be run is simply the case where every verdict stays `STATIC`. That
+    # makes §8.3's graceful degradation structural rather than a promise.
+    #
+    # Defaulted, so adding it orphans no recorded transcript.
+    tier: EvidenceTier = EvidenceTier.STATIC
```

## `survived` — observation-not-prediction/prediction-language-still-used-in-recorded-conclusion

- **type:** `other`
- **defect:** The execution-tier record can still be written in predictive language, so the stored conclusion may describe what the candidate tests would do rather than what they did.
- **expected:** The recorded conclusion text states that the candidate tests were run against the altered copy and reports the observed result.
- **defective:** The recorded conclusion text is phrased as a forecast or expectation about how the candidate tests would behave.
- **candidates asked:** 1
- **candidate used:** 1

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
+        return "The test passed when the defect was injected; another test caught it."
+    return "The test passed when the defect was injected."
```

## `killed` — parser-files-still-parse/parse-check-only-covers-python

- **type:** `scope_too_narrow`
- **defect:** The validity check only parses Python-like files, so edited files with another parser can be accepted even when they no longer parse.
- **expected:** Every file type that has a parser in the mutation validity check is parsed after the edit, and malformed output for any such file is rejected.
- **defective:** Only `.py` and `.pyi` files are parsed, while other parseable file types are left to the non-parse checks and can pass validity even if they are syntactically broken.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 1

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
+        except _PARSE_ERRORS as error:
+            return None
```

## `no_usable_edit` — preserve-code-reading-judgement/execution-off-path-skips-static-judgement

- **type:** `not_wired`
- **defect:** The new execution tier may be wired into the main review path in a way that leaves the existing code-reading judgement unreachable whenever execution is disabled or halted, so the judgement no longer participates in the delivered review flow.
- **expected:** The existing code-reading judgement remains wired into the review path and still runs for the cases the criterion covers.
- **defective:** The review path only invokes the new execution-related logic and never reaches the existing code-reading judgement on the delivered path.
- **reason:** all 3 candidate edit(s) asked for were set aside (2 changed_nothing, 1 failed_check). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 3
- **candidate used:** None
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/pipeline.py lines 457..459 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 2 set aside:** `changed_nothing` — the replacement for src/acceptance/pipeline.py lines 457..459 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 3 set aside:** `failed_check` — the edit replaces 14 lines, over the 12-line bound; the smallest edit that makes the defect true is what was asked for

**refused candidate 1** — `src/acceptance/pipeline.py` lines 457-459

```diff
-    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
-        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
-    )
+    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
+        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
+    )
```

**refused candidate 2** — `src/acceptance/pipeline.py` lines 457-459

```diff
-    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
-        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
-    )
+    attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
+        defect_sets, discovered.tests, change_set, repo, client, unusable, execution
+    )
```

**refused candidate 3** — `src/acceptance/pipeline.py` lines 461-474

```diff
-    pair_mapping = judge_pairs(
-        # Only the defects injection could not reach. The FULL `defect_sets` still
-        # goes to `derive_support` below, so a criterion's denominator is
-        # unchanged — what shrinks is the question put to the model, not the bar.
-        remaining_defect_sets(attempts, defect_sets),
-        discovered.tests,
-        change_set,
-        client,
-        repo=repo,
-        batch_size=pair_batch_size,
-        tests_per_batch=tests_per_batch,
-        unusable=unusable,
-        prior=list(ledger_prior.pair_verdicts) if ledger_prior is not None else None,
-    )
+    pair_mapping = judge_pairs(
+        defect_sets,
+        discovered.tests,
+        change_set,
+        client,
+        repo=repo,
+        batch_size=pair_batch_size,
+        tests_per_batch=tests_per_batch,
+        unusable=unusable,
+        prior=list(ledger_prior.pair_verdicts) if ledger_prior is not None else None,
+    )
```

## `survived` — preserve-code-reading-judgement/static-judgement-skipped-when-execution-runs

- **type:** `scope_too_narrow`
- **defect:** When execution is enabled and produces mutation verdicts, the pipeline can bypass the existing code-reading judgement for those defects instead of still including it in the review's output and decision-making.
- **expected:** The review always retains the existing code-reading judgement as part of its output and as part of the decision path, even when execution runs first.
- **defective:** The review replaces the code-reading judgement with execution results for defects that execution settles, so those defects no longer go through the existing judgement.
- **candidates asked:** 1
- **candidate used:** 1

**edit** — `src/acceptance/pipeline.py` lines 479-479

```diff
-    verdicts = executed_verdicts + pair_mapping.verdicts
+    verdicts = pair_mapping.verdicts + executed_verdicts
```

## `killed` — preserve-current-review-conclusions-when-unrunnable/baseline-halt-changes-review-conclusions

- **type:** `unenforced_on_one_path`
- **defect:** The control-run halt path can change the review's conclusions by stopping before the existing review logic runs, so unrunnable cases do not necessarily preserve today's conclusions.
- **expected:** When the code cannot be run, the review should still produce the same conclusions it produces today, even if the control run finds failing candidate tests or cannot complete them.
- **defective:** When the control run cannot complete or finds failing candidate tests, the review halts and returns a different outcome instead of preserving the current conclusions.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 3

**edit** — `src/acceptance/pipeline.py` lines 284-285

```diff
-    if baseline.halted:
-        raise ReviewHalted(baseline)
+    if baseline.halted:
+        pass
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
+        return [], [], []
```

## `killed` — preserve-current-review-conclusions-when-unrunnable/unrunnable-defects-return-not-attempted-instead-of-static

- **type:** `established_not_maintained`
- **defect:** A defect that execution could not settle is recorded as a mutation-stage outcome, but the later support calculation may no longer preserve the pre-existing static conclusions for those unrunnable cases.
- **expected:** When nothing can be run, defects that execution cannot settle should be handed to the existing static judgement so the review keeps the conclusions it would have reached today.
- **defective:** When execution cannot settle a defect, the code records a mutation outcome and lets that replace or alter the static conclusion instead of preserving it.
- **candidates asked:** 2
- **candidate used:** 2
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/mutation/runner.py lines 177..185 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **tests failing:** 2

**refused candidate 1** — `src/acceptance/mutation/runner.py` lines 177-185

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
+            reason=_why_unobserved(unobserved, result.outcomes),
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

**edit** — `src/acceptance/report.py` lines 312-315

```diff
-    lines = ["Candidate tests set aside (no conclusion rests on these):"]
-    for test in review.set_aside_tests:
-        lines.append(f"  [{test.kind.value}] {test.test_id}")
-        lines.append(f"    {test.reason}")
+    lines = ["Candidate tests set aside (no conclusion rests on these):"]
+    for test in review.set_aside_tests:
+        lines.append(f"  [{test.kind.value}]")
+        lines.append(f"    {test.reason}")
```

## `no_usable_edit` — report-lists-set-aside-tests/set-aside-tests-never-populated

- **type:** `not_wired`
- **defect:** The baseline/control-run path can record failing tests, but the review may never carry them through to the report, so the report has nothing to name.
- **expected:** When the control run finds failing candidate tests and the project is configured to continue, those failing tests are stored on the review and passed to report rendering.
- **defective:** The control-run results are computed, but the failing tests are not wired into the review state or report path, so the report cannot list them.
- **reason:** all 3 candidate edit(s) asked for were set aside (1 changed_nothing, 2 refused_after_run). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 3
- **candidate used:** None
- **candidate 1 set aside:** `refused_after_run` — every one of the 79 tests that failed under the edit failed with NameError, which means the edited code no longer loads or names something that does not exist. Those failures say nothing about the named defect, so this is not counted as a kill and the defect goes to the static judge.
- **candidate 2 set aside:** `refused_after_run` — every one of the 79 tests that failed under the edit failed with NameError, which means the edited code no longer loads or names something that does not exist. Those failures say nothing about the named defect, so this is not counted as a kill and the defect goes to the static judge.
- **candidate 3 set aside:** `changed_nothing` — the replacement for src/acceptance/pipeline.py lines 644..644 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**refused candidate 1** — `src/acceptance/pipeline.py` lines 644-644

```diff
-        set_aside_tests=set_aside_tests,
+        set_aside_tests=baseline.failing_tests,
```

**refused candidate 2** — `src/acceptance/pipeline.py` lines 644-644

```diff
-        set_aside_tests=set_aside_tests,
+        set_aside_tests=baseline.failing_tests,
```

**refused candidate 3** — `src/acceptance/pipeline.py` lines 644-644

```diff
-        set_aside_tests=set_aside_tests,
+        set_aside_tests=set_aside_tests,
```

## `survived` — run-candidate-tests-on-altered-copy/baseline-halt-prevents-execution

- **type:** `missing_case`
- **defect:** A failing candidate test at head halts the review before any altered-copy execution happens, so the candidate tests are never run against the mutant in that case.
- **expected:** Even when the baseline run finds failing candidate tests, the implementation should still run the candidate tests against the altered copy if the criterion is meant to hold for those inputs.
- **defective:** `establish_baseline` returns a halted baseline and `run_review` raises `ReviewHalted`, stopping before `run_mutations` can execute the candidate tests on the altered copy.
- **candidates asked:** 1
- **candidate used:** 1

**edit** — `src/acceptance/pipeline.py` lines 284-285

```diff
-    if baseline.halted:
-        raise ReviewHalted(baseline)
+    if baseline.halted and not execution.allow_failing_tests:
+        raise ReviewHalted(baseline)
```

## `killed` — run-candidate-tests-on-altered-copy/execution-flag-off-by-default

- **type:** `scope_too_narrow`
- **defect:** The mutation runner is only invoked when the new execution setting is enabled, so the candidate tests are not run against the altered copy on ordinary review runs.
- **expected:** The review should execute the candidate tests against the altered copy whenever this criterion applies, not only when an opt-in flag is set.
- **defective:** The review skips the mutation stage unless `execution.enabled` is true, returning empty mutation results instead of running the candidate tests.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 1

**edit** — `src/acceptance/pipeline.py` lines 274-275

```diff
-    if execution is None or not execution.enabled:
-        return [], [], []
+    if execution is None:
+        return [], [], []
```

## `already_present` — run-candidate-tests-on-altered-copy/no-tests-after-empty-baseline

- **type:** `missing_case`
- **defect:** When the control run leaves no usable candidate tests, the mutation stage returns without running anything against the altered copy.
- **expected:** If the criterion covers this input, the implementation should still execute the candidate tests against the altered copy rather than short-circuiting because the baseline produced no usable tests.
- **defective:** `run_mutations` returns `not_attempted` attempts immediately when `baseline.usable_tests` is empty, so no candidate tests are executed on the altered copy.
- **reason:** Lines 71-79 short-circuit to not_attempted when baseline.usable_tests is empty; removing that guard makes run_mutations still call _attempt, which then runs the candidate tests against the mutated copy.
- **candidates asked:** 1
- **candidate used:** None

- **repair corroboration:** a_test_asserts_defective
- **tests failing on the repair:** 3

**repair** — `src/acceptance/mutation/runner.py` lines 71-79

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
+    if not baseline.usable_tests:
+        return [
+            _attempt(
+                defect,
+                change_set,
+                project_root,
+                baseline.usable_tests,
+                build_descriptor,
+                config,
+                max_edit_lines,
+            )
+            for defect in defects
+        ]
```

## `already_present` — run-candidate-tests-on-altered-copy/partial-run-treated-as-not-attempted

- **type:** `other`
- **defect:** If the altered-copy test run is only partially observed, the code records the attempt as `not_attempted` instead of as an execution of the candidate tests against the altered copy.
- **expected:** The candidate tests should be treated as executed against the altered copy whenever the runner actually starts them, even if some do not complete.
- **defective:** `_classify` converts any run with unobserved outcomes into `NOT_ATTEMPTED`, so a partially executed altered-copy run is not recorded as candidate tests having been executed.
- **reason:** Lines 177-185 currently classify any run with unobserved outcomes as NOT_ATTEMPTED; changing that branch to SURVIVED makes a partially observed altered-copy run count as executed against the altered copy.
- **candidates asked:** 1
- **candidate used:** None

- **repair corroboration:** a_test_asserts_defective
- **tests failing on the repair:** 3

**repair** — `src/acceptance/mutation/runner.py` lines 177-185

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

## `no_usable_edit` — single-continuous-edit-in-named-region/descriptor-allows-multi-file-edit

- **type:** `other`
- **defect:** The mutation descriptor path can point at one file while the injected replacement is assembled from text that does not stay confined to a single continuous span in that file, so the recorded edit is not a single patch in one file.
- **expected:** The injected edit is represented as one contiguous line span in exactly one file, and the recorded descriptor/replacement pair corresponds to that single span only.
- **defective:** The implementation records or applies an edit that spans multiple disjoint regions or effectively changes more than one file, so the result is not a single continuous patch in one file.
- **reason:** all 3 candidate edit(s) asked for were set aside (3 changed_nothing). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 3
- **candidate used:** None
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/mutation/validity.py lines 119..124 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 2 set aside:** `changed_nothing` — the replacement for src/acceptance/mutation/validity.py lines 119..124 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 3 set aside:** `changed_nothing` — the replacement for src/acceptance/mutation/validity.py lines 119..124 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**refused candidate 1** — `src/acceptance/mutation/validity.py` lines 119-124

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

**refused candidate 2** — `src/acceptance/mutation/validity.py` lines 119-124

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

**refused candidate 3** — `src/acceptance/mutation/validity.py` lines 119-124

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

## `no_usable_edit` — single-continuous-edit-in-named-region/missing-region-rejected-as-mutable

- **type:** `missing_case`
- **defect:** A defect with no resolved region can still be sent through mutation instead of being rejected as uneditable, so the criterion is not enforced for defects whose named region is absent.
- **expected:** If the defect names no usable region in the delivered code, the mutation stage declines it and records that no single continuous edit can be made there.
- **defective:** The mutation stage proceeds anyway, fabricates or guesses an edit, and treats the defect as mutable despite having no named region to confine it to.
- **reason:** all 3 candidate edit(s) asked for were set aside (3 changed_nothing). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 3
- **candidate used:** None
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/mutation/runner.py lines 104..111 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 2 set aside:** `changed_nothing` — the replacement for src/acceptance/mutation/runner.py lines 105..111 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 3 set aside:** `changed_nothing` — the replacement for src/acceptance/mutation/runner.py lines 104..111 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**refused candidate 1** — `src/acceptance/mutation/runner.py` lines 104-111

```diff
-    regions = regions_for(defect, change_set)
-    if not regions:
-        return _not_mutable(
-            defect,
-            "the defect names no changed region with text at head, so there is no span to "
-            "replace. This is the shape of an absence defect, where the implicated lines are "
-            "where behavior should be and is not.",
-        )
+    regions = regions_for(defect, change_set)
+    if not regions:
+        return _not_mutable(
+            defect,
+            "the defect names no changed region with text at head, so there is no span to "
+            "replace. This is the shape of an absence defect, where the implicated lines are "
+            "where behavior should be and is not.",
+        )
```

**refused candidate 2** — `src/acceptance/mutation/runner.py` lines 105-111

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

**refused candidate 3** — `src/acceptance/mutation/runner.py` lines 104-111

```diff
-    regions = regions_for(defect, change_set)
-    if not regions:
-        return _not_mutable(
-            defect,
-            "the defect names no changed region with text at head, so there is no span to "
-            "replace. This is the shape of an absence defect, where the implicated lines are "
-            "where behavior should be and is not.",
-        )
+    regions = regions_for(defect, change_set)
+    if not regions:
+        return _not_mutable(
+            defect,
+            "the defect names no changed region with text at head, so there is no span to "
+            "replace. This is the shape of an absence defect, where the implicated lines are "
+            "where behavior should be and is not.",
+        )
```

## `no_usable_edit` — single-continuous-edit-in-named-region/region-containment-check-too-permissive

- **type:** `condition_inverted`
- **defect:** The containment check can accept an edit whose span is not actually inside the defect's named region, so the injected change is not confined to the region the defect names.
- **expected:** An edit is accepted only when its start and end lines lie wholly inside one of the defect's named regions for the same file.
- **defective:** An edit is accepted even when its span falls outside the named region, or the containment test is effectively reversed so outside spans pass and inside spans are rejected.
- **reason:** all 3 candidate edit(s) asked for were set aside (3 refused_after_run). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 3
- **candidate used:** None
- **candidate 1 set aside:** `refused_after_run` — 29 of the 339 candidate tests failed under the edit, more than 7.5% of them. An edit that makes one defect true fails the tests near it; one that fails this many has broken something shared, so the failures say nothing about the named defect and no kill is counted.
- **candidate 2 set aside:** `refused_after_run` — 29 of the 339 candidate tests failed under the edit, more than 7.5% of them. An edit that makes one defect true fails the tests near it; one that fails this many has broken something shared, so the failures say nothing about the named defect and no kill is counted.
- **candidate 3 set aside:** `refused_after_run` — 29 of the 339 candidate tests failed under the edit, more than 7.5% of them. An edit that makes one defect true fails the tests near it; one that fails this many has broken something shared, so the failures say nothing about the named defect and no kill is counted.

**refused candidate 1** — `src/acceptance/mutation/validity.py` lines 119-124

```diff
-    if not any(region.contains(descriptor.start_line, descriptor.end_line) for region in named):
-        spans = ", ".join(f"{region.start_line}..{region.end_line}" for region in named)
-        return (
-            f"the span {descriptor.start_line}..{descriptor.end_line} falls outside the "
-            f"region(s) the defect named in {descriptor.path} ({spans})"
-        )
+    if any(region.contains(descriptor.start_line, descriptor.end_line) for region in named):
+        spans = ", ".join(f"{region.start_line}..{region.end_line}" for region in named)
+        return (
+            f"the span {descriptor.start_line}..{descriptor.end_line} falls outside the "
+            f"region(s) the defect named in {descriptor.path} ({spans})"
+        )
```

**refused candidate 2** — `src/acceptance/mutation/validity.py` lines 119-124

```diff
-    if not any(region.contains(descriptor.start_line, descriptor.end_line) for region in named):
-        spans = ", ".join(f"{region.start_line}..{region.end_line}" for region in named)
-        return (
-            f"the span {descriptor.start_line}..{descriptor.end_line} falls outside the "
-            f"region(s) the defect named in {descriptor.path} ({spans})"
-        )
+    if any(region.contains(descriptor.start_line, descriptor.end_line) for region in named):
+        spans = ", ".join(f"{region.start_line}..{region.end_line}" for region in named)
+        return (
+            f"the span {descriptor.start_line}..{descriptor.end_line} falls outside the "
+            f"region(s) the defect named in {descriptor.path} ({spans})"
+        )
```

**refused candidate 3** — `src/acceptance/mutation/validity.py` lines 119-124

```diff
-    if not any(region.contains(descriptor.start_line, descriptor.end_line) for region in named):
-        spans = ", ".join(f"{region.start_line}..{region.end_line}" for region in named)
-        return (
-            f"the span {descriptor.start_line}..{descriptor.end_line} falls outside the "
-            f"region(s) the defect named in {descriptor.path} ({spans})"
-        )
+    if any(region.contains(descriptor.start_line, descriptor.end_line) for region in named):
+        spans = ", ".join(f"{region.start_line}..{region.end_line}" for region in named)
+        return (
+            f"the span {descriptor.start_line}..{descriptor.end_line} falls outside the "
+            f"region(s) the defect named in {descriptor.path} ({spans})"
+        )
```

## `no_usable_edit` — single-continuous-edit-in-named-region/span-validation-not-applied-before-injection

- **type:** `not_wired`
- **defect:** The mechanical validity checks that should enforce single-span, single-file injection may exist but not actually gate the mutation path, allowing invalid edits to be applied.
- **expected:** Before a mutant is written, the runner checks the descriptor mechanically and refuses any edit that is not one contiguous span in one file within the named region.
- **defective:** The runner builds or applies the mutant without consulting the validity gate, so an out-of-region or non-contiguous edit can still be injected.
- **reason:** all 3 candidate edit(s) asked for were set aside (3 changed_nothing). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 3
- **candidate used:** None
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/mutation/runner.py lines 130..134 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 2 set aside:** `changed_nothing` — the replacement for src/acceptance/mutation/runner.py lines 130..134 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 3 set aside:** `changed_nothing` — the replacement for src/acceptance/mutation/runner.py lines 130..134 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**refused candidate 1** — `src/acceptance/mutation/runner.py` lines 130-134

```diff
-    reason = invalidity_reason(
-        descriptor, readable, sources.get(descriptor.path, ""), max_edit_lines
-    )
-    if reason is not None:
-        return _not_mutable(defect, reason)
+    reason = invalidity_reason(
+        descriptor, readable, sources.get(descriptor.path, ""), max_edit_lines
+    )
+    if reason is not None:
+        return _not_mutable(defect, reason)
```

**refused candidate 2** — `src/acceptance/mutation/runner.py` lines 130-134

```diff
-    reason = invalidity_reason(
-        descriptor, readable, sources.get(descriptor.path, ""), max_edit_lines
-    )
-    if reason is not None:
-        return _not_mutable(defect, reason)
+    reason = invalidity_reason(
+        descriptor, readable, sources.get(descriptor.path, ""), max_edit_lines
+    )
+    if reason is not None:
+        return _not_mutable(defect, reason)
```

**refused candidate 3** — `src/acceptance/mutation/runner.py` lines 130-134

```diff
-    reason = invalidity_reason(
-        descriptor, readable, sources.get(descriptor.path, ""), max_edit_lines
-    )
-    if reason is not None:
-        return _not_mutable(defect, reason)
+    reason = invalidity_reason(
+        descriptor, readable, sources.get(descriptor.path, ""), max_edit_lines
+    )
+    if reason is not None:
+        return _not_mutable(defect, reason)
```

## `survived` — smallest-edit-that-makes-defect-true/descriptor-can-return-non-minimal-edit

- **type:** `other`
- **defect:** The mutation descriptor stage can return an edit that is valid but not the smallest edit that makes the named defect true, because the code only checks mechanical validity and accepts whatever span the model supplies.
- **expected:** For each named plausible defect, the review should choose the smallest contiguous edit that makes that defect true in the throwaway copy.
- **defective:** The review accepts a larger or otherwise non-minimal edit that still makes the defect true.
- **candidates asked:** 1
- **candidate used:** 1

**edit** — `src/acceptance/mutation/descriptor.py` lines 50-50

```diff
-Produce the SMALLEST edit that would make that defect real.
+Produce an edit that would make that defect real.
```

## `killed` — smallest-edit-that-makes-defect-true/mutation-stage-not-invoked

- **type:** `not_wired`
- **defect:** The execution tier that is supposed to build and apply the smallest edit is gated behind opt-in settings, so the review can run without ever constructing the edit at all.
- **expected:** When the criterion is being exercised, the review should actually invoke the mutation stage and build the edit in a throwaway copy.
- **defective:** The review leaves execution disabled and falls back to the static path, so no edit is built or applied.
- **candidates asked:** 2
- **candidate used:** 2
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/cli.py lines 951..954 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **tests failing:** 1

**refused candidate 1** — `src/acceptance/cli.py` lines 951-954

```diff
-                execution=ExecutionSettings(
-                    enabled=args.execute,
-                    allow_failing_tests=args.allow_failing_tests,
-                ),
+                execution=ExecutionSettings(
+                    enabled=args.execute,
+                    allow_failing_tests=args.allow_failing_tests,
+                ),
```

**edit** — `src/acceptance/cli.py` lines 951-954

```diff
-                execution=ExecutionSettings(
-                    enabled=args.execute,
-                    allow_failing_tests=args.allow_failing_tests,
-                ),
+                execution=ExecutionSettings(
+                    enabled=args.execute or True,
+                    allow_failing_tests=args.allow_failing_tests,
+                ),
```

## `no_usable_edit` — smallest-edit-that-makes-defect-true/no-search-for-smaller-edit

- **type:** `other`
- **defect:** The implementation does not appear to search among multiple candidate spans or otherwise minimize the edit after the model response, so a plausible larger edit could be used even when a smaller one exists.
- **expected:** The review should compare candidate edits and retain the smallest one that makes the defect true.
- **defective:** The review uses the first acceptable edit returned by the descriptor stage, without proving it is minimal.
- **reason:** all 3 candidate edit(s) asked for were set aside (3 changed_nothing). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 3
- **candidate used:** None
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/mutation/descriptor.py lines 191..214 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 2 set aside:** `changed_nothing` — the replacement for src/acceptance/mutation/descriptor.py lines 191..214 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 3 set aside:** `changed_nothing` — the replacement for src/acceptance/mutation/descriptor.py lines 191..214 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**refused candidate 1** — `src/acceptance/mutation/descriptor.py` lines 191-214

```diff
-def _descriptor_from(result: _Descriptor, regions: Sequence[Region]) -> MutationDescriptor | None:
-    """The answer as a `MutationDescriptor`, or `None` where it declined.
-
-    A malformed span is treated as a decline rather than raised. The stage's
-    contract to the runner is a descriptor or nothing, and an answer whose line
-    numbers do not describe a span is one the mechanical checks would have
-    refused a moment later anyway — as `not_mutable`, which is where this lands.
-    """
-    label = result.region_label.strip()
-    if not label:
-        return None
-    by_label = {region.label: region for region in regions}
-    region = by_label.get(label)
-    if region is None:
-        return None
-    if result.start_line < 1 or result.end_line < result.start_line:
-        return None
-    return MutationDescriptor(
-        path=region.path,
-        start_line=result.start_line,
-        end_line=result.end_line,
-        replacement=result.replacement,
-        region_label=label,
-    )
+def _descriptor_from(result: _Descriptor, regions: Sequence[Region]) -> MutationDescriptor | None:
+    """The answer as a `MutationDescriptor`, or `None` where it declined.
+
+    A malformed span is treated as a decline rather than raised. The stage's
+    contract to the runner is a descriptor or nothing, and an answer whose line
+    numbers do not describe a span is one the mechanical checks would have
+    refused a moment later anyway — as `not_mutable`, which is where this lands.
+    """
+    label = result.region_label.strip()
+    if not label:
+        return None
+    by_label = {region.label: region for region in regions}
+    region = by_label.get(label)
+    if region is None:
+        return None
+    if result.start_line < 1 or result.end_line < result.start_line:
+        return None
+    return MutationDescriptor(
+        path=region.path,
+        start_line=result.start_line,
+        end_line=result.end_line,
+        replacement=result.replacement,
+        region_label=label,
+    )
```

**refused candidate 2** — `src/acceptance/mutation/descriptor.py` lines 191-214

```diff
-def _descriptor_from(result: _Descriptor, regions: Sequence[Region]) -> MutationDescriptor | None:
-    """The answer as a `MutationDescriptor`, or `None` where it declined.
-
-    A malformed span is treated as a decline rather than raised. The stage's
-    contract to the runner is a descriptor or nothing, and an answer whose line
-    numbers do not describe a span is one the mechanical checks would have
-    refused a moment later anyway — as `not_mutable`, which is where this lands.
-    """
-    label = result.region_label.strip()
-    if not label:
-        return None
-    by_label = {region.label: region for region in regions}
-    region = by_label.get(label)
-    if region is None:
-        return None
-    if result.start_line < 1 or result.end_line < result.start_line:
-        return None
-    return MutationDescriptor(
-        path=region.path,
-        start_line=result.start_line,
-        end_line=result.end_line,
-        replacement=result.replacement,
-        region_label=label,
-    )
+def _descriptor_from(result: _Descriptor, regions: Sequence[Region]) -> MutationDescriptor | None:
+    """The answer as a `MutationDescriptor`, or `None` where it declined.
+
+    A malformed span is treated as a decline rather than raised. The stage's
+    contract to the runner is a descriptor or nothing, and an answer whose line
+    numbers do not describe a span is one the mechanical checks would have
+    refused a moment later anyway — as `not_mutable`, which is where this lands.
+    """
+    label = result.region_label.strip()
+    if not label:
+        return None
+    by_label = {region.label: region for region in regions}
+    region = by_label.get(label)
+    if region is None:
+        return None
+    if result.start_line < 1 or result.end_line < result.start_line:
+        return None
+    return MutationDescriptor(
+        path=region.path,
+        start_line=result.start_line,
+        end_line=result.end_line,
+        replacement=result.replacement,
+        region_label=label,
+    )
```

**refused candidate 3** — `src/acceptance/mutation/descriptor.py` lines 191-214

```diff
-def _descriptor_from(result: _Descriptor, regions: Sequence[Region]) -> MutationDescriptor | None:
-    """The answer as a `MutationDescriptor`, or `None` where it declined.
-
-    A malformed span is treated as a decline rather than raised. The stage's
-    contract to the runner is a descriptor or nothing, and an answer whose line
-    numbers do not describe a span is one the mechanical checks would have
-    refused a moment later anyway — as `not_mutable`, which is where this lands.
-    """
-    label = result.region_label.strip()
-    if not label:
-        return None
-    by_label = {region.label: region for region in regions}
-    region = by_label.get(label)
-    if region is None:
-        return None
-    if result.start_line < 1 or result.end_line < result.start_line:
-        return None
-    return MutationDescriptor(
-        path=region.path,
-        start_line=result.start_line,
-        end_line=result.end_line,
-        replacement=result.replacement,
-        region_label=label,
-    )
+def _descriptor_from(result: _Descriptor, regions: Sequence[Region]) -> MutationDescriptor | None:
+    """The answer as a `MutationDescriptor`, or `None` where it declined.
+
+    A malformed span is treated as a decline rather than raised. The stage's
+    contract to the runner is a descriptor or nothing, and an answer whose line
+    numbers do not describe a span is one the mechanical checks would have
+    refused a moment later anyway — as `not_mutable`, which is where this lands.
+    """
+    label = result.region_label.strip()
+    if not label:
+        return None
+    by_label = {region.label: region for region in regions}
+    region = by_label.get(label)
+    if region is None:
+        return None
+    if result.start_line < 1 or result.end_line < result.start_line:
+        return None
+    return MutationDescriptor(
+        path=region.path,
+        start_line=result.start_line,
+        end_line=result.end_line,
+        replacement=result.replacement,
+        region_label=label,
+    )
```

## `killed` — smallest-edit-that-makes-defect-true/region-bounds-can-overconstrain-minimality

- **type:** `scope_too_narrow`
- **defect:** The descriptor stage only considers regions already resolved from the defect's code refs, so a smaller edit outside those regions would never be found even if it would make the defect true.
- **expected:** The review should be able to build the smallest edit that makes the defect true wherever that edit must land in the throwaway copy.
- **defective:** The review restricts candidate edits to predeclared regions and may miss a smaller valid edit elsewhere in the file or project.
- **candidates asked:** 2
- **candidate used:** 2
- **candidate 1 set aside:** `failed_check` — the mutated src/acceptance/mutation/descriptor.py does not parse: invalid character '—' (U+2014) (<unknown>, line 126)
- **tests failing:** 2

**refused candidate 1** — `src/acceptance/mutation/descriptor.py` lines 123-131

```diff
-    A defect with no resolved region is not asked about at all. There is nothing
-    to offer the call and nothing it could answer, and spending a request to be
-    told so would cost one per absence defect on every review.
-    """
-    asking = [defect for defect in defects if regions_by_defect.get(defect.id)]
-
-    answers = map_calls(
-        asking,
-        lambda defect: _ask_about(defect, regions_by_defect[defect.id], sources, client),
+    """One descriptor per defect, or `None` where the stage declined.
+
+    Calls are issued concurrently and the results are recorded in the order the
+    defects were given, not in completion order — `concurrency.py` rule 2, which
+    is what keeps two runs over the same input byte-identical.
+
+    A defect with no resolved region is not asked about at all. There is nothing
+    to offer the call and nothing it could answer, and spending a request to be
+    told so would cost one per absence defect on every review.
+    """
+    asking = defects
+
+    answers = map_calls(
+        asking,
+        lambda defect: _ask_about(defect, regions_by_defect[defect.id], sources, client),
+    )
```

**edit** — `src/acceptance/mutation/descriptor.py` lines 127-127

```diff
-    asking = [defect for defect in defects if regions_by_defect.get(defect.id)]
+    asking = defects
```

## `no_usable_edit` — test-fails-discriminate-defect/baseline-failure-halts-before-discrimination

- **type:** `missing_case`
- **defect:** A candidate test that already fails at head prevents the mutant run from ever reaching the point where a later failure could be recorded as discriminating for the defect.
- **expected:** When the control run finds failing candidate tests and the project does not allow them to be set aside, the review stops before mutation and reports why.
- **defective:** The review proceeds into mutation anyway, so a test that already failed at head can later be treated as discriminating for the defect.
- **reason:** all 3 candidate edit(s) asked for were set aside (3 failed_check). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 3
- **candidate used:** None
- **candidate 1 set aside:** `failed_check` — the mutated src/acceptance/mutation/baseline.py does not parse: unmatched ')' (<unknown>, line 162)
- **candidate 2 set aside:** `failed_check` — the mutated src/acceptance/mutation/baseline.py does not parse: unmatched ')' (<unknown>, line 162)
- **candidate 3 set aside:** `failed_check` — the mutated src/acceptance/mutation/baseline.py does not parse: unmatched ')' (<unknown>, line 162)

**refused candidate 1** — `src/acceptance/mutation/baseline.py` lines 150-160

```diff
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

**refused candidate 2** — `src/acceptance/mutation/baseline.py` lines 150-160

```diff
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

**refused candidate 3** — `src/acceptance/mutation/baseline.py` lines 150-160

```diff
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

## `no_usable_edit` — test-fails-discriminate-defect/killed-tests-not-marked-as-killing

- **type:** `wrong_output_shape`
- **defect:** A failing test under mutation is recorded, but not in the form that says it discriminates for the defect, so downstream support logic cannot treat it as a kill.
- **expected:** A failing candidate test is recorded as a settled mutation outcome with the failing test listed among the defect's killing tests and a verdict marked as killing that defect.
- **defective:** A failing candidate test is recorded without the killing-test linkage or with the wrong tier/kills shape, so it does not read as a discriminating verdict for that defect.
- **reason:** all 3 candidate edit(s) asked for were set aside (1 changed_nothing, 2 failed_check). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 3
- **candidate used:** None
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/review_state.py lines 214..227 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 2 set aside:** `failed_check` — the mutated src/acceptance/mutation/verdicts.py does not parse: unmatched ')' (<unknown>, line 69)
- **candidate 3 set aside:** `failed_check` — the mutated src/acceptance/mutation/verdicts.py does not parse: unmatched ')' (<unknown>, line 68)

**refused candidate 1** — `src/acceptance/review_state.py` lines 214-227

```diff
-    # How well this one answer is known (DR-171 Decision 7). `STATIC` is a
-    # prediction the pair-judgement stage made by reading; `DEFECT_KILLED` is
-    # what the mutation runner observed by injecting the defect and running the
-    # test. One record type for both, so the rating has one implementation: a
-    # parallel record for executed verdicts would fork that arithmetic and the
-    # two copies would drift, which is the failure CLAUDE.md records against the
-    # CLI and the benchmark.
-    #
-    # A review is therefore a mixture of tiers, and a repository where the tests
-    # cannot be run is simply the case where every verdict stays `STATIC`. That
-    # makes §8.3's graceful degradation structural rather than a promise.
-    #
-    # Defaulted, so adding it orphans no recorded transcript.
-    tier: EvidenceTier = EvidenceTier.STATIC
+    # How well this one answer is known (DR-171 Decision 7). `STATIC` is a
+    # prediction the pair-judgement stage made by reading; `DEFECT_KILLED` is
+    # what the mutation runner observed by injecting the defect and running the
+    # test. One record type for both, so the rating has one implementation: a
+    # parallel record for executed verdicts would fork that arithmetic and the
+    # two copies would drift, which is the failure CLAUDE.md records against the
+    # CLI and the benchmark.
+    #
+    # A review is therefore a mixture of tiers, and a repository where the tests
+    # cannot be run is simply the case where every verdict stays `STATIC`. That
+    # makes §8.3's graceful degradation structural rather than a promise.
+    #
+    # Defaulted, so adding it orphans no recorded transcript.
+    tier: EvidenceTier = EvidenceTier.STATIC
```

**refused candidate 2** — `src/acceptance/mutation/verdicts.py` lines 58-66

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
+            verdicts.append(
+                PairVerdict(
+                    defect_id=attempt.defect_id,
+                    test_id=test_id,
+                    kills=test_id in killing,
+                    reason=_reason(attempt, kills=test_id in killing),
+                    tier=EvidenceTier.DEFECT_KILLED,
+                    defect_text=texts.get(attempt.defect_id, ""),
+                    carried_from=attempt.defect_id if test_id in killing else None,
+                )
+            )
```

**refused candidate 3** — `src/acceptance/mutation/verdicts.py` lines 58-66

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
```

## `killed` — test-fails-discriminate-defect/mutation-kill-not-recorded-as-discriminating

- **type:** `not_wired`
- **defect:** A candidate test can fail against the injected mutant, but that failure is not turned into a recorded discriminating verdict for the named defect.
- **expected:** When a mutant run produces a failing candidate test, the review records a verdict for that defect/test pair showing the test discriminates for the defect.
- **defective:** The mutant run may detect the failing test, but the result is only kept as an attempt or baseline note and never becomes a recorded discriminating verdict.
- **candidates asked:** 2
- **candidate used:** 2
- **candidate 1 set aside:** `failed_check` — the edit replaces 16 lines, over the 12-line bound; the smallest edit that makes the defect true is what was asked for
- **tests failing:** 6

**refused candidate 1** — `src/acceptance/mutation/verdicts.py` lines 53-68

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

**edit** — `src/acceptance/mutation/verdicts.py` lines 57-67

```diff
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
+        for test_id in attempt.tests_run:
+            verdicts.append(
+                PairVerdict(
+                    defect_id=attempt.defect_id,
+                    test_id=test_id,
+                    kills=test_id in killing,
+                    reason=_reason(attempt, kills=test_id in killing),
+                    tier=EvidenceTier.STATIC,
+                    defect_text=texts.get(attempt.defect_id, ""),
+                )
+            )
```

## `killed` — test-fails-discriminate-defect/mutation-verdicts-dropped-from-review

- **type:** `not_wired`
- **defect:** The execution stage can produce discriminating verdicts, but they are not carried into the review record that the report and support code read.
- **expected:** Executed discriminating verdicts are appended into the review's pair verdicts and used by support/reporting so the review records that the test discriminates for the defect.
- **defective:** The execution stage computes verdicts, but the review continues to use only the static pair-judgement verdicts, so the failing test is not recorded as discriminating for the defect.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 3

**edit** — `src/acceptance/pipeline.py` lines 479-479

```diff
-    verdicts = executed_verdicts + pair_mapping.verdicts
+    verdicts = pair_mapping.verdicts
```

## `killed` — tests-candidate-selection/execution-tier-alters-candidate-selection

- **type:** `other`
- **defect:** The new execution tier can stop the review after the control run and remove failing candidate tests from later mutation and rating, so the set of tests treated as candidates is no longer the same as before.
- **expected:** The code that decides whether tests are candidates should remain unchanged by the new execution path; candidate selection should still be determined only by the existing discovery logic.
- **defective:** The code establishes a baseline run, halts on failing candidate tests unless overridden, and filters those tests out of later stages, changing which tests are treated as candidates.
- **candidates asked:** 2
- **candidate used:** 2
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/pipeline.py lines 284..285 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **tests failing:** 3

**refused candidate 1** — `src/acceptance/pipeline.py` lines 284-285

```diff
-    if baseline.halted:
-        raise ReviewHalted(baseline)
+    if baseline.halted:
+        raise ReviewHalted(baseline)
```

**edit** — `src/acceptance/pipeline.py` lines 284-285

```diff
-    if baseline.halted:
-        raise ReviewHalted(baseline)
+    if baseline.halted:
+        return [], [], baseline.set_aside
```

## `killed` — tests-candidate-selection/execution-tier-changes-test-run-eligibility

- **type:** `other`
- **defect:** The new execution settings introduce a path that decides whether the review can run tests at all, instead of leaving that decision to the existing review flow.
- **expected:** The code should not add any new decision about whether the project's tests can be run at all; that decision should stay where it already was.
- **defective:** The pipeline now calls a baseline control run and can raise ReviewHalted when candidate tests fail at head, so the review itself decides whether tests may run.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 3

**edit** — `src/acceptance/pipeline.py` lines 277-285

```diff
-    test_ids = [test.test_id for test in tests]
-    baseline = establish_baseline(
-        test_ids,
-        repo,
-        execution.sandbox,
-        allow_failing_tests=execution.allow_failing_tests,
-    )
-    if baseline.halted:
-        raise ReviewHalted(baseline)
+    test_ids = [test.test_id for test in tests]
+    baseline = establish_baseline(
+        test_ids,
+        repo,
+        execution.sandbox,
+        allow_failing_tests=execution.allow_failing_tests,
+    )
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
+    verdicts = pair_mapping.verdicts + executed_verdicts
```

## `already_present` — weaker-tier-evidence/mutation-attempt-tier-returns-stronger-evidence

- **type:** `other`
- **defect:** The mutation attempt tier helper maps settling outcomes to `DEFECT_KILLED`, so the execution path can produce stronger-than-weaker evidence for this judgement.
- **expected:** The mutation execution path must record this judgement using the weaker evidence tier.
- **defective:** `tier_for()` returns `EvidenceTier.DEFECT_KILLED` for `killed` and `survived` outcomes, and `MutationAttempt.tier` exposes that stronger tier.
- **reason:** Lines 10-12 and 60-61 currently map both settling outcomes to DEFECT_KILLED, so MutationAttempt.tier exposes the stronger tier for killed/survived outcomes.
- **candidates asked:** 1
- **candidate used:** None

- **repair corroboration:** a_test_asserts_defective
- **tests failing on the repair:** 7

**repair** — `src/acceptance/mutation/attempt.py` lines 60-60

```diff
-    tier = EvidenceTier.DEFECT_KILLED if kind in SETTLING_KINDS else EvidenceTier.STATIC
+    tier = EvidenceTier.STATIC if kind in SETTLING_KINDS else EvidenceTier.DEFECT_KILLED
```

## `killed` — weaker-tier-evidence/pair-verdict-tier-default-stays-static

- **type:** `scope_too_narrow`
- **defect:** Only the new `PairVerdict.tier` field defaults to `STATIC`; the execution path can still create verdicts at `DEFECT_KILLED`, so the weaker tier is not enforced for all records that feed this judgement.
- **expected:** Every record that contributes to this judgement should be stored at the weaker evidence tier.
- **defective:** `PairVerdict` defaults to `STATIC`, but `verdicts_from()` explicitly emits `PairVerdict(..., tier=EvidenceTier.DEFECT_KILLED)` for settled mutation attempts.
- **candidates asked:** 1
- **candidate used:** 1
- **tests failing:** 6

**edit** — `src/acceptance/mutation/verdicts.py` lines 64-64

```diff
-                    tier=EvidenceTier.DEFECT_KILLED,
+                    tier=EvidenceTier.STATIC,
```

## `no_usable_edit` — weaker-tier-evidence/report-shows-executed-verdicts-as-stronger-tier

- **type:** `other`
- **defect:** The report renders mutation attempts and set-aside tests, but the executed verdicts are still stored as stronger evidence, so the review output can reflect stronger-tier evidence instead of only the weaker tier.
- **expected:** The review record for this judgement should present only weaker-tier evidence.
- **defective:** `render_report()` includes the mutation block, and the underlying attempts/verdicts can carry `DEFECT_KILLED` rather than staying at the weaker tier.
- **reason:** all 3 candidate edit(s) asked for were set aside (3 changed_nothing). That is a fact about these candidates, not about the defect, which goes to the static judge like any defect with no usable edit.
- **candidates asked:** 3
- **candidate used:** None
- **candidate 1 set aside:** `changed_nothing` — the replacement for src/acceptance/report.py lines 283..283 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 2 set aside:** `changed_nothing` — the replacement for src/acceptance/report.py lines 283..283 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced
- **candidate 3 set aside:** `changed_nothing` — the replacement for src/acceptance/report.py lines 283..283 is identical to what it replaces, so nothing would be injected and every test would 'survive' a defect that was never introduced

**refused candidate 1** — `src/acceptance/report.py` lines 283-283

```diff
-    lines = ["Defects injected, and which tests caught them:"]
+    lines = ["Defects injected, and which tests caught them:"]
```

**refused candidate 2** — `src/acceptance/report.py` lines 283-283

```diff
-    lines = ["Defects injected, and which tests caught them:"]
+    lines = ["Defects injected, and which tests caught them:"]
```

**refused candidate 3** — `src/acceptance/report.py` lines 283-283

```diff
-    lines = ["Defects injected, and which tests caught them:"]
+    lines = ["Defects injected, and which tests caught them:"]
```

