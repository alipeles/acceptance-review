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

### [2026-08-12] A weak obligation no test can evidence aborts the whole review
- **Kind:** filing (new issue, child of #185)
- **Found during:** #261/#239, Gate 2, run 1
- **Where:** `src/acceptance/coverage/recommendations.py:182`
- **Severity:** blocker — it is the only thing keeping #261/#239's Gate 2 from
  completing, and it makes configuration-only changes unreviewable in general
- **What's wrong:** `recommend_tests` requires a recommendation for **every**
  weak obligation and raises `SchemaValidationError` otherwise. There is no way
  for the stage to record that an obligation is one *no test can evidence*. On a
  change to `ci.yml`, `pyproject.toml` and formatting, the model answered the
  three obligations a pytest could evidence and declined nine that are properties
  of build steps, action versions and a version pin — a principled split, not a
  truncated answer — and the run aborted, discarding a completed coverage stage
  that had classified all 19 obligations `addressed`.
- **Why I didn't act:** the fix adds a disposition to the recommendation response
  schema, which re-records that stage's transcripts, and it needs a design call
  on how the verdict treats an obligation that is addressed but unevidenceable.
  Both are out of scope for a formatter-and-lint change.
- **Drafted fix:** file as a child of #185, `bug` / `track:checker`:

  > **Title:** A weak obligation that no test can evidence aborts the entire review
  >
  > From #261/#239's Gate 2 (`dogfood-logs/261-gate2-run1/`):
  >
  > ```
  > acceptance: model error: no recommendation for 9 of 12 weak obligation(s):
  > partition-test-is-not-ignored, dev-dependencies-pin-ruff-exact-version,
  > build-runs-formatting-check, build-fails-on-formatting-check-report,
  > build-fails-on-lint-check-error, lint-step-preserves-lint-exit-code,
  > checkout-action-not-node20-major, python-setup-action-not-node20-major,
  > python-sources-formatter-and-lint-clean
  > ```
  >
  > `recommendations.py:182` requires a recommendation for every weak obligation
  > and raises otherwise. The guard is deliberate and its comment is right about
  > why: a response answering 3 of 5 used to yield a report where two silently
  > carried no recommendation, indistinguishable from a complete answer.
  >
  > What it has no room for is an obligation for which **no test is the right
  > instrument**. The answer here was not partial. The model recommended for
  > exactly the three obligations a pytest could evidence —
  > `python-files-ruff-format-clean`, `python-files-ruff-check-clean`,
  > `partition-test-expects-specific-exception` — and declined the nine that are
  > properties of `ci.yml` steps, GitHub Action major versions, and a pin in
  > `pyproject.toml`. No pytest sensibly evidences *"the build's checkout action
  > is not on Node 20."*
  >
  > Two things make this worse than a bad rating:
  >
  > 1. **It is a hard abort, not a degraded report.** The coverage stage had
  >    already classified all 19 obligations `addressed`, with rationales citing
  >    real diff hunks. None of that reaches the user. A configuration-only
  >    change cannot be reviewed at all.
  > 2. **It scales with the batch.** `recommend_tests` makes one unpartitioned
  >    call carrying every weak obligation, so a single unanswerable obligation
  >    discards the other eleven. Same shape as the `judge_discrimination` call
  >    #191 is partitioning.
  >
  > Suggested direction, for discussion rather than as a prescription: give the
  > recommendation response an explicit *"no test can evidence this obligation"*
  > disposition with a reason, so declining is representable and recorded rather
  > than being a schema violation. That keeps the guard's real purpose — a silent
  > omission stays rejected — while separating *"the model skipped it"* from
  > *"the model correctly says testing is the wrong instrument here."* The
  > verdict then needs a rule for an obligation that is `addressed` but
  > unevidenceable by test; §9.3's `Indeterminate` is the obvious candidate,
  > since positive results are bounded and this is exactly a case where no test
  > tier is achievable.
  >
  > Worth noting this was predicted before the run rather than rationalised
  > after: `dogfood-logs/261-gate1-run2/judgement.md` recorded that none of the
  > mandate's obligations could be supported by a pytest, and that the question
  > for Gate 2 was whether the tool had any evidence path for a
  > configuration-only change. It has none, and the absence is fatal rather than
  > graceful.
  >
  > ## Second instance, on a tests-only change (#258 Gate 2)
  >
  > Independently hit by #258 the same day, which matters because the two
  > mandates have nothing in common — that one is a CI-and-formatting change, this
  > one touches `tests/` only:
  >
  > ```
  > acceptance: model error: no recommendation for 2 of 13 weak obligation(s):
  > region-coverage-omits-missing-path, no-failures-without-root-task-file
  > ```
  >
  > Deterministic over three runs (two `record`, one `replay`).
  > `dogfood-logs/258-gate2-run1/`.
  >
  > The recorded transcript (`21e168cc…`) settles what the error message cannot,
  > and rules out the two readings that would otherwise fit:
  >
  > - **Not truncation.** The response parses as complete JSON, terminates on
  >   `"}]}`, and used 2,236 completion tokens with no `max_tokens` in the request.
  > - **Not a positional or volume effect.** The skipped obligations sit at
  >   positions **10 and 11 of 13**, and 12 and 13 were answered — it stepped over
  >   two in the middle and carried on. All 13 ids were in the request and both
  >   missing ids appear in the enum-constrained schema, so the model could have
  >   named them and chose not to.
  >
  > What the two have in common is that **no test can close their gap**:
  > `region-coverage-omits-missing-path` is provided by `glob` resolving a literal
  > final component through `exists()` — verified by injection, since deleting the
  > `is_file()` filter leaves the test green — and
  > `no-failures-without-root-task-file` is a property of a whole suite run, not
  > assertable from inside one without invoking pytest recursively.
  >
  > **This corrects one point above.** The batch-scaling reading — *"a single
  > unanswerable obligation discards the other eleven… same shape as the
  > `judge_discrimination` call #191 is partitioning"* — is right about the blast
  > radius and wrong about the cause, and partitioning will **not** fix it. At a
  > partition of five these two obligations are still unanswerable and the same
  > error fires on a smaller call. Partitioning shrinks how much collateral each
  > abort destroys; it does not remove the abort. The two issues are siblings in
  > stage, not in cause.
  >
  > ## The design already contains this judgement, scoped too narrowly
  >
  > `_weak_obligations` (`recommendations.py:81`) already excludes `CODE_ONLY`
  > obligations, and its docstring gives precisely the reasoning both instances
  > need:
  >
  > > Theirs is not a gap a test could close: they are satisfied by the absence of
  > > excluded work, and no test can assert that work was not done. Recommending
  > > one would prescribe evidence that cannot exist, which is worse than
  > > recommending nothing — #146's review demanded a test for "we didn't also do
  > > something else".
  >
  > That is the same judgement the suggested disposition would make, already
  > written down and already accepted — it is simply scoped to scope exclusions.
  > #258's two are ordinary `boundary` and `functional` obligations, and #261's
  > nine are properties of build steps and version pins. Neither set is reached.
  >
  > Also worth fixing while here: **the transcript records no stop reason**, on
  > either the request or the response. Separating truncation from a
  > short-but-complete answer required reconstructing it from token counts and
  > JSON well-formedness, which is exactly what the recording exists to make
  > unnecessary.
- **Status:** open — **two independent instances**, #261/#239 and #258, both
  blocking their Gate 2. File as one issue carrying both.

### [2026-08-12] Scope-exclusion typing flips wholesale between two runs over the same requirements
- **Kind:** filing (comment on existing issue #205)
- **Found during:** #258, Gate 1, runs 1 and 2
- **Where:** `dogfood-logs/258-gate1-run1/output.log` and `…-run2/output.log`, `exclusion-01`…`exclusion-05`
- **Severity:** nice-to-have
- **What's wrong:** the five `## Scope exclusions` requirements are **byte-identical
  between the two runs** — the only edit between them was deleting a line from
  `## Completion expectations` — and their types share nothing across the pair:
  `human_review` ×5 in run 1, then `compatibility` ×1 + `functional` ×4 in run 2.
- **Why I didn't act:** #205 already owns assigning types in a pass of their own,
  and nothing in #258 depends on the exclusions' type.
- **Drafted fix:** comment on #205:

  > A sharper instance than #191's, from #258's Gate 1
  > (`dogfood-logs/258-gate1-run1/` and `…-run2/`), because here the two runs are
  > a controlled pair: the five exclusion requirements are byte-identical across
  > them, and the only change to the task file was one deleted line in a
  > *different* section.
  >
  > | requirement | run 1 | run 2 |
  > |---|---|---|
  > | `exclusion-01` | `human_review` | `compatibility` |
  > | `exclusion-02` | `human_review` | `functional` |
  > | `exclusion-03` | `human_review` | `functional` |
  > | `exclusion-04` | `human_review` | `functional` |
  > | `exclusion-05` | `human_review` | `functional` |
  >
  > Five for five, with **no overlap between the runs**. #191's instance showed
  > the type co-varying with the phrasing *within* one response; this shows it
  > moving wholesale *between* responses with the input held fixed. Together they
  > argue the type is a by-product of the sentence that came out rather than a
  > property of the requirement that went in.
  >
  > Worth recording what it does **not** cost today, so the priority is not
  > overstated: the type is consumed structurally in exactly one place,
  > `requirement/linking.py:171`, which keys on `TEST_DEMAND` alone. Neither
  > typing changes any downstream behavior on this task file, and `human_review`
  > as a *type* does not raise a human-review pause — that is the separate
  > `AdmissibleEvidence` axis. The defect is that the field carries no reliable
  > information, not that it currently misroutes anything.
- **Status:** open

### [2026-08-12] The shard convention has no cleanup mechanism, only a rule
- **Kind:** decision
- **Found during:** #258, Gate 1 (raised) · #261, Gate 1 (migration landed)
- **Where:** `session-state/`, and `CLAUDE.md` *Repo layout*
- **Severity:** nice-to-have
- **What's wrong:** the shard itself is **done** — `session-state.md` migrated to
  `session-state/191.md`, `258.md` and `261.md` alongside it, and `CLAUDE.md`,
  `.acceptance/ignore` and the `/orient` skill all rewritten to the new path.
  What is still owed is the human's condition on approving it: that there be a
  way to clean up rather than accrete shards for tasks that have landed. The
  drafted rule — *"delete it when the task lands, so the directory is the list of
  what is actually in flight"* — is a convention, and conventions of exactly this
  kind are what `session-state.md` itself accreted under.
- **Why I didn't act:** out of scope for #261, which is formatter and lint gates.
  A mechanism here is a new script with its own tests, not a line of config.
- **Drafted fix — recommendation: the rule alone, for now.** Revisit only if a
  stale shard actually survives a landed task. The cheap check, if one is wanted
  later: a step that lists `session-state/*.md` whose issue number `gh` reports
  as closed. **Rejected alternative:** wiring it into CI — it would need `gh`
  auth in the workflow to answer "is this issue closed", which buys a
  nice-to-have at the cost of a credential in the build.
- **Status:** open — the migration is landed; only the cleanup question remains.
### [2026-08-12] #189's harness duplicates the client contract in two places, and both had silently drifted
- **Kind:** filing (new issue, child of #186)
- **Found during:** #191, taking the pre-change baseline
- **Where:** `src/acceptance/benchmark/instability.py` — `run_once` (client
  construction) and `ObservingClient.complete` (method signature)
- **Severity:** blocker — #191's Acceptance requires the harness to run
- **What's wrong:** the harness restates `ModelClient`'s contract in two places
  instead of delegating, and #259 broke **both**. Neither failed at import, at
  lint, or in #189's own 42 tests; both failed on the first genuine run, one
  after the other:

  1. `run_once` builds `ObservingClient(...)` field by field with five of the
     parameters `RunConfig.build_client()` passes. #259 added `embedding_model`
     to the factory, the hand-rolled copy never got it →
     `LLMError: this client has no embedding model configured` at
     `linking.py:285`.
  2. `ObservingClient.complete` pins the parameter list positionally. #259 added
     `stage_controls` → `TypeError: ObservingClient.complete() got an unexpected
     keyword argument 'stage_controls'`.

  The class docstring already claims *"Delegation happens through
  `super().complete`, so recording, replay, request keying and determinism
  controls are untouched."* That claim was false for any parameter added after
  #189 closed.

  **Nothing caught it because nothing ever ran it.** #189's tests all inject a
  `client_factory`, so the default construction is never exercised, and **no
  baseline was ever recorded from #189** — so the harness sat broken from #259
  merging until #191 asked it for a number.
- **Why I didn't act *fully*:** two unblocking commits are on
  `191-partition-discrimination` (`24b3ea3`, and the `*args/**kwargs` forwarding
  fix) because #191's Acceptance is unreachable without them (*Working
  agreement* §4 exception). The **missing test** is the real fix and belongs to
  #186.
- **Drafted fix:** file as a child of #186, `bug` / `track:benchmark`:

  > **Title:** The instability harness restates the client contract in two places, and both drifted silently
  >
  > `benchmark/instability.py` duplicates `ModelClient`'s contract twice rather
  > than delegating. #259 broke both, and both stayed broken and invisible until
  > #191 took the first real baseline:
  >
  > | site | what it duplicates | what #259 added | symptom |
  > |---|---|---|---|
  > | `run_once` | `RunConfig.build_client()`'s parameter set | `embedding_model` | `LLMError: this client has no embedding model configured` |
  > | `ObservingClient.complete` | `ModelClient.complete`'s signature | `stage_controls` | `TypeError: unexpected keyword argument 'stage_controls'` |
  >
  > The class docstring asserts that delegation leaves recording, replay, request
  > keying and determinism controls untouched. Positionally pinning the signature
  > makes that false for every parameter added afterwards — the second failure is
  > the docstring's own claim being violated by the code beneath it.
  >
  > **The fix that matters is the missing test.** #189's 42 tests all inject a
  > `client_factory`, so the default construction path — the one every real
  > caller takes — is never exercised. This is exactly the shape CLAUDE.md warns
  > about: *a helper with a good unit test that the pipeline never actually
  > calls.* A test must run the harness through its default construction, over a
  > tiny recorded case, and fail if the pipeline's client gains a parameter the
  > harness does not pass.
  >
  > Worth recording as evidence for #253 (determinism as one owned component):
  > this is the fifth place holding part of the client contract, and the two that
  > drifted were both copies.
  >
  > The unblocking commits are on `191-partition-discrimination`; this issue is
  > the test that would have caught it.
  >
  > ## Third instance, and the one that matters most
  >
  > With the two crashes fixed, the run completes — and reports
  > **`defect_verdict_distribution` = 0 across all three runs.** The defect-verdict
  > axis, which is the axis #189 was built for and the only axis #191 can move,
  > measured nothing.
  >
  > This is not an empty case. `run_once` collects:
  >
  > ```python
  > discriminations = [
  >     item
  >     for observed in client.observed
  >     if isinstance(observed, list)
  >     for item in observed
  >     if isinstance(item, ObligationDiscrimination)
  > ]
  > ```
  >
  > but `judge_discrimination` constructs its `ObligationDiscrimination` objects
  > **after** `client.complete` returns — the client only ever observes the
  > `_Discrimination` schema object. The filter cannot match, for any input. Both
  > halves are in the repo today; this is a code-level certainty, corroborated by
  > the measured zero rather than inferred from it.
  >
  > So the harness has **never** measured defect verdicts, and #189 closed
  > without anyone noticing because no baseline was ever taken.
  >
  > **This blocks #191**, whose Acceptance requires the harness to report lower
  > resample variance than a pre-change baseline. There is no such baseline on the
  > discrimination axis until this is fixed, and #191 must not be judged against
  > a number the instrument cannot produce.
- **Status:** open — **now a blocker for #191, not a side note**

### [2026-08-12] A one-sided requirement is derived as a two-sided one — "does not reduce" became "preserves the number"
- **Kind:** filing (new issue, child of #181)
- **Found during:** #191, Gate 1
- **Where:** `dogfood-logs/191-gate1-run1/output.log`, `constraint-11`
- **Severity:** should-fix
- **What's wrong:** the requirement reads *"The change does not reduce the
  defects the tool identifies."* The derived obligation reads *"The change
  preserves the number of defects the tool identifies."* A one-sided bound became
  a two-sided equality. "Does not reduce" permits finding **more** defects, which
  is the desirable direction; "preserves the number" forbids it. The obligation
  as derived is one a correct implementation fails, and on this task file it
  inverts DR-180's governing constraint — *stability must not be bought by
  blunting the judge*, whose whole point is that the defect count may rise.
- **Why I didn't act:** the source wording is not weak, so this is not the
  sanctioned rewrite. "Does not reduce" is unambiguous; the decomposer dropped a
  quantifier. Rewriting the task file to work around it would hide a real defect,
  which is the one thing the gate forbids.
- **Drafted fix:** file as a child of #181, `bug` / `track:checker`:

  > **Title:** A one-sided requirement is derived as a two-sided one, inverting what it permits
  >
  > From #191's Gate 1 (`dogfood-logs/191-gate1-run1/`):
  >
  > | | text |
  > |---|---|
  > | requirement `constraint-11` | The change does not reduce the defects the tool identifies. |
  > | derived obligation | The change **preserves the number of** defects the tool identifies. |
  >
  > `does not reduce` is a lower bound. `preserves the number` is an equality. The
  > derivation silently added an upper bound the mandate does not state, and the
  > added bound forbids the improvement the requirement exists to protect — on
  > this task file, a defect count that *rises* is the success condition
  > (DR-180: *stability must not be bought by blunting the judge*).
  >
  > Worth separating from #223 and #210, which are about an obligation being
  > attached to the **wrong requirement**. Here the link is correct and the
  > requirement is faithfully identified; the loss is inside the restatement, in
  > a single quantifier. That is a different failure and probably a different
  > fix — #223's is a similarity judgement, this is a paraphrase that does not
  > preserve entailment.
  >
  > Suggested acceptance: an obligation derived from a one-sided requirement
  > (`does not reduce`, `at least`, `no more than`, `never fewer than`) states the
  > same bound in the same direction, and does not close the open side.
  >
  > The remaining 27 obligations in this run are faithful, and the run is
  > otherwise the cleanest in the logs — 1:1, no composites, no open questions —
  > so this is a narrow defect, not a symptom of a bad run.
- **Status:** filed (#262)

### [2026-08-12] Structurally identical scope exclusions get two different obligation types in one run
- **Kind:** filing (comment on existing issue #205)
- **Found during:** #191, Gate 1
- **Where:** `dogfood-logs/191-gate1-run1/output.log`, `exclusion-01`…`exclusion-06`
- **Severity:** nice-to-have
- **What's wrong:** all six scope exclusions in the mandate are the same
  construct, and were typed `regression` twice and `functional` four times in one
  response. The descriptions split on the same line — "The change does not alter
  X" for the two `regression` ones, "The change leaves X out of scope" for the
  four `functional` ones — so the type and the phrasing co-vary, which suggests
  the type is being chosen as a by-product of how the sentence came out rather
  than from the requirement's kind.
- **Why I didn't act:** #205 already owns assigning types in a separate pass, and
  nothing downstream of this gate depends on the exclusions' type.
- **Drafted fix:** comment on #205:

  > A clean instance from #191's Gate 1 (`dogfood-logs/191-gate1-run1/`), useful
  > because the six requirements are structurally identical, in one section, in
  > one response:
  >
  > | requirement | type | description form |
  > |---|---|---|
  > | `exclusion-01` | `regression` | The change does not alter … |
  > | `exclusion-02` | `regression` | The change does not alter … |
  > | `exclusion-03` | `functional` | The change leaves … out of scope |
  > | `exclusion-04` | `functional` | The change leaves … out of scope |
  > | `exclusion-05` | `functional` | The change leaves … out of scope |
  > | `exclusion-06` | `functional` | The change leaves … out of scope |
  >
  > The type tracks the **phrasing** perfectly and the requirement's kind not at
  > all — six scope exclusions, one construct, two types. That is the argument for
  > typing in a pass of its own: as long as the type is emitted alongside the
  > restatement, it is a function of the sentence that came out rather than of the
  > requirement that went in.
- **Status:** filed (#205 comment). A second instance from #261's Gate 1 was
  filed as a separate comment — five identical exclusions, three types, all
  sharing one description form, which rules out the phrasing explanation above.

### [2026-08-12] #245: one test cited for two obligations and withheld from a third, in the same run
- **Kind:** filing (comment on existing issue #245)
- **Found during:** #259, Gate 2, run 3
- **Where:** `dogfood-logs/259-gate2-run3/output.log`, obligations 5, 15 and 24
- **Severity:** blocker — it is the only thing keeping #259's Gate 2 from clean
- **What's wrong:** `test_two_runs_over_the_same_obligation_set_choose_the_same_pairs`
  is cited by obligation 24 (`constraint-15`) and by obligation 5
  (`completion-06`, an unrelated obligation about the demand-type gate), and
  reported as "(no mapped test)" for obligation 15 (`completion-10`) — the
  Completion twin of 24, whose text is nearly the test's own name. One run, one
  test, three different answers. It mapped correctly in runs 1 and 2; the only
  change was two boundary tests added elsewhere in the same file.
- **Why I didn't act:** there is no code change that answers it. Writing a second
  determinism test to satisfy a mapper that already found the first one, and
  cited it twice, is chasing a rating rather than fixing a defect.
- **Drafted fix:** comment on #245:

  > A third instance, from #259's Gate 2 run 3 (`dogfood-logs/259-gate2-run3/`),
  > and the cleanest yet because all three mappings are in **one run** and the
  > test is a single function.
  >
  > `tests/requirement/test_link_prefilter.py::test_two_runs_over_the_same_obligation_set_choose_the_same_pairs`:
  >
  > | obligation | requirement | text | mapping |
  > |---|---|---|---|
  > | 24 | `constraint-15` | Two runs over the same obligation set choose the same pairs. | **cited** (24.4) |
  > | 15 | `completion-10` | A test asserts that two runs over the same obligation set choose the same pairs. | **"(no mapped test)"** |
  > | 5 | `completion-06` | ...a pair excluded for stating a different kind of demand stays excluded... | **cited** (5.5) — spurious |
  >
  > So the twin split is not the whole story: the same test was *also* given to
  > an unrelated obligation about the type gate. The mapper is not simply
  > preferring the Constraint over the Completion — it placed one test in two
  > wrong states at once.
  >
  > It also regressed rather than being stably wrong:
  >
  > ```
  > run 1  obligation 15 -> the test   strongly supported
  > run 2  obligation 15 -> the test   strongly supported
  > run 3  obligation 15 -> (none)     unsupported
  > ```
  >
  > Nothing about that obligation or that test changed between runs 2 and 3; two
  > boundary tests were added elsewhere in the same file. The resulting
  > recommendation prescribes, in detail, a test that already exists and that the
  > same report cites twice — which is the #225-family failure of recommendations
  > making checkable false claims about the code.
- **Status:** filed (#245 comment)

### [2026-08-12] #225 reproduces on a second task file: ratings move under unchanged evidence, both directions
- **Kind:** filing (comment on existing issue #225)
- **Found during:** #259, Gate 2, runs 1–3
- **Where:** `dogfood-logs/259-gate2-run{1,2,3}/`
- **Severity:** blocker for the gate's meaning, not for this delivery
- **What's wrong:** three runs over the same branch, each differing from the last
  only by *added* tests:
  - **run 1 → 2:** obligation 1's mapped evidence was byte-identical — the same
    single test — and it fell `strongly supported` → `partially supported`.
    Non-discriminating obligations went 3 → 13 while the work only added tests.
  - **run 2 → 3:** adding **two** boundary tests moved **twelve** obligations up
    to `strongly supported`, most untouched by those tests, and moved one down to
    `unsupported` by dropping its mapping entirely.

  #248 showed the fall-as-evidence-improves direction. This adds the mirror: a
  rise, at the same magnitude, equally unearned by the two tests that triggered
  it. A judge that moves twelve ratings on two unrelated tests is not measuring
  those obligations' evidence.
- **Why I didn't act:** *Working agreement* §3 — the same failure twice, and a
  third attempt would be a different approach rather than a fix. It is #225's
  own subject matter.
- **Drafted fix:** comment on #225 carrying the run-to-run table above and the
  three committed logs. Worth recording specifically that **the upward direction
  is new evidence**: previous instances all showed ratings falling, which is easy
  to read as a conservative judge. Twelve unearned promotions rules that reading
  out — the movement is not a bias in one direction, it is instability.
- **Status:** filed (#225 comment)

### [2026-08-12] The repo is not formatter-clean, so every edit produces churn
- **Kind:** defect
- **Found during:** #259, Gate 2, run 3 (raised by the tool as `[separable]`)
- **Where:** repo-wide — 49 files fail `ruff format --check`
- **Severity:** should-fix
- **What's wrong:** a `PostToolUse` hook formats files on write, and 49 files in
  the tree are not `ruff format` clean. Touching any of them reflows the whole
  file, so an unrelated edit lands as a large diff. On this branch
  `tests/test_cli.py` showed **457 changed lines for a 5-line edit**, and the
  tool correctly flagged it as `separable`. Five of the files #259 needed were
  dirty at base: `cli.py`, `llm.py`, `test_cli.py`, and both benchmark doubles.
  This is adjacent to #239 (85 pre-existing `ruff check` errors, unpinned ruff)
  but distinct — that is the linter, this is the formatter.
- **Why I didn't act:** repo-wide and unrelated to #259; a formatting commit
  across 49 files is its own change with its own review, and burying it inside a
  prefilter PR is exactly the bundling the tool exists to flag.
- **Drafted fix:** one commit that runs `ruff format .` over the tree and nothing
  else, landed on `main` separately, plus `ruff format --check` added to
  `ci.yml` so it cannot drift again. Sequence it with #239 so the lint and format
  gates arrive together and the transcripts-invalidating churn is paid once.
  **Workaround until then**, used on this branch: restore the file with
  `git checkout <base> -- <path>` and re-apply the real edit by script rather
  than with the Edit tool, so the hook never sees it.
- **Status:** filed (#261)

### [2026-08-11] Composite obligations spanning two requirements are structurally unmergeable
- **Kind:** filing (comment on existing issue #223)
- **Found during:** #259, Gate 1
- **Where:** `dogfood-logs/259-gate1-run1/`
- **Severity:** should-fix
- **What's wrong:** the breakdown carries 35 obligations for 33 requirements.
  Derivation restates much of the mandate under the headline `task-01`; linking
  correctly merged 11 of those restatements away and three survive, each a
  *composite* spanning two requirements. All ten pairs involving them were asked
  and denied with individually defensible reasons — **linking is working as
  designed.** A composite cannot have identical truth conditions with either of
  its parts, so the strict sameness test correctly refuses, and the composite
  then survives permanently as a redundant obligation. The defect is upstream in
  derivation, not in the linking judgement.
- **Why I didn't act:** #223 is a separate issue; #259 is a prefilter on which
  pairs are asked, and would not have changed any of these verdicts.
- **Drafted fix:** comment on #223:

  > A further instance from #259's Gate 1 (`dogfood-logs/259-gate1-run1/`), and
  > one that isolates the mechanism cleanly, because here **linking is not at
  > fault**.
  >
  > Derivation restated much of the mandate under the headline requirement.
  > Linking merged 11 of those restatements away correctly. Three survived, and
  > each is a *composite* spanning two requirements:
  >
  > | obligation | owner | spans |
  > |---|---|---|
  > | `task-01-obligation-2` | `task-01` | task-01 + constraint-02 |
  > | `task-01-obligation-4` | `task-01` | constraint-05 + constraint-06 |
  > | `task-01-obligation-15` | `constraint-17` | constraint-17 + an added "exercises the change" clause |
  >
  > All ten pairs involving them were asked, and all ten were denied with sound
  > reasons — e.g. for `obligation-threshold-default-010 + task-01-obligation-4`:
  > *"The defaulting part is the same requirement, but the second is broader, so
  > they are not exactly the same."* That is correct under the prompt's sameness
  > test.
  >
  > **That is the point.** A composite spanning two requirements can never have
  > identical truth conditions with either part, so linking is structurally
  > incapable of removing it, and no improvement to the linking judgement will.
  > It survives as a redundant obligation that then demands its own evidence
  > downstream. The fix has to be in derivation not emitting the composite.
  >
  > Separately, `task-01-obligation-15` carries a `task-01-` id prefix while
  > owned by `constraint-17` — the id asserts a provenance that is wrong.
- **Status:** filed (#223 comment)

### [2026-08-10] #225 reproduced on #248's Gate 2 — 11 untouched ratings fell when two tests were added
- **Kind:** filing (comment on existing issue #225)
- **Found during:** #248, Gate 2, runs 1 and 2
- **Where:** `dogfood-logs/248-gate2-run1/` and `dogfood-logs/248-gate2-run2/`
- **Severity:** blocker — #248's Gate 2 cannot be made clean while this holds
- **What's wrong:** two tests added, nothing removed; one obligation improved
  and eleven untouched ones fell from strongly to partially supported, taking
  non-discriminating obligations from 3 to 13. Three recommendations make
  checkable, false claims about the code, one of them prescribing a test for the
  negation of a requirement the same report rates satisfied.
- **Why I didn't act:** *Working agreement* §3 — failed the same way twice, and
  a third attempt would be a different approach rather than a fix. Writing more
  tests to move these ratings is chasing a judge that is unstable and in places
  wrong about the file it is reading.
- **Drafted fix:** filed as a comment; see #225.
- **Status:** filed (#225 comment)

### [2026-08-10] Every dogfood run flags `session-state.md` and `docs/DEFERRED.md` as separable
- **Kind:** decision
- **Found during:** #248, Gate 2, runs 1 and 2
- **Where:** the `Unrequested changes` section of every `check` over a branch
  that follows the working agreement
- **Severity:** nice-to-have
- **What's wrong:** the working agreement requires `session-state.md` and
  `docs/DEFERRED.md` to be updated on every branch, and neither is ever demanded
  by the mandate — so `check` correctly reports them as `separable` on every
  run. The finding is right, which is the problem: a caveat that appears
  unconditionally carries no information and trains the reader to skip the
  section that also carries real `separable` findings.
  A second, separate problem shares the cause: the **PR diff** is dominated by
  artifacts nobody reviews. On #257, 14 files changed and only 2 are the
  delivery. `.acceptance/ignore` cannot help there — it governs the review's
  change set, not git.
- **Why I didn't act:** it is a process question about how this repo dogfoods,
  not a defect in the tool, and resolving it quietly is forbidden.
- **Drafted fix — agreed with the human, execute after #257 merges.** Four
  parts; the first three need `git`, the fourth is `CLAUDE.md`:

  1. **`docs/DEFERRED.md` → commit to `main` directly**, pushed immediately. It
     is a queue reviewed at gates, gates are the sync points, and it is rarely
     touched mid-task.
  2. **`session-state.md` → commit to `main` at the gates only**, leaving
     mid-task edits uncommitted in the working tree. Uncommitted changes survive
     `git checkout main`, so the move is checkout / add / commit / push /
     checkout back — no `git stash`, which reverts the working tree wholesale.
     Deliberately NOT main-on-every-update: the file is written mid-task by
     design, and a branch switch per update makes the one practice built to be
     cheap expensive enough to get skipped.
  3. **`current-task.md` → untrack and gitignore** (`git rm --cached`). The
     durable record is the copy inside each `dogfood-logs/<run>/`, paired with
     the output it actually produced, which is the more useful artifact anyway;
     the root file's git history adds nothing that pairing does not already
     carry. Note the gitignore rule must land on `main` — a rule only protects
     branches that carry it.

     **BLOCKED on #258 — this part was not done.** Two tests read the live file:
     `test_task_file.py::test_parses_the_projects_own_current_task_file` reads it
     unconditionally, and `test_region_coverage.py::_committed_task_files` feeds
     it into a parametrize computed at collection time. Untracking the file fails
     CI on a fresh clone. #258 repoints both at the 79 committed
     `dogfood-logs/*/current-task.md` files and is the prerequisite for this
     part; do it first, then untrack.
  4. **Add `session-state.md` and `docs/DEFERRED.md` to `.acceptance/ignore`**
     as a backstop, so the tool's output stays right when one of them reaches a
     branch by accident.

  **This reverses the rejection recorded here earlier**, which held that
  ignoring bookkeeping paths would make the tool aware it is being dogfooded.
  That was wrong: `cli.py:138` already hard-excludes the task file with exactly
  this reasoning — *"the specification, not part of the reviewed deliverable"* —
  and `.acceptance/ignore` is a product feature any client would point at a
  changelog or an ADR directory. Excluding a path does not tell the tool it is
  being dogfooded; it tells the tool the path is not part of the delivery.

  **Consequences to handle in the same change:** `CLAUDE.md`'s startup sequence
  says to read `current-task.md` at session start, which will not exist on a
  fresh clone once it is untracked — the step needs a note. Main-direct commits
  also skip CI; verified that nothing under `src/` or `tests/` reads
  `session-state.md` or `docs/DEFERRED.md`, so the risk is markdown-only, but
  "main is always green" becomes a slightly weaker claim.
- **Status:** parts 1, 2 and 4 done on `main` after #257 merged, with the
  `CLAUDE.md` convention written up. **Part 3 blocked on #258**, now filed.

### [2026-08-10] Disambiguate the `_Yielded` obligation fields — spend at the next decompose re-record
- **Kind:** decision
- **Found during:** #248, Gate 1
- **Where:** `src/acceptance/requirement/obligations.py:302-313` (`_Yielded`), and
  `_SYSTEM_PROMPT` in the same module
- **Severity:** should-fix
- **What's wrong:** `_Yielded` encodes a non-empty obligation list as a required
  `obligation` plus `more_obligations`, because strict mode rejects `minItems`
  and the split is the only way to make "at least one" structural (#217). The
  two fields have no stated relationship and the prompt never mentions them, so
  in the **one-obligation** case the model fills the required slot and then
  emits the same object again as the whole of `more_obligations`. Measured over
  all 1,055 recorded transcripts: 4 duplicate-bearing dispositions, **all four**
  byte-identical head vs `more_obligations[0]` with `len(more_obligations) == 1`,
  and **zero** duplicates in any other position. In the same response,
  requirements yielding 2 and 3 obligations used the split correctly.
- **Why I didn't act:** it changes the schema the model is sent, so it re-records
  the whole decompose corpus and makes benchmark accuracy non-comparable across
  the change. `CLAUDE.md` says pay that cost once — this should ride along with
  the next change that already forces a decompose re-record, not spend it alone.
- **Drafted fix:** two parts, both at the same time:
  1. Rename `obligation` → `first_obligation` and `more_obligations` →
     `remaining_obligations`, so the field names state the relationship.
  2. Add a sentence to `_SYSTEM_PROMPT`: when a requirement yields exactly one
     obligation, `remaining_obligations` is empty — never a copy of the first.

  **This reduces the frequency; it cannot eliminate the case.** Head+rest is the
  only structural encoding of a non-empty list available, so the ambiguity is
  inherent to the shape and the decoder guard landing in #248 stays load-bearing
  regardless. Do not remove the guard when this is done. **Rejected
  alternative:** dropping the split for a plain `obligations` list with a code
  check — that reverses #217, which settled that an empty `yielded` must be
  unrepresentable rather than rejected after the fact.
- **Status:** filed (#256)

### [2026-08-10] #248's Deliverable is mis-specified — correct the issue body
- **Kind:** filing (edit to existing issue #248)
- **Found during:** #248, Gate 1
- **Where:** issue #248, "Deliverable" and "Acceptance"
- **Severity:** blocker — #248's Acceptance as written prescribes the wrong fix
- **What's wrong:** #248 reads the defect as the model emitting one requirement's
  obligation twice, and prescribes dropping "an obligation whose description
  already appears under the same requirement", leaving exact-vs-normalised string
  comparison open. The transcript evidence above shows the duplicate is not a
  content repeat at all: it is a byte-identical echo of the required
  `obligation` field at `more_obligations[0]`, induced by the schema shape. A
  description-comparison drop would blame the model for an answer the schema
  invited, and would also collapse genuine repeats elsewhere in the list, which
  is real signal.
- **Why I didn't act:** backlog content needs human review before it reaches
  GitHub.
- **Drafted fix:** replace #248's Deliverable and Acceptance with:

  > ## Deliverable
  >
  > Read `more_obligations` as *the rest of the list*: when its first entry is
  > byte-identical to the required `obligation` field, the requirement yielded
  > one obligation, not two. Record the reading on `UnusableAnswerLog`,
  > attributed to the response shape rather than to a faulty answer.
  >
  > Scoped to the head of the remainder deliberately. A repeat anywhere else is
  > kept, because that would be the model genuinely restating itself and is the
  > linking stage's call — and because a guard that drops repeats anywhere
  > destroys the signal that something upstream is wrong.
  >
  > The exact-vs-normalised comparison question is withdrawn: fields are
  > compared as whole objects for exact equality, and no description matching is
  > involved.
  >
  > ## Acceptance
  >
  > - A disposition whose `more_obligations[0]` is byte-identical to `obligation`
  >   yields one obligation.
  > - The reading is recorded, not silent.
  > - A `more_obligations[0]` differing from `obligation` in any single field
  >   yields both.
  > - An entry identical to `obligation` appearing later than position 0 is kept.
  > - The surviving obligation carries no `_unique` suffix earned only by the echo.
  > - Two runs over byte-identical task text still produce byte-identical review
  >   state.
  >
  > ## Evidence
  >
  > Scanned all 1,055 recorded transcripts. 4 duplicate-bearing dispositions,
  > all four `obligation == more_obligations[0]` byte-for-byte including `id`,
  > all with `len(more_obligations) == 1`; zero duplicates in any other
  > position. Requirements in the same response yielding 2 and 3 obligations
  > showed no duplication — the failure is specific to the one-obligation case,
  > where the head/rest encoding is ambiguous.
  >
  > The instance originally quoted here (`constraint-10`) is no longer in the
  > cache — its transcript was orphaned — so that specific case is inferred from
  > a matching signature (identical ids forcing the `-2` suffix), not directly
  > re-observed.

  Also worth noting on the issue: this defect was **introduced by the fix for
  #217**, which is worth recording so the tradeoff is visible next time a
  structural-shape fix is chosen.
- **Status:** filed (#248 — body and title replaced)

### [2026-08-10] #223: a spurious link that COMPLETED, destroying the headline requirement's obligation
- **Kind:** filing (comment on existing issue #223)
- **Found during:** #248, Gate 1, run 2
- **Where:** `dogfood-logs/248-gate1-run2/output.log`, first block
- **Severity:** should-fix — worst finding across the three Gate 1 runs
- **What's wrong:** the mandate's headline requirement was given an unrelated
  requirement's obligation and its own was never produced. Nothing in the two
  texts is shared, so no rewrite would have prevented it.
- **Why I didn't act:** #223 is a separate issue; fixing it is out of scope for
  #248, which is a decoder change in `_Yielded`.
- **Drafted fix:** comment on #223:

  > Another instance, from #248's Gate 1 run 2 (`dogfood-logs/248-gate1-run2/`):
  >
  > ```
  > [task-01] A requirement that yields one obligation is not read as yielding two.
  >     -> preserve-decomposition-accuracy-measurement  [compatibility/explicit]   (also serves exclusion-06)
  >        The change does not alter measuring how accurate decomposition is.
  > ```
  >
  > The **headline** requirement of the task file is represented by a
  > preservation invariant about benchmark accuracy measurement — `exclusion-06`'s
  > content, sharing no subject, vocabulary or purpose with it. `task-01`'s own
  > obligation was never produced.
  >
  > Worth noting the direction, because it argues #223, #210 and #242 are one
  > underlying problem seen from three sides. #242 is a spurious link that
  > **blocks** a merge, so nothing merges and everything is reported
  > unreconciled. This is a spurious link that **completed**, and the merge
  > destroyed the surviving content. Same defective similarity judgement, opposite
  > failure, and the blocking case is the safe one — it is loud, whereas this is
  > silent and leaves a plausible-looking breakdown.
  >
  > A milder instance of the same content-bleed survived into run 3
  > (`dogfood-logs/248-gate1-run3/`), where `exclusion-05`'s obligation appends
  > `exclusion-06`'s subject to its own description without losing anything:
  >
  > ```
  > [exclusion-05] Which open questions are raised, and what they cite, which is #206.
  >     -> "...or what they cite, and it does not alter the measurement of decomposition accuracy."
  > ```
  >
  > Not caused by task-file wording: run 3's headline is a near-identical
  > sentence and the severe failure vanished, so it is instability rather than a
  > response to better input.
- **Status:** filed (#223 comment)

### [2026-08-10] #242 gains a second, cleaner instance from #248's Gate 1
- **Kind:** filing (comment on existing issue #242)
- **Found during:** #248, Gate 1
- **Where:** `dogfood-logs/248-gate1-run1/output.log`, final block
- **Severity:** should-fix
- **What's wrong:** #248's Gate 1 decompose ends with an unreconciled cluster of
  four obligations, of which only one pair is a plausible duplicate. The other
  two state plainly different things and are dragged in transitively, so the
  denied pair blocks a merge that should have happened — exactly #242's shape,
  on a task file written for a different purpose.
- **Why I didn't act:** #242 is a separate issue with its own Acceptance; fixing
  linking is out of scope for #248.
- **Drafted fix:** comment on #242:

  > A second instance, from #248's Gate 1 run (`dogfood-logs/248-gate1-run1/`).
  > The cluster is:
  >
  > | obligation | from | states |
  > |---|---|---|
  > | `dedupe-identical-obligations-2` | `task-01` | a requirement does not yield the same obligation twice |
  > | `dedupe-identical-obligations` | `constraint-01` | identical descriptions → keep one |
  > | `exact-description-identity` | `constraint-03` | identity is exact, character for character |
  > | `record-duplicate-drop` | `constraint-04` | the drop is recorded, not silent |
  >
  > Only the first pair is a fair merge candidate — the headline restated as its
  > precise constraint. `exact-description-identity` and `record-duplicate-drop`
  > are not duplicates of anything here; they are the spurious links. One pair
  > inside the cluster was denied, so nothing merged and all four were reported
  > unreconciled.
  >
  > Useful because the cluster is 4 obligations over 24 requirements, small
  > enough to reason about whole, and the task file was not written to provoke
  > it. Committed input and output are in the dogfood log above.
- **Status:** filed (#242 comment)
