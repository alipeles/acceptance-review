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

### [2026-08-20] #293's premise reproduces on a nine-line append, and #292's anchoring does not stop it
- **Kind:** filing (comment on existing issue #293)
- **Found during:** #291, Gate 2 runs 1 and 2
- **Where:** `dogfood-logs/291-gate2-run{1,2}/`
- **Severity:** should-fix — evidence for the next task, not a blocker on this one
- **What's wrong:** the only source change between the two runs was two tests
  appended to `tests/test_carry.py`. Two criteria whose requirement text, mapped
  test set **and** mapped test contents were all byte-identical fell from
  *strongly supported* to *partially supported*:
  `reuse-decision-reaches-answer-through-shared-rule` and
  `reuse-refusal-carries-reason`, each mapped to one unedited test. No rejected
  judgement was reported, because `build_anchors` names dependency changes at file
  granularity, so `mapped-test-file:tests/test_carry.py` was a genuine supplied
  change and naming it licensed the downgrade.
- **Why I didn't act:** it *is* #293, the next task; fixing it is outside #291.
- **Drafted fix:** comment on #293:

  > Reproduced at #291's Gate 2, on a smaller change than #269's.
  > `dogfood-logs/291-gate2-run{1,2}/` are the two runs; the only difference
  > between them is nine lines appended to `tests/test_carry.py`.
  >
  > Two criteria dropped a tier with byte-identical inputs on all three axes this
  > issue names — requirement text, mapped test set, mapped test contents:
  > `reuse-decision-reaches-answer-through-shared-rule` and
  > `reuse-refusal-carries-reason`, each mapped to a single untouched test. That
  > is this issue's third Acceptance item failing on demand.
  >
  > It also prices #292's file-level interim. Nothing was rejected: `build_anchors`
  > supplied `mapped-test-file:tests/test_carry.py` as a real change, so naming it
  > was enough. At content level the anchor for both criteria would name **no**
  > change, and #292's existing rejection would hold the stored rating with no new
  > enforcement code. This issue is what makes #292's guard bite.
- **Status:** filed (#293 comment, approved 2026-08-20).

### [2026-08-20] Twin obligations left unmerged with no diagnostic — not #242's mechanism
- **Kind:** filing (comment on existing issue #242)
- **Found during:** #291, Gate 1 and Gate 2 run 2
- **Where:** `dogfood-logs/291-gate1-run1/`, `dogfood-logs/291-gate2-run2/`
- **Severity:** should-fix
- **What's wrong:** `reuse-rule-four-conditions` (from the Constraint) is
  *partially supported* while its twin `reuse-refusal-on-any-failed-check` (from
  the mirrored Completion expectation) is *strongly supported* — **on the same
  five tests**. At Gate 1 the linker left three of six twin pairs unmerged, two of
  which produced ids differing only by a `-2` suffix
  (`caller-supplies-reuse-context` / `caller-supplies-reuse-context-2`).
- **Why I didn't act:** rewording the mandate to move the linker is the forbidden
  kind of edit.
- **Drafted fix:** **withheld at filing time — the #242 attribution does not hold.**
  #242's mechanism is an inconsistent transitive cluster: a denied pair makes the
  linker merge *none* of the cluster, and it announces itself with an
  `Unreconciled linking answers:` block naming the affected obligations. Grepping
  `dogfood-logs/291-gate1-run1/output.log` for `unreconciled`, `contradict` and
  `denied` returns **nothing**. So these twins were not blocked by a spurious link;
  they were simply never merged, silently. That is a different and arguably worse
  failure — #242 at least reports itself.

  Re-targeted draft, **needs approval before filing**: a new sub-issue of **#181**
  (decomposition quality), labels `bug`, `track:checker`, titled *"Twin
  Constraint/Completion obligations are left unmerged with no diagnostic"*. Body:
  the repo's task-file convention states each rule as a Constraint and mirrors it
  as a Completion expectation, so twins are the norm, not an edge case. In
  `dogfood-logs/291-gate1-run1/` the linker merged three of six pairs and left
  three unmerged, two of which produced ids differing only by a `-2` suffix
  (`caller-supplies-reuse-context` / `caller-supplies-reuse-context-2`,
  `reuse-refusal-carries-reason` / `reuse-refusal-carries-reason-2`) — the
  decomposer naming the same obligation twice and the linker then not merging it.
  Downstream cost measured at Gate 2: `reuse-rule-four-conditions` is *partially
  supported* while its twin `reuse-refusal-on-any-failed-check` is *strongly
  supported* **on the same five tests**. Acceptance: two obligations whose
  generated ids differ only by a numeric suffix are either merged or reported as
  an unmerged pair with a reason; no run leaves a twin pair unmerged silently.
  Cross-reference #242 as the related-but-distinct diagnosed case.
- **Status:** filed as #304, sub-issue of #181 (re-target approved 2026-08-20).
  One correction carried into the filing: the two twins are **not** rated
  differently on an identical evidence set. `reuse-refusal-on-any-failed-check`
  (strongly supported) has all five of `reuse-rule-four-conditions`' tests **plus
  one more**, so it is a superset, not a match. The disagreement stands and the
  filing states it that way.

### [2026-08-20] Scope exclusions get three different dispositions in one run, and one recommendation is unwritable
- **Kind:** filing (new sub-issue of #183)
- **Found during:** #291, Gate 2 runs 1 and 2
- **Where:** `src/acceptance/evidence/strength.py`, `src/acceptance/coverage/recommendation.py`
- **Severity:** should-fix — it puts un-closable items on a gate that must be clean
- **What's wrong:** five Scope-exclusion obligations in one run got three
  treatments. `exclusion-02` and `exclusion-04`: *"test evidence: not required —
  settled by the source change itself"*. `exclusion-01` and `exclusion-03`:
  *unsupported*, with recommended tests. `exclusion-05`: *strongly supported*.
  Nothing distinguishes them. Worse, the recommendation for
  `merits-correctness-not-part-of-reuse-rule` asks for a case where the reuse
  checks pass but the stored result is "bad on merits" — the rule takes no merits
  input, so the requested test cannot be written and the item can never close.
- **Why I didn't act:** an evidence-judgement defect, outside #291.
- **Drafted fix:** sub-issue of **#183**, labels `bug`, `track:checker`. Body: a
  scope exclusion asserts the change does *not* do something, so it has one
  correct disposition, and this run shows the stage picking among three.
  Deliverable: exclusions reach one disposition, and no recommendation is emitted
  for an obligation whose inputs make the requested test unconstructable.
  Acceptance: the five exclusions in `dogfood-logs/291-gate2-run2/` reach the same
  disposition; no recommendation asks for an input the code cannot accept.
- **Status:** filed as #301, sub-issue of #183 (approved 2026-08-20).

### [2026-08-20] Second instance of #182 mapping churn: five mapped tests fell to one, none edited
- **Kind:** filing (comment on existing issue #182 — a second instance under the
  entry already filed above)
- **Found during:** #291, Gate 2 runs 1 and 2
- **Where:** `dogfood-logs/291-gate2-run{1,2}/`
- **Severity:** should-fix
- **What's wrong:** `reuse-refusal-carries-reason-2` mapped five tests in run 1 and
  one in run 2. None of the four dropped tests was edited, renamed or removed, and
  the rating fell with the mapping. Different criterion and different diff from the
  instance already filed on #182, so it is corroboration rather than a repeat.
- **Why I didn't act:** #182 owns it; nothing in #291's scope fixes it.
- **Drafted fix:** add to the existing #182 thread with both run directories and
  the before/after mapped sets, noting it bounds #293 directly — #293 re-judges a
  criterion whose mapped set gained or lost a member, so churn of this size spends
  exactly the calls #293 exists to save.
- **Status:** filed (#182 comment, approved 2026-08-20).

### [2026-08-20] #265's own scope is wrong: three of its four target stages cannot be helped by prompt shape at all
- **Kind:** filing (comment on existing issue #265)
- **Found during:** #265, after Gate 2 run 2
- **Where:** `docs/experiments/265-cache-key-scope/`
- **Severity:** should-fix — the issue currently directs the next session at work
  that is now known to be impossible
- **What's wrong:** #265's 2026-08-20 comment says test recommendation,
  unrequested-change detection and coverage classification need invariant content
  hoisted above the variable part until their shared prefix clears the
  1,024-token floor. Two measurements retire that.

  1. **Those three stages issue exactly ONE call per review run**
     (`pipeline.py:351-359`), so they have no sibling to share a prefix with.
     Their measured 278/403/680-token "shared prefixes" are cross-*run* figures —
     the system prompt, which is all two different runs share.
  2. **Cross-stage sharing is impossible by construction.** The response schema
     is in the provider's cache key, and its *name* alone is enough to break
     reuse. Every stage sends a different response model.

  Together: no reordering can ever make those three cache. The remaining route is
  making them issue more than one call that shares an opening — batch
  composition, which is a different piece of work.
- **Why I didn't act:** rewriting the issue body is a backlog edit, and the
  measurement should be attached to it first.
- **Drafted fix:** comment on #265, then amend the issue's scope section:

  > ## Two of this issue's premises do not survive measurement
  >
  > **Three of the four target stages issue one call per run.** `classify_coverage`,
  > `detect_unrequested_changes` and `recommend_tests` are each called once from
  > `pipeline.py:351-359`. They have no sibling call, so there is no within-run
  > prefix to lengthen, and the 278/403/680-token figures above are cross-*run*
  > floors — the system prompt, which is all two different runs share.
  >
  > **Cross-stage sharing is impossible.** Measured in
  > `docs/experiments/265-cache-key-scope/`, six live calls against
  > `openai/gpt-5.4-mini`:
  >
  > | case | schema | cached |
  > |---|---|---|
  > | identical repeat | `_Coverage` | **94.9%** |
  > | identical opening, different tail | `_Coverage` | **95.0%** |
  > | identical messages, different schema | `_Detections` | 0.0% |
  > | identical messages, same schema fields, different schema NAME | `_Renamed` | 0.0% |
  > | different opening | `_Coverage` | 0.0% |
  >
  > Both controls behave. The fourth row is the finding: byte-identical messages
  > and byte-identical schema *fields*, differing only in the schema's name, reuse
  > nothing. The response schema is in the cache key, and every stage sends a
  > different one.
  >
  > Confirmed independently at this issue's own Gate 2: coverage classification
  > and unrequested-change detection now open with a byte-identical ~70k-token
  > diff block seconds apart, and both reported 0.0% cached.
  >
  > ## What the ordering lever is actually worth
  >
  > The 95.0% row is the sibling-call case — identical opening, different tail,
  > same schema — which is what a partitioned stage issues. That is where #191's
  > 84–93% came from, and it is what the ordering change buys for mapping,
  > discrimination, decompose and obligation linking.
  >
  > So the lever works and was aimed at the wrong stages. The scope section should
  > drop "hoist invariant content in the three big stages" and replace it with
  > batch composition, which is the only remaining route for a stage that issues
  > one call.
  >
  > ## Still unexplained
  >
  > Mapping is partitioned into 18 calls with a shared opening and measured
  > **4.5%** at Gate 2, where this experiment says a sibling call should reach
  > ~95%. Neither ordering nor the schema explains that, and it is now the open
  > question this issue should carry — it is the same residue the original
  > comment flagged as "3 of 464".
- **Status:** open

### [2026-08-20] #245 with the correct answer in the corpus: the mapper returned the twin id on one call and not on the one that counted
- **Kind:** filing (comment on existing issue #245)
- **Found during:** #265, Gate 2, run 2
- **Where:** `dogfood-logs/265-gate2-run2/`, obligations 3/16 and 4/15
- **Severity:** blocker — it is the only thing keeping #265's Gate 2 from clean
- **What's wrong:** two Completion expectations came back `unsupported`,
  `(no mapped test)`, while their Constraint twins came back `strongly
  supported` **citing the exact test the Completion twin is told is missing**.
  Same report, same run.

  What makes this instance worth adding: the mapper produced the right answer.
  Transcript `714a89b33d` returns *both* ids for the test, with a rationale
  naming the twin relationship. A second transcript, `39e47c338f`, for the same
  test in its own batch, returns only the Constraint id — and the run consumed
  that one. Two calls, same test, same partition size, five minutes apart,
  different answers.
- **Why I didn't act:** #245 owns it. The tests the recommendations ask for
  already exist and are already cited elsewhere in the same report, so writing
  duplicates would be chasing a rating rather than fixing a defect — the
  disposition #259's Gate 2 recorded for this same shape.
- **Drafted fix:** comment on #245:

  > A fourth instance, from #265's Gate 2 run 2 (`dogfood-logs/265-gate2-run2/`),
  > and the first where **the correct mapping is in the corpus**.
  >
  > | # | obligation | rating | test |
  > |---|---|---|---|
  > | 4 | `shared-content-ordered-by-breadth` (constraint-02) | strongly supported | cites `test_no_request_places_content_unique_to_it_ahead_of_content_it_shares` |
  > | 15 | `test-request-unique-content-after-shared-content` (completion-02) | **unsupported** | "(no mapped test)" |
  > | 3 | `shared-content-byte-identical-across-requests` (constraint-01) | strongly supported | cites `test_content_two_requests_share_is_written_the_same_way_in_both` |
  > | 16 | `test-shared-content-byte-identical-across-requests` (completion-03) | **unsupported** | "(no mapped test)" |
  >
  > The mapper is not blind to the relationship. Mapping transcript
  > `714a89b33d` returns both ids for the test:
  >
  > ```
  > ids : ['shared-content-ordered-by-breadth',
  >        'test-request-unique-content-after-shared-content']
  > why : Fails when content shared by multiple requests appears after
  >       request-unique content, which is exactly the breadth-based ordering
  >       rule and its corresponding failure case.
  > ```
  >
  > That rationale is correct, and it names the twin relationship explicitly.
  > But a second transcript, `39e47c338f`, judging the **same test in its own
  > batch**, returned only `['shared-content-ordered-by-breadth']` — same
  > partition size (12), five minutes apart — and that is the answer the run
  > consumed.
  >
  > So the twin split here is not a limit of what the stage can perceive. It is
  > **instability across calls**, with the good answer and the bad answer both on
  > disk. That argues the fix is not a better prompt for recognising twins but
  > either resolving the pair structurally (a Constraint and its Completion twin
  > share mapped evidence by construction) or re-asking and reconciling, since a
  > second call demonstrably produces the missing id.
  >
  > Confirmed the loss is at mapping and not downstream: `apply_test_mapping`
  > (`mapping.py:241-254`) iterates every returned `obligation_id`, and
  > `extraction.py:60` carries the whole list. The persisted review has
  > `"test_evidence": []` on the Completion twin, matching the consumed mapping
  > exactly.
  >
  > Both tests were falsified before being trusted — injecting the pre-change
  > request shape makes the first fail, and reversing the assembler's sort makes
  > the second fail — so this is not a case of a weak test being correctly
  > declined.
- **Status:** filed (#245 comment)

### [2026-08-20] Decision: does a provider's cache key cover the response schema, and does that make cross-stage prefix reuse impossible?
- **Kind:** decision
- **Found during:** #265, Gate 2, run 2
- **Where:** `dogfood-logs/265-gate2-run2/judgement.md`, the per-stage cached
  share
- **Severity:** should-fix — it decides whether #265's remaining work is worth
  doing at all
- **What's wrong:** #265's change makes coverage classification and
  unrequested-change detection open with a **byte-identical ~70k-token diff
  block**, issued seconds apart in one run. The second reused **none** of it:

  ```
  coverage classification        1 call   79,073 prompt   0.0% cached
  unrequested-change detection   1 call   78,585 prompt   0.0% cached
  test-to-obligation mapping    18 calls  85,609 prompt   4.5% cached
  ```

  So the cross-stage prefix — the lever this whole change was built for — did
  not pay. The ordering is right and the bytes are identical; something else is
  preventing reuse.
- **Hypothesis, stated as one:** each stage sends a different `response_format`
  schema (`_Coverage` vs `_Detections`). If the provider's cache key covers the
  schema as well as the messages, no two stages can ever share a prefix however
  their messages are ordered. This would also explain mapping's 3-of-464 in the
  baseline, which #265's own comment recorded as explained by neither ordering
  nor prefix length.
- **Why I didn't act:** `exclusion-04` of this mandate puts provider reuse
  behaviour out of scope, deliberately, so it is not a Gate 2 criterion. And
  settling it is an experiment, not a code change.
- **Drafted fix — recommendation: run the experiment before any further
  ordering work.** Issue the same messages twice under one schema, and again
  under two different schemas, and read `cached_tokens`. It is a handful of live
  calls and it decides the direction of the rest of #265.

  **If the hypothesis holds:** this change stays (it is correct and cheap, and
  it is what makes sibling calls in a partitioned stage share an opening), but
  #265's remaining lever is **batch composition**, not ordering — and the three
  single-call stages cannot be helped by prompt shape at all, which contradicts
  the reading in #265's comment.

  **Rejected alternative:** carrying on with ordering work on the other stages
  and measuring at the end. That is optimisation by anecdote, which is the thing
  #265 says it exists to avoid.
- **Status:** resolved (human approved running it, 2026-08-20). **The hypothesis
  holds.** `docs/experiments/265-cache-key-scope/` — six live calls, both
  controls behaving: an identical repeat reused 94.9%, a different opening reused
  0%, and messages identical but for the schema **name** reused 0%. So the schema
  is in the cache key and cross-stage sharing is impossible by construction.
  The same run measured `same_schema_new_tail` — identical opening, different
  tail, same schema — at **95.0%**, which is the sibling-call case the ordering
  change creates. Lever works; it was aimed at the wrong stages. Follow-up
  filings queued below.

### [2026-08-20] A local venv behind the ruff pin makes `ruff check .` pass on a tree CI rejects
- **Kind:** defect (working procedure)
- **Found during:** #265, implementation — reported by the #292 session, which
  found main red and could not go green
- **Where:** `CLAUDE.md` *Commands*; the pin is `pyproject.toml:19`
- **Severity:** should-fix — it kept `main` red for four consecutive commits and
  blocked another session's PR
- **What's wrong:** `pyproject.toml` pins `ruff==0.16.2` for CI. This venv had
  **0.15.22**, and `BLE` is not in the older version's default rule set, so
  `.venv/bin/ruff check .` printed *"All checks passed!"* on a tree where CI
  reported `BLE001` and exited 1. Lint is a build step, so the whole `test` job
  died in ~25s before a single test ran.

  Three findings appeared the moment the pinned version was installed, not one:
  the reported `BLE001` in `docs/experiments/265-prompt-cache-baseline/`, an
  `I001` import-sort in `coverage/open_questions.py`, and a **second** `BLE001`
  at `llm.py:227` in code written on this branch minutes earlier. So the drift
  was actively hiding a fresh break as well as an old one.
- **Why I didn't act further:** the two code fixes are done — the baseline-script
  line is on `main` as `c63bf86`, the other two are on
  `265-share-request-openings`. What is left is documentation, and `CLAUDE.md` is
  the human's file.
- **Drafted fix — recommendation: one line in `CLAUDE.md` under *Commands*,**
  beside the existing `ruff check .` entry:

  > `.venv/bin/ruff check .` only matches CI when the venv matches the pin in
  > `pyproject.toml` (`ruff==0.16.2`). An older ruff has a smaller default rule
  > set and passes trees CI rejects — this kept `main` red for four commits.
  > Check with `.venv/bin/ruff --version`; `pip install -e ".[dev]"` needs the
  > sandbox off, because it hits the same TLS wall as `gh`.

  **Rejected alternative:** making CI install whatever ruff is current. The
  workflow comment already explains why the pin exists — a floating version made
  CI enforce whatever ruff had most recently released, and #239 is the scar. The
  pin is right; the local venv is what drifted.
- **Status:** fixed (human decision, 2026-08-20). Landed in `CLAUDE.md` under
  *Commands*, beside the `ruff check .` line.

### [2026-08-20] Mapping dropped four intact tests from an unchanged obligation
- **Kind:** filing (comment on existing issue #182)
- **Found during:** #292, Gate 2, runs 1 and 2
- **Where:** `src/acceptance/evidence/mapping.py`; evidence in
  `dogfood-logs/292-gate2-run1/` and `-run2/`
- **Severity:** should-fix — it bounds what #292 (PR #299) can guarantee
- **What's wrong:** same task file, `--continue` on both runs, obligation blocks
  byte-identical across 29 lines. Only `tests/` changed between them, in two
  files. The obligation `changed-test-evidence-rating-justify-itself` went from
  four mapped tests to none, and **none of those four was modified, renamed or
  removed** — all four live in files that do not appear in the diff. The verdict
  for that obligation flipped `strongly supported` → `unsupported`, and a
  recommended test appeared prescribing evidence that already existed.
- **Why I didn't act:** #182 is the umbrella that owns mapping instability, and
  no change in #292's scope would fix it.
- **Drafted fix:** comment on #182 — filed, see Status.
- **Status:** filed (#182 comment, approved 2026-08-20). It bounds #292: the
  anchored rejection stops a rating moving without a changed input, but the
  rating is computed from the mapping, so a criterion whose mapped set churns is
  re-judged against genuinely different evidence and the new rating passes the
  check without a violation. The guarantee is incomplete until mapping is stable
  under an additive change.

### [2026-08-20] A repeated disposition with mechanically-renamed ids aborts the whole review
- **Kind:** filing (new sub-issue of #181)
- **Found during:** #265, Gate 1, run 1
- **Where:** `src/acceptance/requirement/obligations.py:1203-1216`
  (`_filter_dispositions`) and `:1265-1269` (`_requirement_map`)
- **Severity:** should-fix — it is not a bad finding, it is *no* finding: the run
  produces nothing at all, and once recorded it is permanently fatal for that
  input
- **What's wrong:** the decompose call returned `task-01` twice. Both copies are
  `yielded`, both carry the same seven obligations in the same order with the
  same descriptions and the same `source_quote`s. They differ in exactly one
  way: **every id in the second copy has `-dup` appended**, and the suffix is in
  the model's own response, not added by our `_unique` helper.

  `_filter_dispositions` already handles this case and says so in its comment —
  *"a response that repeats itself verbatim is a degenerate generation rather
  than a contradiction — observed once the obligations moved inside the
  dispositions and responses grew: the model emitted its whole disposition list
  twice."* But it tests `previous == entry`, whole-object equality, so the
  perturbed ids slip past. `_requirement_map` then raises
  `SchemaValidationError: requirement 'task-01' was disposed more than once`,
  the CLI reports a model error, and the run ends. No obligations, no report, no
  verdict — for all eighteen requirements, not just `task-01`.

  The disposition being applied is #217's rule for a **self-contradiction**, two
  *different* answers for one requirement. Two answers identical apart from a
  mechanical suffix on every id are one answer, repeated.
- **It is intermittent, and that makes it worse rather than better.** Run 2 was
  the same task file, same model, same seed, with only the orphaned transcript
  deleted so the identical request went out live — and it came back clean. So the
  tool cannot stop the model repeating itself; what it controls is the response,
  and today the response is to abandon the review. And because the bad answer is
  recorded under the request key, every later run replays it and fails the same
  way. Deleting the transcript is the only remedy and nothing says so.
- **Why I didn't act:** it is in `requirement/`, outside #265's area (which is
  request assembly and the client), and the fix needs a call on how far the
  collapse should reach — see the draft.
- **Drafted fix:** file as a sub-issue of #181, `bug` / `track:checker`:

  > **Title:** A repeated disposition with mechanically-renamed ids aborts the entire review
  >
  > Child of #181. Labels: `bug`, `track:checker`.
  >
  > ## What happens
  >
  > From #265's Gate 1 run 1 (`dogfood-logs/265-gate1-run1/`):
  >
  > ```
  > acceptance: model error: requirement 'task-01' was disposed more than once
  > ```
  >
  > The third decompose batch was asked about two requirements and returned
  > three dispositions — `exclusion-06`, `task-01`, `task-01`. The two `task-01`
  > entries are the same disposition twice: same `yielded`, same seven
  > obligations in the same order, same descriptions, same `source_quote`s. The
  > only difference is that every id in the second copy ends in `-dup`:
  >
  > | copy | head obligation | in `more_obligations` |
  > |---|---|---|
  > | 1 | `share-opening-text-across-run-requests` | six ids |
  > | 2 | `share-opening-text-across-run-requests-dup` | the same six, each `+-dup` |
  >
  > The suffix is the model's, visible in the recorded response body. It is not
  > `_unique`'s `-2`.
  >
  > ## Why the existing guard misses it
  >
  > `_filter_dispositions` (`obligations.py:1203-1216`) exists for exactly this
  > failure mode. Its comment names it:
  >
  > > An EXACT repeat of a disposition already returned in this response is
  > > dropped, not rejected. … a response that repeats itself verbatim is a
  > > degenerate generation rather than a contradiction — observed once the
  > > obligations moved inside the dispositions and responses grew: the model
  > > emitted its whole disposition list twice.
  >
  > The test is `previous == entry` — equality of the whole disposition object.
  > Renaming the ids defeats it, so the copy is passed through as a *differing*
  > duplicate and `_requirement_map` (`:1265-1269`) raises.
  >
  > That raise implements #217's rule against a **self-contradiction**: "two
  > different answers for one requirement". These are not two different answers.
  > The obligations say the same thing in the same words; only their labels
  > moved, and the labels are ours to assign anyway — `_unique` already rewrites
  > colliding ids.
  >
  > ## Consequence
  >
  > The whole review is abandoned, not the duplicate. Eighteen requirements were
  > decomposed and none survive. And the response is **recorded**, so the failure
  > is permanent for that input: every rerun replays the stored answer and dies
  > identically. Clearing it means finding and deleting the transcript by hand,
  > which nothing in the output suggests.
  >
  > This collides with the standing invariant that uncertainty is first-class.
  > A degenerate repeat is at worst an indeterminate result about one
  > requirement; it is not grounds for producing nothing.
  >
  > ## It is intermittent
  >
  > Run 2 (`dogfood-logs/265-gate1-run2/`) issued the byte-identical request
  > live after the transcript was deleted, and returned a clean, complete answer
  > — 18 requirements, 17 with obligations, no open questions. Same model, same
  > seed, same input. So this is not a property of the task file, and no
  > rewording avoids it.
  >
  > ## Suggested direction
  >
  > Compare dispositions for equality **ignoring ids** — the ids carry no
  > meaning the pipeline does not assign itself, and `_unique` already renames
  > collisions. A second copy whose obligations match the first field for field
  > apart from their ids is a repeat, and should be dropped and recorded on
  > `UnusableAnswerLog` as a degenerate generation, exactly as the verbatim case
  > already is.
  >
  > Deliberately narrower than "drop any duplicate": a copy that differs in a
  > `description`, `type` or `source_quote` is still a real contradiction and
  > must still raise. This is the same shape of fix as #248, one level up — #248
  > collapses a repeated **obligation** inside one disposition, this collapses a
  > repeated **disposition** inside one response.
  >
  > Worth deciding alongside it: whether a `SchemaValidationError` from one
  > batch should end the run at all, or be recorded against that batch's
  > requirements while the rest of the review proceeds. That is the same
  > argument #275 makes about one omitted recommendation aborting thirteen.
  >
  > ## Acceptance
  >
  > - A response that returns one requirement's disposition twice, identical
  >   except for ids, yields that requirement's obligations once and completes.
  > - The collapse is recorded on `UnusableAnswerLog`, not silent.
  > - A second disposition differing in any field other than an id still raises.
  > - A test drives `decompose` through the path, not only the helper.
  >
  > Evidence: `dogfood-logs/265-gate1-run1/` (`judgement.md`), and
  > `dogfood-logs/265-gate1-run2/` for the clean re-issue of the same request.
- **Status:** filed (#298, sub-issue of #181). A `Related:` line was added at
  filing time, beyond the approved draft.

### [2026-08-20] An imperative Task headline yields an obligation that states an instruction, not a property
- **Kind:** filing (comment on existing issue #297)
- **Found during:** #265, Gate 1, runs 2 and 3
- **Where:** `dogfood-logs/265-gate1-run3/output.log`, requirement `task-01`
- **Severity:** nice-to-have — #297 already owns the defect; this adds a variant
  it does not cover
- **What's wrong:** #297 is about an imperative headline losing its verb and
  producing an ungrammatical obligation. This run shows the other outcome: the
  imperative is carried through **intact and grammatical**, so the obligation
  reads *"Make the model requests of a single review run open alike wherever they
  carry the same content, so …"* — a well-formed instruction rather than a
  property that could be true or false of the code. The grammar is not the
  defect; carrying the mood is.
- **Why I didn't act:** #297 owns it, and rewriting the mandate a third time to
  dodge it would be tuning the input. The headline is ordinary house style.
- **Drafted fix:** comment on #297:

  > A variant from #265's Gate 1 (`dogfood-logs/265-gate1-run3/`), worth adding
  > because it shows the grammar is not what is wrong.
  >
  > Headline: *"Make the model requests of a single review run open alike
  > wherever they carry the same content, so a provider that can reuse a
  > repeated opening has as long an opening to reuse as the run allows."*
  >
  > Derived obligation: *"Make the model requests of a single review run open
  > alike wherever they carry the same content, so shared content is written the
  > same way in each request and appears as long a reusable opening as the run
  > allows."*
  >
  > Here the verb survives and the sentence is well formed — the failure in this
  > issue's original instance does not occur. What survives with it is the
  > **imperative mood**, so the obligation states a thing to do rather than a
  > property that is true or false of a diff. Every downstream stage asks
  > "is this satisfied?", which is not a question an instruction answers.
  >
  > That suggests the fix is not repairing the verb but converting the mood:
  > an obligation derived from an imperative should be restated in the
  > indicative, as the Constraints in the same file already are.
  >
  > A second instance for this issue's other Acceptance bullet, from run 2 of the
  > same gate: before the headline was reworded, `task-01` yielded a single
  > obligation conjoining `constraint-01` and `constraint-02`. Because it
  > restates *two* constraints, it matches neither on its own and the linker
  > merged it with neither — so a composite restatement is strictly harder to
  > reconcile than the single-constraint restatement that bullet describes.
- **Status:** filed (#297 comment)

### [2026-08-20] A dogfood `output.log` can come back empty with exit 0
- **Kind:** defect (working procedure, not the tool)
- **Found during:** #265, Gate 1, runs 2 and 3
- **Where:** `CLAUDE.md`, *Dogfooding — the review gates*
- **Severity:** nice-to-have
- **What's wrong:** twice in one gate, `acceptance decompose … > output.log`
  exited 0 and left a **zero-byte** file; re-running the identical command after
  `rm -f` produced the full 6.9 KB both times. Both empty files had mode `0600`
  where a shell redirect normally gives `0644`. A silently empty log destroys the
  dogfood run's only durable record while reporting success — and the gate
  procedure requires that file.
- **I could not reproduce it, and the obvious explanation is wrong.** The
  hypothesis was that it happens when the run issues live calls. Tested with a
  probe task file edited to force a live decompose call and redirected to a
  file: 6,551 bytes, no failure. So there is no mechanism here and **nothing is
  filed against the tool** — this looks like a shell or sandbox artifact.
- **Why I didn't act:** unreproducible, and out of #265's area regardless.
- **Drafted fix — recommendation: one line in `CLAUDE.md`,** under the
  `dogfood-logs/` layout: *"Check `output.log` is non-empty after writing it. A
  redirect has twice produced a zero-byte log on a successful run."*
  **Rejected alternative:** chasing the cause. Two occurrences, no reproduction,
  and the check costs one `wc -c`.
- **Status:** fixed (human decision, 2026-08-20 — "just fix the CLAUDE.md issue").
  The line landed under the `dogfood-logs/` layout in *Dogfooding — the review
  gates*, stating plainly that the cause is unknown and that the live-calls
  hypothesis was tested and disproved.

### [2026-08-20] Should a rating be allowed to FALL without naming a change?
- **Kind:** decision
- **Found during:** #292, Gate 2, run 1
- **Where:** `src/acceptance/evidence/discrimination.py::judge_discrimination`,
  the anchored rejection
- **Severity:** blocker — it decides what #292 actually delivers, and #292's
  Acceptance item about `tests/fixtures/rating-stability/` is what surfaced it
- **What's wrong:** the rejection as implemented is **symmetric**: a rating that
  moves without resting on a supplied change is held whichever way it moved.
  `DR-180` says the two directions are not symmetric — in 7 of its 8 unstable
  obligations the LOW rating was the correct one, and `strongly supported`
  issued when unearned is the dangerous failure. So this shape is reachable: a
  criterion is anchored because its test file changed; the judge correctly
  downgrades it because it has finally noticed a pre-existing hole unrelated to
  that change; it names nothing, because none of the changes is the reason; the
  unearned `strongly_supported` is held. That is `DR-180`'s defect re-created by
  the fix for a different one.
- **Why I didn't act:** it changes what #292 delivers and the evidence points
  both ways. Deciding it quietly is exactly what *Surface open decisions* forbids.
- **Recommendation:** enforce **asymmetrically** — require a justification to
  RAISE a rating, and let a fall through unjustified. The counter-argument is
  #269's 37→4 collapse, which was a mass fall and was wrong; the answer to it is
  that the collapse was caused by re-judging criteria that should never have been
  re-judged, which is **#293's** deliverable. Using #292's rule to suppress
  downgrades makes one issue pay for another's gap, in the direction `DR-180`
  names as dangerous.
- **Alternative rejected:** keep it symmetric and rely on the prompt plus the
  schema enum to make omission rare. Rejected because "rare" is not a property
  this project accepts in place of enforcement, and the failure is silent —
  a held STRONG looks exactly like an earned one.
- **Status:** resolved 2026-08-20 — **human decision: keep it symmetric.** My
  recommendation was rejected. The rule is: *every change to a prior judgement,
  anywhere in the pipeline, must be tied to a changed input.* No exception for
  the direction of travel. The `DR-180` problem I was pointing at is real but is
  a **separate** problem — making the FIRST judgement right — and is not to be
  solved by tolerating unexplained movement in later ones. Recorded in
  `DR-292`; the pipeline-wide half belongs to #286.

### [2026-08-20] A review run reaches into `benchmark/` for a model call that names no stage
- **Kind:** filing (new sub-issue of #184)
- **Found during:** #292, Gate 1, run 1
- **Where:** `src/acceptance/requirement/carry.py:166-171` calls
  `src/acceptance/benchmark/alignment.py:77`
- **Severity:** should-fix — a green guard over a violated constraint, and a
  layering violation `CLAUDE.md` states as a structural fact
- **What's wrong:** two things, one fix.

  1. `align_obligations()` at `benchmark/alignment.py:77` calls
     `client.complete(messages, _Alignment)` with no `stage=`, so
     `ModelClient._observe_call` (`llm.py:405`) labels it
     `UNKNOWN_STAGE`. #285's constraint is that no model call the review
     pipeline issues reports its stage as unknown. `decompose` printed an
     `unknown` row: 1 call, 881 prompt / 48 output tokens.
  2. **`plan_carry` calls benchmark code from the review path.**
     `requirement/carry.py:166` does a function-local
     `from acceptance.benchmark.alignment import align_obligations` and calls it
     at `:171`. `align_obligations`' own docstring (`alignment.py:17-18`) says it
     "runs against known ground truth, not in the product's own review path",
     and `CLAUDE.md` states `benchmark/` "is not part of a review run". Both are
     false as written.
- **Why the guard is green:** `tests/test_stage_attribution.py` passes 8/8. Its
  AST scan (`:88`) filters `_EXCLUDED = ("benchmark",)` **by path**, so the
  offending site is excluded — and `carry.py`'s in-function import hides the
  reachability from a per-module scan regardless. Its wiring test (`:179`) does
  run a real `run_review`, but with no ledger prior, so `plan_carry` returns at
  `carry.py:115-119` before reaching the guard at `:165` and the call never
  happens. **The only path that reaches the defect is the one path the wiring
  test does not take.**
- **Why it now fires on nearly every run:** the guard at `carry.py:165` needs a
  prior ledger entry plus residue on both sides. #251's triage changed `CLAUDE.md`
  to require `--continue` on every Gate 1 and Gate 2 re-run, which supplies that
  prior — so a condition that used to be rare is now the default.
- **Why I didn't act:** out of scope for #292, and it touches
  `requirement/carry.py::plan_carry`, which **#291 already rewrites** on its
  unpushed branch. Fixing it here would collide.
- **Drafted fix:** file as a sub-issue of #184.

  > **Title:** A review run reaches into `benchmark/` for a model call that names no stage
  >
  > Child of #184. Labels: `bug`, `track:checker`.
  >
  > ## What happens
  >
  > A `decompose` run continued with `--continue` prints an `unknown` row in its
  > per-stage usage breakdown:
  >
  > ```
  > decompose           1 (1 live / 0 replayed)   6,481     734
  > obligation linking  2 (2 live / 0 replayed)   1,791     127
  > unknown             1 (1 live / 0 replayed)     881      48
  > ```
  >
  > The call is `align_obligations()` at `benchmark/alignment.py:77`, which
  > passes no `stage=`, so `ModelClient._observe_call` (`llm.py:405`) labels it
  > `UNKNOWN_STAGE`. This violates #285's constraint that no model call the
  > review pipeline issues reports its stage as unknown.
  >
  > ## The larger half
  >
  > It is reached from **product** code. `requirement/carry.py:166` imports
  > `acceptance.benchmark.alignment` inside `plan_carry()` and calls it at `:171`,
  > guarded at `:165` by a prior ledger entry plus unmatched residue on both
  > sides. So the review path depends on the measurement harness.
  >
  > `align_obligations`' docstring says the opposite (`alignment.py:17-18`):
  > *"This is benchmark measurement infrastructure — it runs against known ground
  > truth, not in the product's own review path."* `CLAUDE.md` says
  > *"`benchmark/` is the measurement harness; it is not part of a review run."*
  > Both are now false.
  >
  > ## Why no test caught it
  >
  > `tests/test_stage_attribution.py` passes 8/8.
  >
  > - Its AST scan (`:88`) excludes `benchmark/` **by path**, so the site is
  >   outside what it polices. The scan has no notion of "reachable from the
  >   review pipeline", and the in-function import would defeat a per-module
  >   scan anyway.
  > - Its wiring test (`:179`) runs a real `run_review`, but passes no ledger
  >   prior, so `plan_carry` returns early at `carry.py:115-119` and never
  >   reaches the call.
  >
  > The one path that reaches the defect is the one path the wiring test does
  > not take — and since `CLAUDE.md` now requires `--continue` on every gate
  > re-run, that path is the common case.
  >
  > ## Acceptance
  >
  > - The requirement-alignment call names the stage that issued it, and no
  >   `decompose` or `check` run reports a stage of `unknown`.
  > - A test drives a run **with a ledger prior and residue on both sides** —
  >   the path that reaches `align_obligations` — and fails on an unattributed
  >   call.
  > - No module under `benchmark/` is imported from the review path, or the
  >   statements to the contrary in `alignment.py`'s docstring and `CLAUDE.md`
  >   are corrected to match a deliberate decision.
  >
  > ## Sequencing
  >
  > Touches `requirement/carry.py::plan_carry`, which #291 rewrites on an
  > unpushed branch. Sequence after #291 lands, or fold into it.
  >
  > Evidence: `dogfood-logs/292-gate1-run1/`, `judgement.md` Finding 3.
- **Status:** filed (#296, sub-issue of #184)

### [2026-08-20] The Task headline yields a duplicate obligation with the verb left unconjugated
- **Kind:** filing (new sub-issue of #181)
- **Found during:** #292, Gate 1, run 1
- **Where:** `src/acceptance/requirement/obligations.py` (decomposition); evidence
  in `dogfood-logs/292-gate1-run1/output.log`, requirement `task-01`
- **Severity:** should-fix — it manufactures a spurious obligation that mapping
  and evidence judgement then spend a Gate 2 on
- **What's wrong:** the headline *"Make a changed test-evidence rating justify
  itself."* produced two obligations. One is a fair restatement; the other,
  `changed-test-evidence-rating-justify-itself`, is *"A changed test-evidence
  rating justify itself."* — the imperative "Make" stripped without the verb
  being repaired, and typed `test_demand` rather than `functional`. It also
  duplicates `constraint-04`, which states the same rule grammatically.
- **Why I didn't act:** out of scope for #292, and rewording `current-task.md` to
  dodge it would be tuning the input around a tool defect rather than fixing weak
  wording. The headline is ordinary English, and #251's run 5 headline was
  imperative too and decomposed cleanly — so the mood is not the trigger.
- **Drafted fix:** file as a sub-issue of #181.

  > **Title:** A Task headline in the imperative yields an obligation with the verb left unconjugated
  >
  > Child of #181. Labels: `bug`, `track:checker`.
  >
  > ## What happens
  >
  > #292's Gate 1 run 1 gave the decomposer this Task headline:
  >
  > > Make a changed test-evidence rating justify itself.
  >
  > `task-01` yielded two obligations. The second is
  > `changed-test-evidence-rating-justify-itself`, described as *"A changed
  > test-evidence rating justify itself."* — the imperative verb "Make" was
  > removed and the remaining "justify" was left uninflected, producing a
  > sentence that is not grammatical and an obligation that is a bare
  > restatement of the headline.
  >
  > It is typed `test_demand`, not `functional`, so it will be carried into
  > mapping and evidence judgement as a demand for a test of a sentence that
  > states no behavior distinct from `constraint-04`
  > (`changed-rating-names-one-given-change`), which says the same rule
  > grammatically.
  >
  > ## Why it is not just cosmetic
  >
  > A duplicate obligation is a criterion mapping must find tests for and the
  > judge must rate. It cannot be strongly supported on its own terms because it
  > names no behavior of its own, so it is a standing source of a
  > less-than-clean Gate 2 that no code change can close.
  >
  > ## Not the input's fault
  >
  > #251's Gate 1 run 5 (`dogfood-logs/251-gate1-run5/`) used an imperative
  > headline of the same shape — *"Re-judge a criterion's test evidence only
  > when … and make a changed rating justify itself."* — and produced two clean,
  > grammatical obligations. The imperative mood alone does not trigger it.
  >
  > ## Acceptance
  >
  > - A Task headline in the imperative yields obligation descriptions that are
  >   grammatical sentences.
  > - An obligation that restates a Constraint verbatim in different words is
  >   merged with it rather than carried alongside it.
  >
  > Evidence: `dogfood-logs/292-gate1-run1/output.log`, `judgement.md` Finding 1.
- **Status:** filed (#297, sub-issue of #181)

### [2026-08-20] A third instance of the unreconciled linking triangle, in #292's Gate 1
- **Kind:** filing (comment on existing issue #242)
- **Found during:** #292, Gate 1, run 1
- **Where:** `src/acceptance/requirement/linking.py`; evidence in
  `dogfood-logs/292-gate1-run1/output.log`, final block
- **Severity:** nice-to-have — a known, already-filed defect; this only adds an
  instance to it
- **What's wrong:** three obligations were linked transitively but at least one
  pair among them was denied, so none merged:
  `stored-rating-and-changes-recorded-with-judgement-request` (constraint-03),
  `changed-criterion-gets-stored-rating-and-dependency-changes` (completion-02),
  `stored-rating-and-dependency-changes-in-request` (completion-03).
  `constraint-03` and `completion-03` are the same sentence in the same words, so
  this is a genuine redundancy the linker should have collapsed.
- **Why I didn't act:** #242 already owns this defect; #251's Gate 1 runs 3 and 5
  hit the same shape and accepted it as residual redundancy.
- **Drafted fix:** comment on #242.

  > A third instance, from #292's Gate 1 run 1
  > (`dogfood-logs/292-gate1-run1/`), notable because the redundancy is exact
  > rather than approximate: `constraint-03` and `completion-03` in the task file
  > are the **same sentence in the same words**, and their two obligations still
  > did not merge —
  > `stored-rating-and-changes-recorded-with-judgement-request` and
  > `stored-rating-and-dependency-changes-in-request`, with
  > `changed-criterion-gets-stored-rating-and-dependency-changes` as the third
  > corner. The linker merged the easier pair in the same run
  > (`rejected-judgement-reported` across `constraint-07` and `completion-07`),
  > so the failure is specific to the triangle, not to merging in general.
  >
  > Worth recording alongside it: these task files deliberately mirror each
  > Constraint as a Completion expectation, so near-duplicate pairs are the
  > format's normal output and the linker meets them on every run.
- **Status:** filed (#242 comment)

### [2026-08-19] #225 in a controlled pair — a rating fell on a diff that only added tests, and the prescription it gained is satisfied by one of them
- **Kind:** filing (comment on existing issue #225)
- **Found during:** #258, Gate 2, runs 3 and 4
- **Where:** `dogfood-logs/258-gate2-run3/` and `-run4/`
- **Severity:** should-fix — it is why #258's gate moved away from clean while
  its evidence grew
- **What's wrong:** the only difference between the two runs is one commit that
  adds six tests. Three obligations improved and a fourth — the sole
  `strongly supported` one — fell to `partially supported`, leaving **zero**
  strongly supported. The prescription it gained names a defect that a test in
  the same diff detects; the mapping cited that test against three *other*
  obligations.
- **Why I didn't act:** #225 owns it, and nothing #258 can write fixes a rating
  that falls when evidence is added.
- **Drafted fix:** comment on #225:

  > A controlled instance of both halves of this title, from #258's Gate 2 runs
  > 3 and 4 (`dogfood-logs/258-gate2-run3/`, `-run4/`).
  >
  > The pair is controlled in the way that matters: same base, same mandate, and
  > the head differs by **one commit that only adds tests**. The source under
  > review is byte-identical.
  >
  > ```
  > Changes since a752f82c:
  >   moved:
  >     - A test asserts that parsing succeeds for every committed task file …
  >         test evidence: strongly supported -> partially supported
  >     - No test reads the task file at the repository root.
  >         test evidence: indeterminate -> partially supported
  >     - A test run reports no failures when no task file is present …
  >         test evidence: unsupported -> partially supported
  >     - No test's outcome or case list depends on the task file …
  >         test evidence: unsupported -> partially supported
  > ```
  >
  > Three obligations rose. The one that had been `strongly supported` fell, so
  > the review went from one strongly-supported obligation to **none** while
  > strictly gaining evidence.
  >
  > The second half of the title lands too, and slightly harder than the original
  > instance. Obligation 1's new prescription:
  >
  > > **detects:** Parser silently skips one committed file by not including it in
  > > the parametrized corpus.
  >
  > `tests/requirement/test_task_file_corpus.py::test_the_parse_test_enumerates_the_corpus_and_nothing_else`
  > is in the diff and asserts exactly that — the parametrize's argvalues equal
  > `committed_task_files()`, so a file omitted from the parametrized corpus
  > fails it. It was not cited against obligation 1. It **was** cited against
  > obligations 6, 7 and 10 in the same report, so this is not a discovery
  > failure: the test was found, judged relevant three times, and the obligation
  > whose prescription it answers was not one of them.
  >
  > Worth recording what improved in the same run, so the report is not read as
  > uniformly worse: obligations with `(no mapped test)` went from three to zero.
  > The mapping got better and the ratings got worse.
  >
  > ## Two more runs, and the cleanest instance is in run 5
  >
  > Runs 5 and 6 added six more tests, closing eight obligations and then two
  > more. In run 5, obligation 12's block reads — prescription and citation two
  > lines apart:
  >
  > ```
  >        test evidence: partially supported  [tier: static]
  >          12.2  tests/requirement/test_task_file_corpus.py::test_an_entry_whose_target_is_missing_is_omitted
  >          recommended test: The region-coverage case list excludes at least one path that is absent from the tree.
  >            detects: The corpus builder omits a present file as well as the missing one.
  > ```
  >
  > That test asserts `committed_task_files(tmp_path) == [real]`: the dangling
  > entry omitted, the real one kept — exactly the named defect. The stage cited
  > it as the obligation's evidence and prescribed it in the same breath, with no
  > second test in between.
  >
  > In run 6, on a diff that only added tests and fixed a docstring, that same
  > obligation went **`partially supported -> unsupported`** — no mapped test —
  > while the test above sat unchanged in the tree, and a second obligation went
  > `strongly supported -> partially supported`. Across four runs the same
  > obligations were rated 1, 0, 8 and 9 strongly supported over monotonically
  > increasing evidence.
  >
  > One more datum for the same file: **every defect statement changed between
  > run 3 and run 4** — fourteen of fourteen, for obligations whose text never
  > moved and against source that never changed. Whatever the prescription
  > describes, it is not a stable property of the gap.
- **Status:** filed (#225 comment)

### [2026-08-19] Recommendations prescribe tests for behavior the mandate declares out of scope
- **Kind:** filing (new issue, child of #185)
- **Found during:** #258, Gate 2, run 3
- **Where:** `src/acceptance/coverage/recommendations.py` — the stage's prompt
  never sees the scope exclusions
- **Severity:** should-fix — it makes a gate unreachable by asking for work the
  mandate forbade
- **What's wrong:** two of the thirteen prescriptions ask for parser edge cases —
  an empty-section format, and an off-by-one span boundary — when *"how a task
  file is parsed into sections"* is `exclusion-02` of the same task file, which
  the same report shows as `addressed`. The tool holds the exclusion and
  prescribes against it in one run.
- **Why I didn't act:** #258 touches `tests/` only, and the fix is a prompt
  change that re-records the recommendation stage.
- **Drafted fix:** file as a child of #185, `bug` / `track:checker`:

  > **Title:** Test recommendations cross the mandate's own scope exclusions
  >
  > From #258's Gate 2 run 3 (`dogfood-logs/258-gate2-run3/`). The task file
  > declares five scope exclusions, among them:
  >
  > ```
  > ## Scope exclusions
  > - How a task file is parsed into sections.
  > ```
  >
  > which the report renders as obligation 16, `addressed`, *"examined 7 changes
  > across 5 files; none breaches this boundary."* Two prescriptions in the same
  > report ask for exactly that behavior:
  >
  > | obligation | prescribed input | defect it claims to catch |
  > |---|---|---|
  > | 8, `parse-test-nonempty-sections` | *"a fixture that contains one or more empty sections or edge-case formatting"* | *"Parser preserves non-empty sections for the specific tested files but would fail on an untested edge-case format"* |
  > | 9, `parse-test-span-roundtrip` | *"a fixture whose spans are adjacent to punctuation, blank lines, or section boundaries so an off-by-one span bug changes the extracted text"* | *"Parsed spans use off-by-one boundaries"* |
  >
  > Both are defects **in the parser**, which this mandate excluded. Writing
  > either test would be work the mandate forbade, and not writing it holds the
  > obligation at `partially supported`, so the gate cannot be reached by any
  > action the mandate permits.
  >
  > `_render_prompt` supplies the criterion, its evidence class, the surviving
  > defects and the diff. It supplies no exclusions, so the stage cannot know.
  > The obligations carrying them are in the same review — five of them, each
  > `satisfied_by_absence`, each already decided at decomposition — so this is a
  > matter of passing what the review already holds, not of deriving anything
  > new.
  >
  > Suggested: render the exclusion obligations into the recommendation prompt as
  > boundaries the prescribed test must not require crossing, and reject or
  > re-ask for a prescription whose required inputs are an exclusion's subject.
  > The weaker version — prompt-only, no validation — is worth having on its own.
- **Status:** filed (#282, sub-issue of #185). A *Where* and an *Acceptance*
  section were added at filing time, beyond the approved draft.

### [2026-08-19] A prescription's `detects` names a defect that would not violate the obligation
- **Kind:** filing (new issue, child of #185)
- **Found during:** #258, Gate 2, run 3
- **Where:** `src/acceptance/coverage/recommendations.py`, `_Recommendation.plausible_defect`
- **Severity:** should-fix
- **What's wrong:** obligation 11 is *"The region-coverage case list is
  non-empty."* Its prescription is to catch *"the case list is non-empty but
  missing some intended coverage cases"* — a defect that satisfies the
  obligation. A test built to that spec cannot be evidence for it, so the
  obligation stays `partially supported` however the test is written.
- **Why I didn't act:** out of #258's area, and it needs a validation step the
  stage does not have.
- **Drafted fix:** file as a child of #185, `bug` / `track:checker`:

  > **Title:** A prescribed test's target defect does not always violate the obligation
  >
  > From #258's Gate 2 run 3 (`dogfood-logs/258-gate2-run3/`). The system prompt
  > is explicit that *"the test you prescribe must catch exactly that defect"*,
  > and the defect is what makes the test discriminating. Three of thirteen
  > prescriptions name a defect that is not a violation of the criterion:
  >
  > - **Obligation 11** — criterion *"the region-coverage case list is
  >   non-empty"*; defect *"the case list is non-empty but missing some intended
  >   coverage cases"*. The defect states the criterion holds.
  > - **Obligation 12** — criterion *"the case list omits a path that is not
  >   present in the tree"*; defect *"a different missing path is omitted
  >   correctly, but the specific dangling symlink in the test is still
  >   included"* — circular: the defect is defined in terms of the test that is
  >   being prescribed to find it.
  > - **Obligation 2** — criterion *"a test asserts the case list is non-empty"*;
  >   defect *"the case list is populated only in some environments"*, which no
  >   test run in one environment can falsify.
  >
  > These are not weak prescriptions; they are unreachable ones. An obligation
  > whose prescribed defect cannot violate it can never leave `partially
  > supported`, which turns a gate that requires *strongly supported* into one
  > that cannot be passed. Related in symptom to #225/#252 (ratings held down by
  > defects no test can kill), but distinct in cause: this is the *defect
  > statement* being wrong, not the rating moving.
  >
  > Suggested: a cheap check with real teeth — ask the stage, in the same
  > constrained response, to state which part of the criterion the defect
  > violates, and reject a prescription that cannot. It is the same shape as the
  > `required_evidence_reason` #271 added at decomposition, and it makes the
  > claim falsifiable by a reader.
  >
  > ## Update after three more runs: this is the whole residue
  >
  > #258 then wrote ten tests against the prescriptions, over runs 4, 5 and 6,
  > taking the weak set from 13 to 5. **All five survivors are this defect**, and
  > they are what now stands between that branch and a clean gate:
  >
  > | obligation | defect the prescription names | would it violate the obligation? |
  > |---|---|---|
  > | `…-non-empty-test` | *"only contains a filtered subset but still at least one item"* | no — still non-empty |
  > | `…-stays-within-dogfood-logs-test` | *"includes only dogfood-logs paths but also duplicates one"* | no — all still under `dogfood-logs/` |
  > | `…-case-list-source` | *"also includes a synthetic in-memory case not backed by a file"* | no |
  > | `…-case-list-nonempty` | *"contains only one case when several should exist"* | no — still non-empty |
  > | `…-omits-missing-path` | *"excludes at least one path that is absent from the tree"* | **that is the obligation's own text** |
  >
  > The last one is the limiting case: the prescription asks for a test that
  > catches the criterion **being satisfied**. Nothing can be written against it,
  > because there is nothing to detect. An obligation in this state cannot reach
  > `strongly supported` by any amount of work, so a gate that requires it is
  > unreachable rather than demanding — see `dogfood-logs/258-gate2-run6/`.
- **Status:** filed (#283, sub-issue of #185). A *Where* and an *Acceptance*
  section were added at filing time, beyond the approved draft.

### [2026-08-19] #266 landed and the recommendation abort survived it — one omission of thirteen still destroys the whole report
- **Kind:** filing (new issue, child of #185)
- **Found during:** #258, Gate 2, run 2
- **Where:** `src/acceptance/coverage/recommendations.py:195`
- **Severity:** blocker — #258's Gate 2 has now been unassessable twice, and the
  second time was against the tool that was fixed for the first
- **What's wrong:** #266 moved the *"is a test owed here at all"* judgement up to
  decomposition and made silence the only thing `recommend_tests` rejects. It
  worked for its own cases: the two obligations that aborted #258's run 1 were
  both answered this time. But the model omitted a **different** criterion, and
  the stage still converts one omission out of thirteen into a hard abort — no
  report, no verdict, no findings for the other twelve, and no retry anywhere on
  the path.
- **Why I didn't act:** #258 touches `tests/` only; the abort is in
  `coverage/`, and the fix needs a design call on what the report says about an
  obligation whose recommendation was never obtained. Same reason as last time.
- **Drafted fix:** file as a child of #185, `bug` / `track:checker`:

  > **Title:** A single omitted recommendation still aborts the entire review, after #266
  >
  > #266 fixed the *cause* it was filed for and left the *disposition* in place.
  > From #258's Gate 2 run 2 (`dogfood-logs/258-gate2-run2/`), against `main`
  > with #266 landed:
  >
  > ```
  > acceptance: model error: no recommendation for 1 of 13 weak obligation(s): no-root-task-file-read
  > ```
  >
  > The good news first: #266 works. The two obligations that aborted run 1 —
  > `region-coverage-case-list-omits-missing-path` and
  > `no-failures-without-root-task-file` — were both answered this time. Neither
  > was excused from needing a test at decomposition either; both came back
  > `code_and_tests`. The new axis fired only where it should have.
  >
  > What survived is the response to silence. Transcript
  > `adf65d6a…f993ed.json`, a single unpartitioned call:
  >
  > - 13 criteria supplied, 12 returned; the skipped one is at **position 4**,
  >   not the tail.
  > - `stop_reason: "stop"`, 2,901 completion tokens. Not truncation, and not the
  >   DR-164 call-size shed — positions 5–13 all came back.
  >
  > `_weak_obligations`' docstring argues that silence now has "no correct
  > reason", since `required_evidence` is decided upstream. That is a sound claim
  > about what the model *ought* to do and an unsound basis for what the stage
  > should do when it doesn't. A model that skips one of thirteen is not a
  > contract violation the review can be abandoned over; it is an indeterminate
  > result about **one** obligation.
  >
  > That is the invariant this collides with: *uncertainty is first-class —
  > `Indeterminate` and open-question outputs are valid, expected results.*
  > Recording the omission as an unusable answer, or as an `Indeterminate`
  > finding reading *"no recommendation was produced for this obligation"*,
  > would keep the review, keep the gate red for an honest and legible reason,
  > and lose exactly the one prescription. Aborting loses twelve good ones with
  > it. The guard's real purpose — that a silent omission must never be
  > indistinguishable from a complete answer — is served either way.
  >
  > A retry is worth considering alongside it, since there is currently none: one
  > re-ask for the missing ids only would likely close most instances, and what
  > survives a retry is a much stronger signal than what survives a first call.
  >
  > **On the cause, offered as a hypothesis rather than a finding:** the skipped
  > criterion at position 4, `no-root-task-file-read` (*"Test execution does not
  > access the repository-root task file"*), is a near-duplicate of position 3,
  > `no-root-task-file-read-check` (*"A check asserts that no test reads the task
  > file at the repository root"*) — a Constraint and its Completion twin,
  > arriving adjacently, describing one property from two sides. The model
  > answered the first and dropped the second. The competing explanation — that
  > criteria with no surviving-defect list get dropped — does **not** hold: three
  > criteria had none and two of them were answered. If the duplicate-pair
  > reading is right, this is #245 (twin obligations) manifesting as an abort two
  > stages downstream, which is an argument for fixing the disposition regardless
  > of how far #245 gets.
  >
  > Also still true and still worth fixing, carried over from #266: **the
  > transcript records no stop reason on the request side**, so separating
  > truncation from a short-but-complete answer means reconstructing it from
  > token counts.
- **Status:** filed (#275, sub-issue of #185). A *Where* and an *Acceptance*
  section were added at filing time, beyond the approved draft, so the issue is
  workable.

### [2026-08-19] #245 gains an instance where the twin split is visible without a report
- **Kind:** filing (comment on existing issue #245)
- **Found during:** #258, Gate 2, run 2
- **Where:** `dogfood-logs/258-gate2-run2/`, obligations `no-root-task-file-read`
  and `no-root-task-file-read-check`
- **Severity:** should-fix
- **What's wrong:** the Constraint `no-root-task-file-read` came back
  **`unsupported`** — no mapped test — while its Completion twin
  `no-root-task-file-read-check` came back `partially_supported`.
  `tests/test_root_task_file_is_not_read.py` exists, is 94 lines, and is exactly
  the test for both. One of the pair got it; the other got nothing.
- **Why I didn't act:** #245 already owns the twin split, and #258 cannot act on
  the finding anyway — the run aborted before rendering, so this is visible only
  in the recommendation call's input.
- **Drafted fix:** comment on #245:

  > Another instance, from #258's Gate 2 run 2 (`dogfood-logs/258-gate2-run2/`),
  > with two features the earlier ones did not have.
  >
  > The pair is `no-root-task-file-read` (Constraint: *"No test reads the task
  > file at the repository root"*) and `no-root-task-file-read-check`
  > (Completion: *"A check asserts that no test reads the task file at the
  > repository root"*). One test serves both —
  > `tests/test_root_task_file_is_not_read.py`, which is the whole point of the
  > delivery. The Completion twin was rated `partially_supported`; the Constraint
  > twin was rated **`unsupported`**, i.e. no mapped test at all.
  >
  > 1. **It is visible without a report.** The run aborted at the recommendation
  >    stage, so no §16 report was ever rendered. The split shows up in the
  >    *input* to that stage — the criteria list carries each obligation's
  >    evidence class — which means this failure mode can be observed even on
  >    runs that produce nothing.
  > 2. **It may not stop at a wrong rating.** The two obligations arrived
  >    adjacently in the recommendation call, and the second of the pair is
  >    exactly the criterion the model then silently skipped, aborting the review.
  >    That is one run and a hypothesis, not a demonstrated cause — but if it
  >    holds, the twin split is not only mis-rating obligations, it is feeding
  >    duplicate-looking criteria into a downstream call that answers them once.
  >    Filed separately as the disposition defect (child of #185).
- **Status:** filed (#245 comment) — the last line names #275, the number the
  disposition defect actually got.

### [2026-08-19] `decompose`'s text output hides the very field Gate 1 is required to check
- **Kind:** filing (new issue, child of #185)
- **Found during:** #258, Gate 1, run 3
- **Where:** `src/acceptance/cli.py:340-381`
- **Severity:** nice-to-have
- **What's wrong:** #266 added `required_evidence` and
  `required_evidence_reason` to every obligation, and the reason is the only
  thing a human can argue with when the tool decides an obligation needs no test.
  `decompose`'s text output renders neither. Reading them at Gate 1 means
  re-running with `--json` and writing a script to walk it.
- **Why I didn't act:** presentation, outside #258's area, and the workaround is
  one command.
- **Drafted fix:** file as a child of #185, `enhancement` / `track:checker`:

  > **Title:** `decompose` does not show `required_evidence` or its reason
  >
  > #266 made *"which kinds of evidence does this obligation require"* a
  > decomposition-time judgement, and the dogfooding procedure now requires
  > reading the stated reason at Gate 1 — a wrong *"no test is owed here"* is the
  > false green the design is most exposed to, and the reason is the only thing a
  > reader can argue with.
  >
  > `acceptance decompose` prints the requirement, the obligation id, its
  > `type/derivation` and its restated text. It does not print `required_evidence`,
  > `required_evidence_reason` or `satisfied_by_absence`. Checking them means
  > re-running with `--json` and parsing it by hand, which is what #258's Gate 1
  > run 3 had to do.
  >
  > Suggested: append the value to the existing bracket — `[test_demand/explicit,
  > tests_only]` — and print the reason under the restated text when one is
  > given, the way `report.py` already does for the rendered report. Only
  > obligations that departed from the `code_and_tests` default carry a reason,
  > so on a typical task file this adds a handful of lines.
- **Status:** filed (#276, sub-issue of #185). A *Where*, a *Deliverable* and an
  *Acceptance* section were added at filing time, beyond the approved draft.

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
- **Status:** filed (#205 comment). Two changes made at filing time: the stale
  `AdmissibleEvidence` name corrected to `required_evidence` (#266 renamed it),
  and a third run added — `dogfood-logs/258-gate1-run3/` re-decomposes run 2's
  task file under #266's changed prompt and reproduces run 2's typing exactly,
  which cuts against the finding and is on the record for that reason.

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
- **Status:** wont-fix (the rule alone, for now — human decision, 2026-08-19).
  Revisit only if a stale shard actually survives a landed task; the `gh`-driven
  check stays drafted above if it is ever wanted.
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
  3. `run_once` filters `client.observed` for `ObligationDiscrimination`, which
     the stage builds *after* `complete` returns — so it never crosses the client
     and the filter matched nothing, for every input. **This one did not raise.**
     It reported success with an empty `defect_verdict_distribution`, which is
     the only axis #191 moves. Fixed on the branch (`9ee0de9`) with the test that
     would have caught it; the other two are still uncovered.

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
- **Status:** filed (#289, sub-issue of #186) — **a blocker for #191**

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

### [2026-08-12] Perturbation sensitivity divides a numerator that can count judgements its denominator excludes
- **Kind:** defect
- **Found during:** #191, taking the pre-change baseline
- **Where:** `src/acceptance/benchmark/instability.py::_perturbation_result`
- **Severity:** should-fix
- **What's wrong:** `watched_judgements` is `len(obligations) + len(open_questions)`,
  but `changed_judgements` counts the distinct subjects of *any* content
  difference — including a `defect_verdict` flip, whose subject is
  `"<obligation> :: <defect wording>"` and is not in the denominator. The two
  were consistent only for as long as `defect_verdicts` was always empty, which
  is to say only because of the bug fixed in `ea42e4f`. Now that the axis
  populates, the ratio can exceed 1.
- **Why I didn't act:** #191's Acceptance compares a post-change sensitivity
  figure against the pre-change one, and changing how that figure is computed
  in the same PR would make the two incomparable — the one thing the issue's
  Costs section asks to avoid. It has to move after the comparison, not during.
- **Drafted fix:** count the watched population per axis rather than as one
  total: obligations + open questions for the presence and evidence-class axes,
  and the number of `(obligation, defect)` keys present in *both* snapshots for
  the verdict axis, since a key present in only one is not a judgement that
  moved. Report a sensitivity per axis and never a blended one, for the same
  reason `content` and `shape` are never summed.
- **Status:** filed (#290, sub-issue of #186). Re-verified against the code at
  `ed6f4b9` before filing — `_perturbation_result` is unchanged, so the drafted
  fix was filed as written, with an Acceptance section added.

### [2026-08-12] Record #191's pre-change baseline figures on the issue
- **Kind:** filing (comment on existing issue #191)
- **Found during:** #191, taking the pre-change baseline
- **Where:** `docs/experiments/191-discrimination-partition/`
- **Severity:** blocker — #191's Acceptance says the numbers are recorded on the issue
- **What's wrong:** nothing is wrong; the Acceptance requires the baseline be
  posted, and it now exists and is reproducible.
- **Why I didn't act:** filings wait for the gate.
- **Drafted fix:** comment on #191:

  > Pre-change baseline, taken before touching `evidence/discrimination.py`.
  > Reproducible with `docs/experiments/191-discrimination-partition/retake_baseline.py`,
  > which replays the recordings rather than re-buying them, and asserts the task
  > digest so a wrong reconstruction fails instead of quietly measuring a
  > different case.
  >
  > Case `167-gate2-run4`, base `839ea47` → head `52c52b8`, `openai/gpt-5.4-mini`,
  > 3 runs at seeds 1000/1001/1002, perturbation `add-unrelated-test`.
  >
  > | figure | pre-change |
  > |---|---|
  > | calls: decompose / map / **discriminate** | 3 / 7 / **1** |
  > | defects enumerated per run | 38 — exactly 2 for each of 19 obligations, all three runs |
  > | `would_be_caught: true` | **38 of 38**, every run |
  > | defect keys shared by ≥2 runs | **0 of 114** |
  > | evidence-class content differences across runs | mean 0.67, spread 2.0 |
  > | perturbation sensitivity | 1 of 21 watched judgements moved |
  >
  > Two things in that table bear on how this issue is judged.
  >
  > **The uniformity.** One call covering 19 obligations returns exactly two
  > defects each and catches all of them, three times over. That is the DR-164
  > signature — schema-valid while shedding the work — and it is the direct
  > argument for (a).
  >
  > **The defect set does not repeat at all.** 114 distinct
  > `(obligation, defect wording)` keys over three runs, each appearing exactly
  > once. `compare_runs` keys a verdict on the exact defect string, so with no
  > shared key the verdict axis reports zero differences *by construction*:
  > verdict stability today is **unmeasurable, not good**. This is DR-180's
  > second-order finding measured rather than inferred, and it is the direct
  > argument for (b).
  >
  > Consequence for the Acceptance as written: a post-change run reporting *more*
  > comparable subjects, or more detected verdict differences, is the axis
  > starting to work rather than a regression. The count of comparable subjects
  > has to be read before the count of differences.
  >
  > Also worth recording: this axis was empty in the first attempt at the
  > baseline. The harness filtered the client's observations for
  > `ObligationDiscrimination`, which is built inside the stage after `complete`
  > returns and never crosses the client (`ea42e4f`). The re-taken report is
  > byte-identical to the first everywhere except that axis, which went from 0
  > subjects to 114 — same recordings, corrected extraction.
- **Status:** filed (comment on #191). One line added at filing time: #289 now
  carries the harness defect, and blocks judging #191 against a pre-change
  number until it is fixed on `main`.

### [2026-08-12] Ratings moved on a tests-only diff in #191's own Gate 2 — post-change
- **Kind:** filing (comment on existing issue #225)
- **Found during:** #191, Gate 2, rounds 1 and 2
- **Where:** `dogfood-logs/191-gate2-run1/` and `191-gate2-run2/`
- **Severity:** should-fix — it does not block this delivery, but it is the
  subject matter of the change being delivered
- **What's wrong:** round 2 differs from round 1 by **added tests only** — the
  three tests that close round 1's findings, and nothing else. Three obligations
  rated `strongly supported` in round 1 came back **non-discriminating** in
  round 2, with nothing about their own evidence changed:

  | obligation | round 1 | round 2 |
  |---|---|---|
  | `test-editing-mapped-test-leaves-other-obligation-defects-unchanged` | strongly supported | non-discriminating |
  | `test-adding-mapped-test-leaves-obligation-defects-unchanged` | strongly supported | non-discriminating |
  | `test-review-pipeline-uses-separated-defect-verdict-steps` | strongly supported | non-discriminating |

  Checked on merits before being recorded here, per DR-180. **One of the three
  was a real finding** — the editing test genuinely edited nothing, and is fixed
  in `dbff85e`. The other two describe, in detail, tests that already exist and
  that the same report cites: the recommendation for
  `test-adding-mapped-test-leaves-obligation-defects-unchanged` asks for a test
  that adds a mapped test and observes the enumerated defects are unchanged,
  which is `test_adding_a_test_leaves_the_obligations_enumeration_request_unchanged`,
  cited in that very obligation's evidence. That is the #225-family failure of
  recommendations making checkable false claims about the code.
- **Why I didn't act:** the real finding is fixed; the other two have no code
  change that answers them. Writing a third test to satisfy a judge that already
  found the second one is chasing a rating rather than fixing a defect.
- **Drafted fix:** comment on #225 carrying the table above, and noting what
  makes this instance worth recording: **it is post-change, on the branch that
  fixes the enumeration half.** #191 stabilises which defects are *named*; these
  three obligations moved anyway. That is evidence the verdict half is a
  separate defect not closed by #191 — which is what #192 is for — and it is the
  first time that separation could be observed at all, because before #191 no
  defect wording ever repeated between runs, so the verdict axis had nothing to
  compare.
- **Status:** filed (comment on #225). The persistent-recommendation half was
  split out to #287 at filing time and the comment says so.

### [2026-08-12] A recommendation flagged the same obligation three runs running while citing the test that satisfies it
- **Kind:** filing (new issue, child of #185)
- **Found during:** #191, Gate 2, rounds 1–3
- **Where:** `dogfood-logs/191-gate2-run{1,2,3}/`, `test-verdict-call-carries-configured-bounded-obligations`
- **Severity:** should-fix
- **What's wrong:** the obligation was rated `partially supported` in all three
  rounds. By round 3 the run cites **both** relevant tests, including
  `test_the_verdict_bound_counts_criteria_and_not_defects`, which was written in
  round 2 to satisfy this very recommendation and does everything its `inputs`
  asks: more criteria than the batch size, one criterion carrying five defects
  so defect count and criterion count diverge, and an assertion over the
  verdict-call request payload rather than the final review.

  The `detects` clause is also incoherent in rounds 2 and 3:

  > The verdict request is built from the wrong batch dimension, so the number of
  > defects carried per call is bounded by the number of obligations instead of
  > the configured defect-verdict batch size.

  That inverts the two dimensions. The mandate bounds *obligations per verdict
  call* (`constraint-03`), which is exactly what `defect_verdict_batch_size`
  does. Round 1's statement of the same finding was coherent, so the wording
  degraded while the flag persisted.
- **Why I didn't act:** there is no code change that answers it. The test the
  recommendation describes exists and the same report cites it; writing a third
  is chasing a rating.
- **Drafted fix:** file as a child of #185, `bug` / `track:checker`:

  > **Title:** A recommendation persists across three runs while citing the test that satisfies it
  >
  > Worth separating from the #225 family even though it looks similar. #225 is
  > about ratings **moving** — the same evidence judged differently between runs.
  > This one does not move: it is wrong in the same way three times, which means
  > it is not the instability and will not be fixed by anything that stabilises
  > the judge.
  >
  > From `dogfood-logs/191-gate2-run{1,2,3}/`, obligation
  > `test-verdict-call-carries-configured-bounded-obligations`:
  >
  > | round | rating | tests cited | recommendation asks for |
  > |---|---|---|---|
  > | 1 | partially supported | 1 | uneven defect counts across criteria |
  > | 2 | partially supported | 2 (incl. the test written for round 1's ask) | the same thing |
  > | 3 | partially supported | 2 | the same thing again |
  >
  > Round 2 added `test_the_verdict_bound_counts_criteria_and_not_defects`
  > precisely to close round 1's recommendation. Round 3 cites it and repeats the
  > recommendation.
  >
  > Two candidate mechanisms, both worth checking before picking a fix:
  >
  > 1. The recommendation is generated from the obligation and the diff without
  >    reading the cited tests, so it cannot notice the ask is already met.
  > 2. The rating and the recommendation are produced together, so a
  >    `partially supported` rating obliges a recommendation and one gets written
  >    whether or not a gap exists.
  >
  > The garbled `detects` clause is evidence for (1): it describes a defect in
  > terms that do not correspond to the code's actual batching dimension.
- **Status:** filed (#287, sub-issue of #185)

### [2026-08-12] #245: a test mapped in round 1 reports "(no mapped test)" in round 3, while its file is cited in the same obligation
- **Kind:** filing (comment on existing issue #245)
- **Found during:** #191, Gate 2, rounds 1 and 3
- **Where:** `dogfood-logs/191-gate2-run{1,3}/`, `test-adding-mapped-test-leaves-obligation-defects-unchanged`
- **Severity:** should-fix
- **What's wrong:** round 1 rated the obligation `strongly supported`, citing
  `tests/test_discrimination_wiring.py::test_adding_a_test_leaves_the_obligations_enumeration_request_unchanged`
  — a test whose name is very nearly the obligation's own text. Round 3 rates it
  **`unsupported`** with **"(no mapped test)"**, while the *code* evidence for
  the same obligation cites `tests/test_discrimination_wiring.py`, the file that
  contains it. Nothing about the test changed between the runs.
- **Why I didn't act:** the test exists, is named almost identically to the
  obligation, and was found once already. There is nothing to write.
- **Drafted fix:** comment on #245, adding this instance to the record. What it
  contributes beyond the existing ones: the report **points at the file in one
  axis and denies the test exists in the other, in the same obligation, in the
  same run.** Previous instances split a test between two obligations or moved a
  mapping between runs; this one is internally contradictory within a single
  rendered obligation, which makes it visible to a reader without a second run
  to compare against.
- **Status:** filed (comment on #245)

### [2026-08-13] Unrequested-change detection is blind to REMOVALS
- **Kind:** filing (new issue, child of #185)
- **Found during:** #191, Gate 2 rounds 1–3
- **Where:** `src/acceptance/coverage/unrequested.py`
- **Severity:** should-fix — it is a whole class of miss, not one miss
- **What's wrong:** the #191 branch removed the changed-code block from the
  defect-verdict prompt. Nothing in the mandate asked for it, it took an input
  away from a judging stage, and measured against the pre-change baseline it
  took evidence-class movement from 2 to 16. **Three Gate 2 rounds reported nine
  unrequested changes between them and none named it.** The two that came
  closest were both dispositioned `in_service` — i.e. accepted:

  > round 1: "…introduce a specific two-stage prompt structure… and **alter
  > adjacent behavior such as prompt contents** and batching strategy."
  > round 3: "…the specific helper reshaping and private model renaming are
  > **internal implementation details**."

  Meanwhile it rated a `*args/**kwargs` signature change on a benchmark helper
  as `risky`, and thought new CLI flags were worth reporting.

  Every one of the nine is phrased as *"X **beyond** what's required."* The
  detector is looking for additions. A deletion — a removed input, a weakened
  assertion, a dropped guard, a narrowed prompt — appears to be structurally
  invisible to it, which predicts a whole class of misses rather than one.
- **Why I didn't act:** out of scope for #191, and the fix is a change to what
  the detection call is asked for, which re-records that stage.
- **Drafted fix:** file as a child of #185, `bug` / `track:checker`:

  > **Title:** Unrequested-change detection finds additions and is blind to removals
  >
  > Worked example, from the tool reviewing its own branch across three rounds:
  > `#191` deleted the changed-code block from the defect-verdict prompt. Not
  > requested by any obligation, and measurably harmful — the judge got worse on
  > the project's own instability measure. Nine unrequested changes were reported
  > across the three rounds and not one named the deletion.
  >
  > The phrasing of all nine is the tell: every one is *"X beyond what's
  > required."* The stage is being asked what the diff **adds** that the mandate
  > did not ask for. Nothing asks what it **takes away**.
  >
  > This matters more than a single miss because removals are the higher-risk
  > half. Adding an unrequested CLI flag is noise; removing an input from a
  > judging stage, deleting a guard, or weakening an assertion changes behaviour
  > silently and is exactly what a reviewer is for.
  >
  > Suggested acceptance: a diff that deletes a prompt input, a guard, or an
  > assertion, with no obligation calling for the deletion, is reported as an
  > unrequested change — and is not dispositioned `in_service` by default.
- **Status:** filed (#288, sub-issue of #185)

### [2026-08-13] Token usage is recorded without the cached-token count
- **Kind:** defect
- **Found during:** #191, measuring prompt-cache effectiveness
- **Where:** `src/acceptance/llm.py::_extract_usage`
- **Severity:** nice-to-have
- **What's wrong:** it records `prompt_tokens`, `completion_tokens`,
  `total_tokens` and `cost_usd`, and drops `prompt_tokens_details.cached_tokens`.
  Since #191 both discrimination calls repeat the whole diff per batch and rely
  on the provider's prompt cache to make that affordable — measured live at
  84–93% of each verdict request served from cache — so the one number that says
  whether the design is working is the one not kept. Answering it needed an ad
  hoc script issuing live calls.
- **Why I didn't act:** it is in `llm.py`, outside #191's area, and the question
  it answers was answered another way.
- **Drafted fix:** add `cached_tokens` to `_extract_usage` when the provider
  reports it. Response-side metadata only — it is not part of the request key,
  so it invalidates no transcript and can land any time. Roughly:

  ```python
  details = getattr(raw, "prompt_tokens_details", None)
  cached = getattr(details, "cached_tokens", None) if details else None
  if cached is not None:
      usage["cached_tokens"] = cached
  ```
- **Status:** fixed on `main` by `82e4ec7` (#285), which landed while this entry
  sat in the queue. `_extract_usage` now records `cached_tokens`,
  `cache_creation_tokens` and `cache_write_tokens` through a `_usage_field`
  accessor, with `tests/test_usage.py` and `tests/test_stage_attribution.py`
  covering it — a wider fix than this entry drafted, and it makes the same
  absent-is-not-zero argument.

  **How this was nearly duplicated, which is the part worth keeping.** #251's
  Gate 1 triage re-verified all 14 open entries and reported this one "still
  live" — against a worktree six commits behind `origin/main`, with no `git
  fetch` first. A duplicate fix was written, tested and about to be committed
  before the fetch that preceded the commit revealed #285. **Re-verification at a
  gate has to `git fetch` first**; a branch cut days ago is not the current code,
  and the queue is precisely the place where slow-moving items get overtaken.

### [2026-08-13] A restatement inserts a negation the source does not carry — #262's second and harsher instance
- **Kind:** filing (comment on existing issue #262)
- **Found during:** #266, Gate 1
- **Where:** `dogfood-logs/266-gate1-run1/output.log`, `constraint-09`
- **Severity:** should-fix
- **What's wrong:** the requirement reads *"…from a criterion for which no test
  **was** recommended."* The obligation derived from it, flagged `explicit`,
  reads *"…for which no test **was not** recommended."* An inserted negation
  inverts the second half of the comparison, so the obligation demands the
  opposite distinction from the one the mandate states. `explicit` is the flag
  that claims the text is a restatement rather than an inference, which is
  precisely the claim being broken.
- **Why I didn't act:** the wording was also poor and I rewrote it (run 2), but
  the rewrite is not the report — the source sentence was parseable and
  unambiguous, so the inserted `not` is a derivation failure on its own terms.
  Fixing the tool is outside #266's scope.
- **Drafted fix:** comment on **#262**, which is the same failure family
  (a paraphrase that does not preserve entailment) rather than a new issue:

  > **A second instance, and a harsher one: an inserted negation.**
  >
  > From #266's Gate 1 (`dogfood-logs/266-gate1-run1/`):
  >
  > | | text |
  > |---|---|
  > | requirement `constraint-09` | The report distinguishes a criterion for which no test was recommended because none can evidence it from a criterion for which no test **was** recommended. |
  > | derived obligation | …from a criterion for which no test **was not** recommended. |
  >
  > #262's original instance widened a bound — `does not reduce` became
  > `preserves the number`, which still entails part of the source. This one
  > reverses a polarity: the derived obligation is satisfied by exactly the
  > behaviour the requirement forbids. Same stage, same `explicit` flag, same
  > loss inside the restatement, one step further along.
  >
  > It suggests the acceptance criterion on #262 wants widening beyond
  > one-sided quantifiers: an `explicit` obligation must preserve the
  > **polarity** of every clause it restates, not only the direction of a bound.
  >
  > Two notes on scope. The source sentence was genuinely badly worded — a
  > self-comparison whose halves differ only by a trailing clause — and #266
  > rewrote it under the sanctioned-rewrite rule; the re-run derived both
  > halves faithfully. That says the wording was a contributing factor, not
  > that the derivation was correct. And the remaining 27 obligations in the
  > same run are faithful, so this is narrow, as #262's original was.
- **Status:** filed (comment on #262)

### [2026-08-13] An inferred obligation duplicates an explicit one and the linker does not reconcile them
- **Kind:** filing (new issue, child of #181)
- **Found during:** #266, Gate 1
- **Where:** `dogfood-logs/266-gate1-run1/output.log`, `task-01` vs `constraint-01`
- **Severity:** should-fix
- **What's wrong:** `task-01` yielded an `inferred` obligation,
  `no-test-can-evidence-criterion-statement-supported` — *"A criterion may be
  answered with a statement that no test can evidence it."* `constraint-01`
  yielded `recommendation-may-state-no-test-can-evidence` — *"A test
  recommendation may state that no test can evidence its criterion."* Those are
  the same demand under two ids. The linking stage exists to reconcile exactly
  this and did not, so the obligation set carries a redundancy that will demand
  its own evidence, its own mapping and its own rating downstream.
- **Why I didn't act:** out of scope for #266, and rewording the Task line to
  dodge it would hide the defect. Run 2 happens not to reproduce it, but the
  inputs differed, so run 2 is not evidence of a fix.
- **Drafted fix:** file as a child of **#181**, `bug` / `track:checker`:

  > **Title:** An inferred obligation restating an explicit one is not reconciled with it
  >
  > From #266's Gate 1 (`dogfood-logs/266-gate1-run1/`), decomposing a task
  > file whose Task line summarises what its constraints then specify:
  >
  > | source | id | text | flag |
  > |---|---|---|---|
  > | `task-01` | `no-test-can-evidence-criterion-statement-supported` | A criterion may be answered with a statement that no test can evidence it. | inferred |
  > | `constraint-01` | `recommendation-may-state-no-test-can-evidence` | A test recommendation may state that no test can evidence its criterion. | explicit |
  >
  > One demand, two obligations. In the same run the decomposer *did* link two
  > other `task-01` obligations onward — both render `(also serves
  > constraint-03)` / `(also serves constraint-07)` — so the many-to-many
  > machinery worked on the same requirement in the same response and missed
  > this pair. That narrows it: not a stage that failed to run, a similarity
  > judgement that came back negative on a pair a reader calls identical.
  >
  > Worth separating from #223, which is a **spurious** link — an obligation
  > attached to a requirement it does not belong to. This is the dual: a link
  > that should exist and does not, leaving a redundant obligation rather than
  > a misplaced one.
  >
  > #259's embedding-distance gate is the obvious place to look, since the two
  > descriptions should sit well inside a 0.10 cosine distance. Whether the
  > pair was excluded by distance before the model ever saw it, or was sent and
  > judged distinct, is the first thing to establish — the two have different
  > fixes and the recorded linking transcript distinguishes them.
  >
  > Suggested acceptance: two obligations stating the same demand, one derived
  > from a headline requirement and one from the constraint that specifies it,
  > are reconciled into one obligation serving both requirements.
- **Status:** filed (#268, sub-issue of #181)

### [2026-08-13] #245 takes down a whole Gate 2 — nine twin-splits in one run, and one in the mirror direction
- **Kind:** filing (comment on existing issue #245)
- **Found during:** #266, Gate 2
- **Where:** `dogfood-logs/266-gate2-run1/`
- **Severity:** blocker (for #266's gate; the defect itself is #245's)
- **What's wrong:** every one of the nine obligations rated `unsupported` in
  #266's Gate 2 has an on-point test that the mapping stage **saw and assigned to
  its twin**. Nine instances in a single run, where #245 was filed on one. One of
  them splits in the direction #245's title does not describe: the test was
  mapped to the *completion* twin and the *constraint* got nothing.
- **Why I didn't act:** the tests exist and discriminate — three of them were
  confirmed by defect injection. There is nothing to add and no wording to fix;
  the fix is in `evidence/mapping.py`, which is #245's scope, not #266's.
- **Drafted fix:** comment on **#245**:

  > **Nine instances in one run, and the split runs both directions.**
  >
  > #266's Gate 2 (`dogfood-logs/266-gate2-run1/`, base `265bfac`, head
  > `28f2e2d`) came back `INCOMPLETE` with 9 of 30 obligations `unsupported` and
  > `(no mapped test)`. All nine are this defect. Read off the recorded
  > `_Mappings` transcripts — 118 candidate tests offered, 17 of them the
  > change's own:
  >
  > | starved obligation | on-point test | mapped instead to |
  > |---|---|---|
  > | `test-review-does-not-abort-on-no-test-can-evidence-statement` (completion-02) | `test_a_declined_obligation_does_not_abort_the_review` | constraint-01 |
  > | `test-omitted-criterion-still-aborts-review` (completion-03) | `test_an_omitted_obligation_still_aborts_even_when_others_are_declined` | constraint-04 |
  > | `test-statement-attributed-to-criterion-in-persisted-state` (completion-04) | `test_the_refusal_reaches_review_state_attributed_to_its_obligation` | constraint-05, constraint-06 |
  > | `test-all-weak-criteria-answered-that-way-produce-report` (completion-05) | `test_a_config_only_change_produces_a_report` | constraint-11, task-01 |
  > | `test-report-omits-no-test-can-evidence-statement-for-no-recommendation` (completion-08) | `test_the_report_says_no_such_thing_for_an_obligation_that_merely_lacks_one` | constraint-10 |
  > | `no-test-evidence-statement-carries-reason` (constraint-02) | `test_a_declined_obligation_does_not_abort_the_review` | constraint-01 only |
  > | `no-test-evidence-statement-does-not-abort-review` (constraint-03) | same test | constraint-01 only |
  > | `weak-criteria-all-statement-produces-report` (constraint-07) | `test_a_review_of_only_declined_obligations_is_unable_to_determine` | task-01 only |
  > | `addressed-criterion-indeterminate-on-test-evidence-axis` (constraint-08) | `test_a_declined_obligation_is_indeterminate_on_the_evidence_axis` | **completion-06** |
  >
  > Two things this run adds.
  >
  > **The split runs the other way too.** The last row maps the test to the
  > *completion* twin and starves the *constraint*. This issue's title says a
  > Completion expectation is split from its Constraint twin, which reads as one
  > direction; the stage picks exactly one of the pair, and which one is not
  > predictable. Worth widening the title or the acceptance to say so.
  >
  > **Superseded before filing.** The comment actually posted covers all five
  > Gate 2 runs, because the cause was found and largely fixed inside #266:
  > the instruction, not the mechanism, and 9 instances down to 1.
  >
  > **The blast radius is a whole gate, not a rating.** Nine of thirty
  > obligations, every one of them `addressed` in code with a test that exists
  > and discriminates — three were confirmed by defect injection. The review is
  > not wrong about the work; it is wrong about which obligation each test
  > belongs to, and that alone is enough to fail a gate outright.
  >
  > **Ruled out, so nobody re-derives it.** 93 of 118 mapping entries have empty
  > `obligation_ids`, which looks like DR-164's shed-work signature and is not:
  > an entry is per candidate test, and almost none of this repo's ~1,100 tests
  > bear on the mandate, so empty is the correct answer for them. Every
  > `_Mappings` call in the run also recorded `stop_reason: stop` — no truncation.
- **Status:** filed (comment on #245). Rewritten before posting to cover all five
  Gate 2 runs rather than run 1 alone: the cause is the instruction rather than
  the mechanism, the first fix overcorrected into over-mapping, and the second
  took it from 9 instances to 1.

### [2026-08-13] #225: seven ratings moved between two runs one commit apart, three of them on untouched scope exclusions
- **Kind:** filing (comment on existing issue #225)
- **Found during:** #266, Gate 2 run 3
- **Where:** `dogfood-logs/266-gate2-run3/output.log`, the `Changes since b55eef5a` section
- **Severity:** blocker (it is what stops #266 reaching a clean gate)
- **What's wrong:** the tool's own delta section reports seven obligations
  falling between two heads one commit apart. Three are **scope exclusions**
  nothing in that commit touched. One fell from `strongly supported` to
  `unsupported` in the very commit that added a dedicated test for it.
- **Why I didn't act:** not fixable inside #266 and not fixable by iterating —
  three runs produced 9, then 2, then 5 findings, with the movement uncorrelated
  with the work.
- **Drafted fix:** comment on **#225**:

  > **Seven movements between two heads one commit apart, computed by the tool itself.**
  >
  > From #266's Gate 2 (`dogfood-logs/266-gate2-run3/`), base `265bfac`, heads
  > `b55eef5` → `95efe1e`. This is the tool's own `Changes since` section, not a
  > reconstruction:
  >
  > ```
  > closed:
  >   A statement that no test can evidence a criterion carries a reason.
  >       test evidence: nominally supported -> strongly supported
  > moved:
  >   ...two runs produce the same statements    strongly -> partially
  >   ...a test bearing on several criteria      strongly -> partially
  >   ...every weak criterion answered           strongly -> UNSUPPORTED
  >   ...two runs, same statements (constraint)  strongly -> partially
  >   ...code-alone exclusion unchanged          strongly -> UNSUPPORTED
  >   ...request size unchanged                  strongly -> partially
  >   ...non-test evidence not recommended       strongly -> partially
  > ```
  >
  > Two things make this a stronger instance than the earlier ones.
  >
  > **Three of the seven are scope exclusions** — obligations of the form "the
  > change does not alter X". The commit between the two heads touched none of
  > them, and by construction a scope exclusion's evidence is the *absence* of
  > work, so there is nothing for added tests to have perturbed.
  >
  > **One moved against the direction of the work.** *"A review in which every
  > weak criterion is answered with a statement that no test can evidence it
  > produces a report"* fell from `strongly supported` to `unsupported` in the
  > commit that added `test_every_weak_obligation_declined_still_returns_a_result`,
  > a test whose entire subject is that obligation and which carries the
  > omission contrast that makes it discriminating.
  >
  > The `closed` line shows the same run correctly recognising a fix landing, so
  > the delta machinery is working; it is the ratings underneath that are moving.
- **Status:** filed (comment on #225, rewritten with the #266 filtering caveat)

### [2026-08-19] An obligation true by construction earns a test for a defect that cannot exist
- **Kind:** filing (new issue, child of #183)
- **Found during:** #266, Gate 2 runs 4 and 5
- **Where:** `dogfood-logs/266-gate2-run4/output.log`, obligation 20
- **Severity:** should-fix
- **What's wrong:** `constraint-03` of #266's mandate is unfalsifiable once
  `constraint-02` enumerates four values — the field is one enum, so "both
  required and not required" is unrepresentable. Run 4 rated it `partially
  supported` and prescribed a test whose `detects` names *"two redundant internal
  flags"*, an implementation that does not exist. Run 5 rated the same obligation
  `strongly supported`. Neither run recognised the kind of statement it was.
- **Why I didn't act:** the tautology was kept deliberately, on the human's
  instruction, as an experiment to see how the tool handles one. Fixing the tool
  is outside #266.
- **Drafted fix:** filed as a child of #183 — see the issue for the full text.
- **Status:** filed (#270, sub-issue of #183)

### [2026-08-19] Context stated as current behaviour becomes an obligation to preserve it
- **Kind:** filing
- **Found during:** #269, Gate 1 run 1
- **Where:** `src/acceptance/requirement/obligations.py`
- **Severity:** should-fix
- **What's wrong:** the `## Task` section described current behaviour in the
  present tense — what the tool does today and why it is wrong. Two of the five
  obligations derived from it require that behaviour to *continue*:
  `rerun-rederive-from-scratch` (*"Decomposition is re-derived from scratch on
  every run, and a changed task invalidates everything…"*) and
  `criterion-wording-churn-across-runs` (*"…criterion wording churn occurs, with
  identifiers re-minted alongside the wordings"*). Both are satisfied by **not
  doing the task**, so a correct implementation is scored as failing them. Three
  more turned completed measurements into obligations
  (`criterion-churn-preserves-content`, `not-model-nondeterminism`,
  `task-text-is-prompt-for-later-stages`). Evidence:
  `dogfood-logs/269-gate1-run1/`, with `269-gate1-run2/` showing all five gone
  after the narrative was trimmed.
- **Why I didn't act:** it is in `requirement/`, and #269 delivers carry-forward,
  not the derivation prompt.
- **Drafted fix:** **not a new issue — this is #212**, *"Task files cannot
  distinguish context from requirements, so background becomes an obligation"*,
  and the resolution is the `## Context` section that issue already proposes.
  #212 already names the inverted form — *"an obligation to preserve the thing
  being removed"* — from #202's Gate 1, so this is a **reproduction on a second
  mandate**, not a new dimension. Post as a **comment on #212** on that basis:
  it moves the evidence from three runs of one task file to two task files 
  written eight months apart, which is what distinguishes a house-style artifact 
  from a property of the format. Two details worth adding: the three
  measurement-derived obligations show the same failure for *completed
  measurements*, not just problem statements, and trimming the narrative removed
  all five — so a Context section parsed but not decomposed would have sufficed
  here, which is direct support for Deliverable 4.
- **Status:** filed (comment on #212)

### [2026-08-19] A scope exclusion is derived as a prohibition on behaviour that must keep working
- **Kind:** filing
- **Found during:** #269, Gate 1 run 2
- **Where:** `src/acceptance/requirement/obligations.py`
- **Severity:** should-fix
- **What's wrong:** `exclusion-03` says prior-review selection for stages other
  than decomposition — which `rerun.py::find_prior_review` performs over git
  ancestry — is out of scope, i.e. this change leaves it alone. The derived
  obligation reads *"The change does not perform prior-review selection for
  stages other than decomposition via `rerun.py::find_prior_review` over git
  ancestry"*, which as an obligation on the delivered system forbids behaviour
  that exists today and must keep working. The contrast is in the same run:
  `exclusion-02` was reframed positively and correctly, as *"The continued run is
  named only by its identifier."* Evidence: `dogfood-logs/269-gate1-run2/`.
- **Why I didn't act:** `requirement/`, outside #269's area, and the exclusion is
  correctly worded — this is not a task-file fix.
- **Drafted fix:** file as a child of **#181**, and cross-reference **#262**,
  which is the same inversion reached through a constraint rather than a scope
  exclusion — worth checking whether one fix covers both before either is
  scheduled. Acceptance: a scope exclusion naming existing behaviour yields an
  obligation that permits that behaviour to continue, or no obligation at all,
  never one prohibiting it. Labels `bug`, `track:checker`.
- **Status:** filed (#272, sub-issue of #181)

### [2026-08-19] An explicit obligation restating another explicit obligation is not reconciled with it
- **Kind:** filing
- **Found during:** #269, Gate 1 run 3 (post-#271)
- **Where:** `src/acceptance/requirement/linking.py`
- **Severity:** should-fix
- **What's wrong:** in run 3, `task-01` yielded six obligations and `task-02`
  four. Two are correctly linked — `constraint-01-unchanged-requirement-no-model-call`
  *(also serves constraint-01)* and `every-run-reports-identifier` *(also serves
  constraint-20)*. Six are unlinked restatements:

  | obligation | restates | type |
  |---|---|---|
  | `unchanged-requirement-carries-obligations` | `constraint-02`/`-03` | inferred |
  | `edited-requirement-rederived-from-old-and-new-text` | `constraint-04` | explicit |
  | `new-requirement-derived-fresh` | `constraint-08` | explicit |
  | `disappeared-requirement-drops-obligations` | `constraint-06` | explicit |
  | `run-records-derived-work` | `task-02` prose | inferred |
  | `later-run-can-name-continued-run` | `task-02` prose | inferred |

  The clearest is `disappeared-requirement-drops-obligations` against
  `constraint-06`'s `drop-obligations-for-removed-requirement` — near-identical
  ids, same assertion, no link. The first row is **exactly #268** (an *inferred*
  obligation restating an explicit one). The three explicit-on-explicit rows are
  the same defect on an axis #268 does not cover, which is what makes this a
  separate filing rather than a comment on #268.
- **Why I didn't act:** `linking.py` is outside #269's area. It is a Gate 2
  hazard, not a Gate 1 one — each restatement independently demands evidence.
- **Drafted fix:** file as a child of **#181**, cross-referencing **#268** as the
  inferred-vs-explicit half of the same problem, and say plainly that the
  mechanism works and is under-applied — two links were made in the same run.
  Evidence: `dogfood-logs/269-gate1-run3/`. Acceptance: an obligation restating
  an explicit constraint is linked to it regardless of whether either is inferred
  or explicit. Labels `bug`, `track:checker`.
- **Status:** filed (#273, sub-issue of #181)

### [2026-08-19] A derived obligation dropped the symbol its requirement named
- **Kind:** filing
- **Found during:** #269, Gate 1 runs 2 and 3
- **Where:** `src/acceptance/requirement/obligations.py`
- **Severity:** should-fix
- **What's wrong:** `exclusion-03` names `rerun.py::find_prior_review`. Run 2's
  obligation retained the symbol; run 3's dropped it, leaving *"The change does
  not perform prior-review selection for stages other than decomposition."* The
  task file was byte-identical between the two runs; only the tool changed
  (#271). This is the #193 §3 axis: symbol loss is invisible to both recall and
  precision, because the aligner correctly matches an obligation that dropped its
  symbol to one that kept it — so no set metric will ever report it, and it is
  caught only by reading.
- **Why I didn't act:** `requirement/`, outside #269's area.
- **Drafted fix:** file as a child of **#181**, with the run 2 / run 3 pair as
  the evidence and the note that the two runs differ only in tool version.
  Acceptance: an obligation derived from requirement text naming a symbol retains
  that symbol. Cross-reference #193 §3 as the reason no existing metric catches
  it, and #195's decompose-regression suite as where the assertion belongs.
  Labels `bug`, `track:checker`.
- **Status:** filed (#274, sub-issue of #181)

### [2026-08-19] Scope-exclusion typing flipped in both directions on unchanged requirement text
- **Kind:** filing
- **Found during:** #269, Gate 1 runs 1 and 2
- **Where:** `src/acceptance/requirement/obligations.py`
- **Severity:** should-fix
- **What's wrong:** across three runs, three scope exclusions whose text was
  byte-identical throughout took three different types:

  | requirement | run 1 | run 2 | run 3 (post-#271) |
  |---|---|---|---|
  | `exclusion-01` | `functional` | `human_review` | `regression` |
  | `exclusion-06` | `human_review` | `functional` | `human_review` |
  | `exclusion-07` | `human_review` | `functional` | `human_review` |

  `exclusion-06` and `-07` returned to `human_review` after passing through
  `functional`, so #271 did not settle this. **The caveat that bounds this
  evidence:** no two runs share both a tool version and a surrounding registry —
  runs 1→2 changed the task file's `## Task` section, runs 2→3 changed the tool —
  and the decomposer reads the whole registry as context (#178). This is
  corroborating evidence, **not a controlled measurement**.
- **Why I didn't act:** outside #269's area, and a controlled test (perturb one
  unrelated bullet, hold the tool fixed) is #193/#205's work.
- **Drafted fix:** this is the scope-exclusion typing instability already queued
  against **#205** — post as a **comment on #205** carrying this instance and its
  three-run evidence, rather than filing a duplicate. State the caveat above in
  the comment rather than presenting it as a measurement. Note that #205's
  original instance and this one differ in direction, so the fix must pin the
  type rather than merely exclude `human_review`, and that #271 — which moved the
  evidence decision into decomposition — did not resolve it.
- **Status:** filed (comment on #205)

### [2026-08-19] One requirement yields two obligations stating the same property
- **Kind:** filing
- **Found during:** #275, Gate 1 run 1
- **Where:** `src/acceptance/requirement/obligations.py`
- **Severity:** should-fix
- **What's wrong:** two single-property constraints each produced two
  obligations that differ only in voice. `constraint-07` ("The report states,
  for a criterion whose prescription was not obtained, that no prescription was
  produced for it.") produced `report-no-prescription-produced`
  (`functional`, imperative) and `report-says-no-prescription-produced`
  (`explanation_observability`, the requirement text verbatim). `constraint-12`
  ("A response naming the same criterion more than once is rejected.") produced
  `reject-duplicate-criterion-names` and `duplicate-criterion-rejected`, both
  `error_handling`, and that pair was flagged nowhere. `constraint-08`, the same
  shape of sentence, produced one. Not the twin-across-sections shape of
  #245/#273 and not attributable to task-file wording: one requirement, one
  property, two obligations.
- **Why I didn't act:** `requirement/`, outside #275's area.
- **Drafted fix:** file as a child of **#181**, titled *"One requirement yields
  two obligations stating the same property, differing only in voice"*.
  Body: the two instances above with their ids and types, the `constraint-08`
  counter-example from the same run, and the note that #242's linking policy
  then fails to merge them so the redundancy survives to Gate 2 — where each
  copy independently demands evidence. Distinguish from #273 (restatement
  *across* requirements) and #224 (under-splitting) explicitly. Acceptance: a
  requirement stating one property yields one obligation; #195's
  decompose-regression suite carries a case over this run's breakdown.
  Evidence: `dogfood-logs/275-gate1-run1/`. Labels `bug`, `track:checker`.
- **Status:** filed (#277, sub-issue of #181)

### [2026-08-19] An all-duplicate cluster merged nothing — #242 without a spurious member
- **Kind:** filing (comment)
- **Found during:** #275, Gate 1 run 1
- **Where:** `src/acceptance/requirement/linking.py:382-396`
- **Severity:** should-fix
- **What's wrong:** the unreconciled-cluster message fired over
  `report-states-no-prescription-produced-for-omitted-criterion`,
  `report-no-prescription-produced` and `report-says-no-prescription-produced`.
  In #242's instance an unrelated third member dragged two genuine duplicates
  into an inconsistent cluster. Here **all three are genuine duplicates**, so no
  false-positive link is available to blame — a pair among three synonymous
  obligations was *denied*. Same policy, opposite input: a false negative on a
  true pair, not a false positive on an unrelated one.
- **Why I didn't act:** `requirement/`, outside #275's area, and #242 is open.
- **Drafted fix:** post as a **comment on #242** carrying the message verbatim,
  the three obligations with their source requirements, and the point that the
  all-or-nothing policy is now shown to lose merges in both directions — so a
  fix aimed only at suppressing spurious links would not cover this instance.
  Evidence: `dogfood-logs/275-gate1-run1/`.
- **Status:** filed (comment on #242)

### [2026-08-19] Every `test_demand` twin went unmerged; the three merges are all non-`test_demand`
- **Kind:** filing (comment)
- **Found during:** #275, Gate 1 run 1
- **Where:** `src/acceptance/requirement/linking.py`
- **Severity:** nice-to-have
- **What's wrong:** of nine constraint/completion twin pairs in one run, three
  merged and nine remained. All six completion obligations typed `test_demand`
  are unmerged (6 of 6); completion obligations typed anything else merged 3 of
  6, and all three merges are with a non-`test_demand` twin. One run, so a
  correlation rather than a finding — but it is a mechanical explanation for
  #273's "inconsistent rather than absent", and cheap to test.
- **Why I didn't act:** `requirement/`, outside #275's area; #273 is open and
  is the right home.
- **Drafted fix:** post as a **comment on #273** with the merged/unmerged table
  from this run and the type correlation, stated as a hypothesis to check
  against #269's run-3 breakdown rather than as an established cause.
  Evidence: `dogfood-logs/275-gate1-run1/`.
- **Status:** filed (comment on #273)

### [2026-08-19] `litellm>=1.50` admits 1.97.0, which breaks every live call
- **Kind:** filing
- **Found during:** #275, Gate 1 run 1
- **Where:** `pyproject.toml:12`
- **Severity:** should-fix
- **What's wrong:** a fresh `.venv` in this worktree resolved litellm **1.97.0**
  against pydantic **2.13.4**, and every live call died in litellm's own
  response construction: `` `Message` is not fully defined; you should define all
  referenced types, then call `Message.model_rebuild()` ``, surfaced as
  `APIConnectionError`. The other worktrees hold 1.96.2 and work. `pyproject.toml`
  floors the dependency at `litellm>=1.50` with no ceiling, so every new
  environment picks up the break — and it bites **recording**, which is the first
  thing a new worktree must do. Replay-mode runs and CI are unaffected, which is
  why nothing caught it.
- **Why I didn't act:** the venv pin unblocked #275 (`pip install litellm==1.96.2`);
  editing `pyproject.toml` on this branch would put a dependency change in a
  presentation-fix PR.
- **Drafted fix:** file as a child of **#184**, titled *"A fresh install picks up
  a litellm that cannot make a live call"*. Body: the traceback, the two
  versions, and the point that replay-only CI cannot detect it. Acceptance:
  `pyproject.toml` constrains litellm to a range where a recording run works, and
  something exercises a live-call code path against the installed version — even
  if only a construction-level smoke check that does not call a provider.
  Labels `bug`, `track:checker`.
- **Status:** filed (#278, sub-issue of #184)

### [2026-08-19] No retry when the prescribing stage omits a criterion
- **Kind:** decision
- **Found during:** #275, Gate 1
- **Where:** `src/acceptance/coverage/recommendations.py`
- **Severity:** nice-to-have
- **What's wrong:** nothing on the path retries. #275 makes an omission
  survivable and legible, but the prescription is still lost for that criterion,
  and #275's own evidence (12 of 13 returned, `stop_reason: "stop"`) suggests a
  single re-ask for the missing ids would close most instances. What survives a
  retry is also a far stronger signal than what survives a first call.
- **Why I didn't act:** deliberately excluded from #275's mandate — it is a
  second design question (how many re-asks, what the request key does with a
  second call, how replay records it) and folding it in risks the disposition
  fix that #258 is blocked on.
- **Drafted fix:** **recommendation — file as a follow-up issue under #185**,
  after #275 lands, titled *"Re-ask once for the criteria the prescribing stage
  omitted"*. Acceptance: a bounded re-ask over the missing ids only; a second
  omission is recorded as not-obtained exactly as #275 does; the retry request is
  recorded and replays deterministically. **Alternative rejected:** doing it
  inside #275 — it would expand a fix that unblocks another task, and the
  not-obtained disposition is needed whether or not a retry exists.
- **Status:** filed (#280, sub-issue of #185) — #275 landed as `441c829`

### [2026-08-19] Twenty ratings moved on a test-only change — a controlled #252 pair
- **Kind:** filing (comment)
- **Found during:** #275, Gate 2 runs 1 and 2
- **Where:** `src/acceptance/evidence/strength.py:132-139`,
  `src/acceptance/evidence/discrimination.py`
- **Severity:** should-fix
- **What's wrong:** run 1 rated **20 of 31** obligations `partially supported`
  and run 2 rated **25 strongly supported**, over a **byte-identical source
  diff** — the only change between them is 57 added lines in two test files.
  Three of the twenty had a concrete gap the new tests genuinely close. The other
  seventeen were held down by defects no test can kill: *"correctly marks the
  tested omission case indeterminate, but mishandles a different omitted
  criterion elsewhere"*, *"rejects unasked criteria in general, but the specific
  test input is accidentally treated as asked"* — restatements of "your test only
  covers what it covers". Under `caught == total` a single unkillable entry caps
  the rating permanently, so those seventeen should not have cleared, and they
  did. The unrequested-change list moved the same way over the same diff: 7
  entries with one `risky` in run 1, 2 entries both `in_service` in run 2.
- **Why I didn't act:** `evidence/`, outside #275's area, and #252 owns the
  mechanism.
- **Drafted fix:** post as a **comment on #252**. #252 owns the permissive
  direction — a lazily enumerated defect list buying `strongly_supported`; this
  is the strict direction of the same arithmetic, and the pair shows the rating
  tracking the *volume* of test material rather than the gaps named. Say plainly
  that this is an unusually controlled instance: same tool version, same task
  file, same source diff, one variable. Evidence:
  `dogfood-logs/275-gate2-run1/` and `-run2/`, with both judgements. Cross-ref
  #180 (instability) and #250 (run 1 prescribes the test it already cites as
  that obligation's evidence, in obligation 1).
- **Status:** filed (comment on #252)


### [2026-08-19] The whole-review abort on a skipped recommendation survives #271 — FIXED by #279
- **Kind:** filing
- **Found during:** #269, Gate 2 run 3
- **Where:** `src/acceptance/coverage/recommendations.py:196`
- **Severity:** ~~blocker~~ — **resolved before filing**
- **Resolution:** **#279** (*Record an omitted recommendation instead of
  abandoning the review*) landed on `main` and fixes exactly this. Gate 2 run 4,
  rebased onto it, renders the full report. **Do not file** — kept here as the
  record of how it was found and confirmed fixed.
- **What's wrong:** the review aborts before rendering with *"no recommendation
  for 2 of 49 weak obligation(s): carry-forward-unchanged-merge-decisions,
  reask-merge-decision-when-either-obligation-changed"*. **No report exists**, so
  Gate 2 cannot be assessed at all — not clean, not unclean, unknown. 47 answered
  obligations, every coverage finding and the verdict are all destroyed by two
  skipped recommendations. Deterministic: reproduced identically on a replay
  re-run.

  This is the defect #258 was blocked on for a week and that **#271 landed to
  close (#266)**. The comment #271 wrote directly above the raise states the
  reasoning that was supposed to make it unreachable — *"Every obligation
  reaching here requires test evidence, decided at decomposition. So silence is
  once again the only thing this has to reject — there is no correct reason for
  the model to skip one"*. The premise may be right; the conclusion does not
  hold, because the model skipped two anyway.

  Not a hard threshold: runs 1 and 2 of the same gate rendered at 44 and 49 weak
  obligations. That restates #258's transcript finding — partitioning does not fix
  this, it only shrinks how much each abort destroys.
- **Why I didn't act:** `coverage/` is outside #269's area, and fixing the
  recommender inside this branch would be a second delivery hiding in one PR.
- **Drafted fix:** file as a child of **#185**, referencing #266 and #271 as the
  prior attempt and #258 as the earlier victim. The design question to settle in
  the issue: a skipped recommendation should degrade **that obligation** to "no
  recommendation available", not destroy the report — the current rule treats an
  incomplete answer as no answer, which is right for a disposition covering the
  mandate (M1.2.r2) and wrong for an advisory prescription attached to one
  obligation. Acceptance: a response that omits a recommendation for one weak
  obligation still produces a report, that obligation is marked as carrying no
  recommendation, and the omission is reported rather than silent. Labels `bug`,
  `track:checker`. Evidence: `dogfood-logs/269-gate2-run3/`.
- **Status:** closed — #279 landed the same fix independently. Nothing to file.

### [2026-08-19] Adding tests made 33 obligations worse — ratings degrade on a re-judgement
- **Kind:** filing
- **Found during:** #269, Gate 2 runs 4 and 5 (supersedes the run 2/3 draft below)
- **Where:** `src/acceptance/evidence/strength.py`, and the re-judgement path in
  `rerun.py` / `pipeline.py`
- **Severity:** blocker
- **What's wrong:** run 5 differs from run 4 by one commit that **adds nine tests
  and changes no source file**. The ratings moved like this:

  | rating | run 4 | run 5 |
  |---|---|---|
  | strongly supported | **37** | **4** |
  | partially supported | 3 | 48 |
  | nominally supported | 8 | 0 |
  | unsupported | 4 | 0 |

  **33 obligations got worse because evidence was added.** The cleanest instance
  is `unchanged-task-file-no-decompose-call`, where run 5 cites a strict
  **superset** of run 4's tests — the same on-point test plus two more — and drops
  from `strongly supported` to `partially supported`. The report's own delta
  section spells it out: `Changes since 2276c135:` is line after line of
  `test evidence: strongly supported -> partially supported`.

  Run 5 is an incremental re-run — `find_prior_review` selected run 4's review and
  re-judged what the change could affect. Nearly every obligation cites
  `tests/requirement/test_carry_forward.py`, so nearly every obligation was
  re-judged, and nearly every re-judgement came back a tier lower. Whether the
  cause is the re-judgement path or the strength judge being harsher on a second
  look is the question the issue has to settle; the observable fact is that a
  rating is currently a function of **how many times an obligation has been
  looked at**, not only of the evidence under it.

  This bounds what any Gate 2 verdict in this repository is worth right now, which
  is why it is a blocker rather than a should-fix.
- **Severity note:** raised from should-fix after run 5. The run 2/3 instance
  below is the same defect at two obligations, where it could still be argued as
  noise.
- **What's wrong:** `carry-forward-unchanged-merge-decisions` and
  `reask-merge-decision-when-either-obligation-changed` were both
  **`strongly supported`** in Gate 2 run 2, each citing two tests. One commit
  later, in run 3, both are not-strongly-supported — `weak` is defined as exactly
  that (`recommendations.py:139-142`), and their appearance in the weak set is
  what triggers the abort filed above.

  **Their evidence did not move.** The run-3 commit (`7fc842d`) touched
  `requirement/obligations.py` and appended two tests to
  `tests/requirement/test_carry_forward.py`. It did not touch
  `requirement/linking.py`, which is the code these two obligations are about,
  and it did not touch any of the four tests they cited in run 2 — all of which
  still exist and still pass (1186 passing). The obligation text is identical in
  both runs.

  So a rating moved while the code under review, the obligation text and the
  cited tests all stood still. What moved is unrelated content elsewhere in the
  same diff and the same test file.
- **Why I didn't act:** `evidence/` is outside #269's area, and no amount of test
  writing inside #269 can fix a rating that moves for reasons unrelated to tests.
- **Drafted fix:** file as a child of **#183**, cross-referencing **#251** (*a
  criterion is re-judged only when its own inputs changed, and a changed rating
  names the change*) — #251 is very close to being the fix, so check whether this
  belongs as evidence on it rather than as a new issue. Acceptance, in two parts
  because the run 4/5 pair separates them: (1) an obligation whose cited tests are
  a superset of a prior run's, with unchanged obligation text, does not receive a
  lower rating than that run gave it; (2) a rating that changes between two runs
  names what changed, per #251. Evidence: `dogfood-logs/269-gate2-run4/` and
  `-run5/` for the 37→4 collapse, `-run2/` and `-run3/` for the earlier
  two-obligation instance. Labels `bug`, `track:checker`.
- **Status:** filed (comment on #251). No separate issue: #251 already describes
  this defect and cites two smaller instances of it, so splitting it off would
  divide the evidence for one fix across two places.

### [2026-08-19] Are the measurement harness's model calls in scope for per-stage cost attribution?
- **Kind:** decision
- **Found during:** #264, Gate 1
- **Where:** `benchmark/instability.py:356`, `benchmark/alignment.py:77`
- **Severity:** should-fix
- **What's wrong:** #264's Acceptance says *"No call site reports as `unknown`"*,
  and the issue body counts benchmark's call sites among those that would. But
  CLAUDE.md's repo layout states plainly that `benchmark/` **is not part of a
  review run**, and the thing #264 builds is a per-run, per-stage cost footer for
  a review. Counting harness calls into a review run's footer would attribute
  spend to a run that did not make it.

  The exact inventory, walked today: **13** `.complete(` call sites, not the 14
  the issue body claims. One of the 13 —
  `benchmark/instability.py:262` — is a subclass override forwarding
  `super().complete(..., stage)`, not an originating call. Of the remaining 12,
  **10 are on the product path** and **2 are in `benchmark/`**. Three of the 10
  already pass `stage=` (`evidence/mapping.py:174`, `requirement/linking.py:520`,
  `requirement/obligations.py:877`), leaving **7 product-path sites to fix**.
  `evidence/discrimination.py:159` does **not** pass it, contrary to the issue body.
- **Why I didn't act:** resolving it silently would decide what the Acceptance
  means. It changes what the enforcement test asserts, so it has to be settled
  before that test is written.
- **Drafted fix:** **Recommendation — exclude `benchmark/`.** Scope the
  enforcement test to `src/acceptance/` minus `benchmark/`, so it fails when any
  of the 10 product-path sites omits `stage=`, and leave the harness's 2 alone.
  Rationale: the footer reports what a *review* cost, and the harness is a
  separate program that happens to share the client. `current-task.md` carries
  this as a scope exclusion (*"Model calls issued by the measurement harness,
  which is not part of a review run"*), so approving this is approving the task
  file as decomposed.

  **Resolved 2026-08-19 (human): exclude `benchmark/`.** The enforcement test
  scopes to `src/acceptance/` minus `benchmark/`, over the 10 product-path sites.

  **Alternative rejected:** pass `stage=` at all 12 sites so `unknown` never
  appears anywhere. It reads truer to the Acceptance's literal wording and costs
  two extra keyword arguments, but it puts harness spend into a review run's
  footer unless the aggregation then filters it back out — which is the same
  decision, made twice and in a place where it is easy to get wrong.
- **Status:** resolved (excluded — human decision, 2026-08-19); implemented in #264

### [2026-08-19] #278 is narrower than filed: 1.93.0 cannot be installed fresh either
- **Kind:** filing (comment on existing issue #278)
- **Found during:** #264, environment setup before Gate 1
- **Where:** `pyproject.toml:12`
- **Severity:** should-fix
- **What's wrong:** #278 reproduced today in a new worktree — a fresh
  `pip install -e ".[dev]"` resolved **litellm 1.97.0** and every live call died
  as described there. Two facts the issue does not yet carry:

  1. **The root cause, precisely.** Rebuilding the model by hand gives
     `PydanticUndefinedAnnotation: name 'ChatCompletionReasoningSummaryTextBlock'
     is not defined`. That type **is** defined, in litellm's own
     `litellm/types/llms/openai.py:526`, but `litellm/types/utils.py` annotates
     `Message` with it as a string under a `TYPE_CHECKING` import, so pydantic
     cannot resolve it at runtime. It is a litellm packaging bug, not a
     version-skew problem with `openai` or `pydantic`.
  2. **Pinning *down* is not a workaround in a fresh environment.**
     `pip install litellm==1.93.0` fails: pip selects the **sdist**
     (`litellm-1.93.0.tar.gz`) rather than a wheel, and the source build needs a
     Rust toolchain it then tries to download —
     `PermissionError: ... puccinialin/rustup-init/rustup-init.lock`. So the
     acceptable range is bounded on *both* sides, and #278's Acceptance should
     say which versions actually install *and* work. **1.96.2 is the only version
     confirmed good** (by #275, and by the pre-existing venvs).
- **Why I didn't act:** `pyproject.toml` is outside #264's area, and #278 already
  owns the fix. Unblocked instead by cloning the working `.venv` into the
  worktree and re-pointing its editable path file at the worktree's `src` — worth
  recording as the escape hatch, since `pip install -e .` cannot rebuild the
  environment while this is open.
- **Drafted fix:** comment on **#278** with the two points above. No new issue.
- **Status:** filed (comment on #278)

### [2026-08-20] #251 on a pair whose test file is byte-identical — three ratings fell with no source change at all
- **Kind:** filing (comment on existing issue #251)
- **Found during:** #264, Gate 2 (runs 1 and 2)
- **Where:** `evidence/mapping.py` — the mapping half, so #182 as much as #251
- **Severity:** blocker (it is what keeps Gate 2 from ever coming back clean)
- **What's wrong:** between the two runs, three obligations went
  `strongly supported -> unsupported` and lost **every** mapped test, while:

  - the intervening commit (`23cf2e7`) touched exactly two files,
    `tests/support.py` and `tests/test_stage_attribution.py` (`git show --stat`);
  - **no source file changed** — not one line under `src/`;
  - **`tests/test_usage.py` is byte-identical between the two heads**, and it is
    the file holding the tests that were cited and then were not.

  | obligation | cited in run 1 | cited in run 2 |
  |---|---|---|
  | `no-finer-than-stage-cost-attribution` | `test_usage.py::test_each_stage_is_accounted_for_separately_and_in_a_stable_order` | (no mapped test) |
  | `stage-attributed-run-cost` | same test | (no mapped test) |
  | `model-call-stage-usage-cost-cache-recording` | `test_usage.py::test_usage_details_are_read_from_a_mapping_too` | (no mapped test) |

  This is a tighter instance than the #269 pair already on #251: there the diff
  had grown in several places, so "the mapping saw a different diff" was an
  available explanation. Here the file carrying the lost tests did not change by
  a single byte, and neither did the code under review or the obligation text.

  **A mechanism worth checking, offered as a hypothesis.** #264's own footer —
  the thing this task built — instruments the stage that failed, and it shows
  mapping issuing **14 live calls in run 1** and **15 calls in run 2, of which
  only 3 were live**. So the added test file moved *partition boundaries*, and
  the three re-asked partitions answered differently from the recordings the
  other twelve replayed. That is DR-164 territory and would explain why the
  losses cluster on three obligations rather than scattering. Not verified:
  reading the two runs' mapping transcripts side by side would settle it.
- **Why I didn't act:** `evidence/mapping.py` is outside #264's area, and the
  gate's own rule forbids the only alternative — chasing the rating by writing
  more tests, which is what made #269's run 5 worse.
- **Drafted fix:** comment on **#251**, cross-referencing **#182**, with the
  table above, the `git show --stat` output, and the partition-count hypothesis
  flagged as unverified. Evidence: `dogfood-logs/264-gate2-run1/` and `-run2/`,
  which carry both `revisions.txt` files, so the pair is reproducible. No new
  issue — #251 already describes this defect and this is its cleanest instance,
  so splitting it off would divide the evidence for one fix.
- **Status:** filed (comment on #251)

### [2026-08-19] The Gate 1 procedure never passes `--continue`, so every gate re-run pays churn #269 already removes
- **Kind:** defect (documentation)
- **Found during:** #251, Gate 1 runs 2, 3 and 4
- **Where:** `CLAUDE.md`, *Dogfooding — the review gates*, Gate 1 step 1
- **Severity:** nice-to-have
- **What's wrong:** runs 2 and 3 differ by one bullet in `## Scope exclusions`,
  reworded from *"Partitioning the evidence-judgement request so that one
  criterion's request carries no other criterion's tests"* to *"Partitioning the
  evidence-judgement request per criterion"*. Four requirement pairs that were
  **not** touched inverted whether they merged:

  | pair | run 2 | run 3 | run 4 (`--continue` run 2) |
  |---|---|---|---|
  | `constraint-16` ↔ `completion-10` | **merged** | not merged | **merged** |
  | `constraint-01` ↔ `completion-02` | not merged | **merged** | not merged |
  | `constraint-02` ↔ `completion-03` | not merged | **merged** | not merged |
  | `constraint-07` ↔ `completion-05` | not merged | **merged** | not merged |

  **The third column is the point.** Runs 1–3 were all made without `--continue`,
  so nothing was carried and #269's machinery never ran (`0 carried, 0 revised` in
  each header). Run 4 replays run 3's task file naming run 2 as the continued run
  — `31 carried, 1 revised, 2 derived`, one decompose call — and reproduces run
  2's merge outcome exactly. `linking.py:482-500` carries a merge decision forward
  whenever both its obligations are unchanged (#269's `constraint-32`), so
  de-duping **is** covered and the stage is stable when the feature is used.

  What is left is that the documented Gate 1 command is
  `decompose --task current-task.md`, with no `--continue`. A gate's second and
  third runs are exactly where stability matters — they exist because the first
  run found something — and they are the runs that discard it.
- **Why I didn't act:** it is a change to `CLAUDE.md`'s gate procedure, which is
  not #251's area and is the human's to approve.
- **Drafted fix:** **no issue.** Add to `CLAUDE.md` Gate 1, step 1: *"On a re-run
  after reworking `current-task.md`, pass `--continue <previous run id>` — the run
  prints the id to continue. Without it nothing is carried forward and the
  obligation set is free to move for reasons unrelated to the rewording."* Note
  that `check` needs the same treatment if it takes the flag. Evidence:
  `dogfood-logs/251-gate1-run2/`, `-run3/`, `-run4/`.
- **Status:** fixed on `main`. `CLAUDE.md` Gate 1 gained the `--continue`
  paragraph with the #251 measurement as its evidence. `check` does take the flag
  — verified with `check --help` — so Gate 2 gained a note too, distinguishing
  `--continue` (carries the obligation set) from the prior *review* that
  `find_prior_review` selects over git ancestry (carries judgements, needs no
  flag).

**Correction:** an earlier version of this entry was a `should-fix` filing against
#181 claiming linking has no carry gate. That was wrong — `linking.py:482-500` is
the gate — and the claim was made without having run the tool with `--continue`.
The finding survives only as the documentation gap above.

### [2026-08-19] #272 gains two instances, and the mechanism is a trailing subordinate clause
- **Kind:** filing (comment on existing issue #272)
- **Found during:** #251, Gate 1 runs 1 and 2
- **Where:** `src/acceptance/requirement/obligations.py`
- **Severity:** should-fix
- **What's wrong:** two more scope exclusions derived as prohibitions on
  behaviour that must keep working, in one mandate, and both isolate the
  mechanism #272 does not yet name:

  | run | exclusion text | derived obligation |
  |---|---|---|
  | 1 | "Selecting which stored earlier state a repeated review continues, **which is done over git ancestry**." | "The change does not select which stored earlier state a repeated review continues **over git ancestry**." |
  | 2 | "Partitioning the evidence-judgement request **so that one criterion's request carries no other criterion's tests**." | "The evidence-judgement request for one criterion **carries no other criterion's tests**." |

  In both, a trailing subordinate clause was promoted into the obligation and the
  main clause's sense was lost. Run 2's is the worse of the two: the mandate
  excludes partitioning, so the request will keep carrying every criterion's
  tests, and the obligation asserts the exact opposite. Deleting the trailing
  clause fixed each one on the next run, which is what identifies the clause as
  the cause. The same shape decomposed **correctly** at #269 Gate 1
  (`dogfood-logs/269-gate1-run3/output.log:228`), so it is intermittent rather
  than systematic.
- **Why I didn't act:** `requirement/`, outside #251's area. Both were worked
  around by rewording the task file, which is the sanctioned Gate 1 fix, but the
  rewording is not the report.
- **Drafted fix:** post as a **comment on #272** with the table above, the #269
  counter-example, and the observation that the fix in both cases was deleting a
  trailing clause — which suggests an acceptance test shaped as *"an exclusion
  with a trailing relative or purpose clause yields an obligation whose sense
  matches the main clause"*. Evidence: `dogfood-logs/251-gate1-run1/` and
  `-run2/`.
- **Status:** filed (comment on #272)

### [2026-08-19] #277 gains an instance where the two obligations are byte-identical, not merely same-voiced
- **Kind:** filing (comment on existing issue #277)
- **Found during:** #251, Gate 1 run 1
- **Where:** `src/acceptance/requirement/obligations.py`
- **Severity:** should-fix
- **What's wrong:** `completion-02` ("A criterion whose requirement text, mapped
  test set and mapped test contents are unchanged keeps its stored rating **and**
  issues no evidence-judgement call") produced
  `criterion-unchanged-keeps-stored-rating` and
  `criterion-unchanged-no-evidence-judgement-call` — two obligations whose
  descriptions are byte-identical to each other and to the whole requirement.
  #277's instances differ in voice; these do not differ at all. It also differs in
  cause: the requirement here genuinely holds two claims, so splitting it is
  right — what is wrong is that neither half's description was narrowed to the
  half it covers, leaving two obligations nothing downstream can tell apart. The
  linking stage then reported it could not reconcile them.
- **Why I didn't act:** `requirement/`, outside #251's area. Fixed for this
  mandate by splitting the expectation into two bullets, which is a task-file fix
  and does not address the tool behaviour.
- **Drafted fix:** post as a **comment on #277** distinguishing the two causes —
  #277's is one property yielding two obligations, this is two properties yielding
  two obligations that are not narrowed to their property — and note that the
  second may be the easier acceptance test to write: *an obligation's description
  is not the whole of its requirement's text when that requirement yielded more
  than one obligation*. Evidence: `dogfood-logs/251-gate1-run1/`.
- **Status:** filed (comment on #277)

### [2026-08-19] #242 gains a third all-duplicate cluster, from a different mandate
- **Kind:** filing (comment on existing issue #242)
- **Found during:** #251, Gate 1 run 3
- **Where:** `src/acceptance/requirement/linking.py`
- **Severity:** should-fix
- **What's wrong:** the unreconciled-cluster message fired over
  `changed-rating-must-name-a-change` (`completion-07`),
  `changed-rating-names-one-given-change` (`constraint-11`) and
  `changed-rating-justifies-itself` (Task prose). All three state one claim — a
  judgement that alters a rating names one of the changes it was given — so, as in
  the #275 instance already queued against #242, there is no spurious third member
  to blame for the inconsistency: a pair among three synonymous obligations was
  denied, and the all-or-nothing policy then merged none of them. Three
  obligations survive to Gate 2 where there is one claim, each independently
  demanding evidence.
- **Why I didn't act:** `linking.py`, outside #251's area.
- **Drafted fix:** post as a **comment on #242** — or fold into the #275 comment
  already queued against it, if that one has not been posted when this is
  approved. Carry the message verbatim and the three obligations with their source
  requirements. Evidence: `dogfood-logs/251-gate1-run3/`.
- **Status:** filed (comment on #242). Posted as its own comment, not folded —
  the #275 one was already up.

### [2026-08-19] `litellm>=1.50` admits 1.97.0, which cannot make a live call at all — ALREADY FILED as #278
- **Kind:** filing (comment on existing issue #278), downgraded from a new filing
- **Where:** `pyproject.toml:12`
- **Found during:** #251, Gate 1
- **Severity:** nice-to-have

**Withdrawn as a new filing.** #278, *"A fresh install picks up a litellm that
cannot make a live call"*, was opened 2026-08-19 from #275's Gate 1 with the same
traceback and the same diagnosis. My instance adds only that #275 recovered with
`litellm==1.96.2` and this worktree with `1.93.0`, both against pydantic 2.13.4 —
worth a one-line comment on #278 confirming a second worktree hit it, and only if
the comment already on that issue does not say so. The original draft follows for
the record.

- **What's wrong:** a fresh `.venv` in this worktree resolved `litellm` to 1.97.0,
  and every `--mode record` call died before reaching the provider:
  `PydanticUserError: 'Message' is not fully defined; you should define all
  referenced types, then call 'Message.model_rebuild()'`, raised inside
  `litellm/types/utils.py` constructing its own `ModelResponse`, and surfaced as
  `APIConnectionError`. litellm 1.97.0 is incompatible with the resolved pydantic
  2.13.4. Pinning `litellm==1.93.0` — the version the primary worktree's venv
  holds — fixed it with no other change. **CI will not catch this**: the suite runs
  in replay mode and never calls `litellm.completion`, so the break is invisible
  until someone records, which is exactly when it is most expensive.
- **Why I didn't act:** changing a dependency floor is a dependency decision and
  touches every environment, not just #251's.
- **Drafted fix:** cap the range in `pyproject.toml` —
  `"litellm>=1.50,<1.97"` — or pin `litellm==1.93.0` outright. My recommendation
  is the cap rather than the pin, so the floor keeps admitting the versions that
  work. Worth a second item either way: a smoke test that constructs a
  `litellm.ModelResponse` and runs in CI, so a resolver moving under us fails
  loudly in replay-mode CI instead of silently at the next record run.
- **Status:** filed (comment on #278). Rewritten before posting: the existing
  comment there concluded that `litellm==1.93.0` *cannot be installed*, on the
  evidence of a `puccinialin/rustup-init.lock` `PermissionError`. That is a
  sandbox denial, not a pip failure — the same command succeeds with the sandbox
  off, and 1.93.0 recorded three `decompose` runs and a live `align_obligations`
  call on this worktree. So the comment is a correction, and 1.93.0 joins 1.96.2
  as a confirmed-good version.

### [2026-08-20] Carry-and-justify becomes a pipeline-wide contract, not a per-stage build
- **Kind:** filing
- **Found during:** #251, Gate 1 — raised by the human after run 4 showed #269's
  pattern covering both decompose stages
- **Where:** `src/acceptance/rerun.py`, `src/acceptance/requirement/carry.py`,
  `src/acceptance/requirement/ledger.py`
- **Severity:** should-fix
- **What's wrong:** #269 established a three-part contract for one stage — work
  from the named prior run, skip any unit whose own inputs are unchanged, and put
  a unit whose inputs moved back in front of the model with the change in hand.
  #251 is the second instance. Seven more model-call stages have nothing of the
  kind, and the whole-pipeline mechanism that does exist — `rerun.py`, M7.5 —
  carries at one coarse granularity: an obligation is stale if any *file* it cites
  was touched (`stale_obligation_ids`). That rule is what produced the 37→4
  collapse recorded on #251. So this is not greenfield: it is replacing one blunt
  predicate with a per-stage contract.

  Where it applies, by stage:

  | stage | unit | its own inputs | applies? |
  |---|---|---|---|
  | decompose derivation | requirement | requirement text | **done (#269)** |
  | linking / merge | obligation pair | both obligations | **done (#269)** |
  | open-question resolution | question | question + diff | yes |
  | test mapping | obligation | obligation + candidate tests | yes — and it is #182 |
  | discrimination | criterion | criterion + mapped tests + their source | **#251** |
  | coverage classification | obligation | obligation + cited hunks | yes |
  | unrequested-change detection | — | the whole diff | **no** |
  | disposition | unrequested change | that change + policy | yes |
  | recommendation | weak obligation | obligation + its evidence | yes |
  | declaration comparison | declaration claim | claim + obligations + evidence | yes |

  Unrequested-change detection is the one genuine exception and `pipeline.py:299`
  already says why: it is a judgement about the change as a whole, so there is no
  unaffected subset. A mandate saying *"every stage"* would put an unsatisfiable
  obligation in front of the tool.
- **Why I didn't act:** it is a plan-level decision about sequencing several
  issues, which is the human's.
- **Drafted fix:** file as a child of **#184** (determinism & reproducibility),
  titled *"Carry-and-justify is one contract every re-run stage implements"*.
  Body: the table above; the statement of the contract in three parts; the point
  that `rerun.py`'s file-level predicate is the current whole-pipeline answer and
  is the measured defect site; and the sequencing — #269 and #251 are instances
  one and two, this issue lifts the primitives out of `requirement/` and each
  remaining stage becomes its own small issue against the extracted contract.

  **Two things the issue must settle rather than assume:**

  1. **Justification does not generalise as cleanly as carry.** `DR-269`
     deliberately refused to show the model its prior answer — *"anchoring bias is
     defeated by not asking"* — while #251's second half shows the stored rating.
     Both are defensible: an evidence class is ordinal, so "it got worse" is a
     claim that can be interrogated, whereas a merge decision is boolean and has
     nothing to justify. Settle whether justification is universal or applies only
     where the output is ordinal.
  2. **Whether this closes into #253 or stands beside it.** #253 is the
     *structural* determinism refactor and explicitly scopes judgement-stability
     behaviour out, to #251 and #254. This is a third axis — incremental re-run
     semantics — and I believe it stands alone, but #253's own "Open" section
     already asks whether it should close into #184, and three overlapping
     determinism issues is one too many.

  Acceptance: the carry contract lives in one stage-agnostic module; #269's two
  stages and #251's consume it rather than each defining it; each remaining stage
  has its own issue naming its unit and its inputs; `rerun.py`'s file-level
  predicate is retired rather than left beside the new one. Labels
  `track:checker`, `decision`.
- **Status:** filed (#286, sub-issue of #184)

### [2026-08-20] The echoed-obligation defect is not a uniform low rate — it concentrates on scope exclusions
- **Kind:** filing
- **Found during:** design discussion on duplicate obligations (no issue in flight)
- **Where:** `src/acceptance/requirement/obligations.py:220` (prompt) vs `:378-384` (schema)
- **Severity:** should-fix
- **What's wrong:** #256 — the open decision to rename `_Yielded`'s two obligation
  fields so their relationship is stated — presents the echoed-head defect as a
  low uniform rate (4 in 1,055 transcripts) with no mechanism. That is why it was
  deferred as unurgent. A scan of the current transcript cache shows the four
  occurrences are not spread out: all four are in **one response**, all four on
  **scope-exclusion** requirements, and in that same response the non-exclusion
  requirements used the two fields correctly.

  > Over the 79 current-schema transcripts in `.acceptance/cache/` — current
  > meaning obligations carried inside their disposition, after #204 — there are
  > 505 yielded dispositions, 469 of them single-obligation:
  >
  > | requirement kind | echoed | total | rate |
  > |---|---|---|---|
  > | scope exclusion | 4 | 102 | 3.9% |
  > | everything else | 0 | 403 | 0.0% |
  >
  > Fisher exact, two-sided: **p = 0.00159**.
  >
  > The single transcript carrying them (`c8f94d48113c…`):
  >
  > ```
  > exclusion-03  n=2 echo=True   exclusion-04  n=2 echo=True
  > exclusion-05  n=2 echo=True   exclusion-06  n=2 echo=True
  > task-01       n=3 echo=False  task-02       n=2 echo=False
  > task-03       n=2 echo=False
  > ```

  **The mechanism is a collision between the prompt and the schema.**
  `_SYSTEM_PROMPT` tells the model that every scope-exclusion bullet "produces
  EXACTLY ONE obligation stating the ABSENCE of the excluded work". The schema
  then offers a required singular `obligation` *and* a `more_obligations` list.
  Told the answer is singular and handed two slots, filling both is a defensible
  reading. The echo fires exactly where the prompt is most emphatic about
  singularity — the opposite of a random low-rate fault.
- **Why I didn't act:** #256 is deferred by design to the next change that already
  forces a re-record of the decompose transcripts, and that sequencing still
  holds. This changes the issue's evidence, not its schedule.
- **Drafted fix:** `add_issue_comment` on **#256** carrying the table, the Fisher
  result, the transcript breakdown, and the prompt/schema collision. Two things
  the comment should say that the issue does not:

  1. **The deferral rationale needs restating.** "No measured urgency: 4
     occurrences in 1,055 transcripts" understates it — the right denominator is
     scope-exclusion dispositions, where the rate is 3.9%, and scope exclusions
     are common in this repo's own mandates.
  2. **The prompt sentence may matter more than the rename.** #256's deliverable
     bundles a field rename with a prompt sentence. The evidence points at the
     "EXACTLY ONE" instruction as the trigger, so the two halves are separable and
     the prompt half is testable on its own.

  Also worth noting on the issue: a paired A/B test is cheap and available — the
  28 cached requests that contain scope exclusions, re-issued under variant
  schemas, about 84 calls, roughly $0.75 — but it is powered only to show an
  effect go to zero, not to measure a halving.
- **Status:** open (approved for filing 2026-08-20)

### [2026-08-20] Decision: derive dispositions and obligations in two passes, instead of encoding "at least one" as head-plus-rest
- **Kind:** decision
- **Found during:** design discussion on duplicate obligations (no issue in flight)
- **Where:** `src/acceptance/requirement/obligations.py` — `_Yielded`, `_Decomposition`, `decompose`
- **Severity:** should-fix
- **What's wrong:** the split of a non-empty obligation list into a required
  `obligation` plus a `more_obligations` list exists solely because OpenAI strict
  mode rejects `minItems`, and it is the sole source of the ambiguity behind #256
  (the field-rename decision) and #248 (the closed bug where an echoed head became
  a second obligation). #256 accepts the encoding and tries to make the ambiguity
  rarer with better field names. The alternative is to remove the need for a
  multi-element schema at the point of derivation.
- **Why I didn't act:** an open design decision that changes a response schema and
  re-records the whole decompose corpus — the human's call, and CLAUDE.md says to
  sequence that cost deliberately.
- **Drafted fix:** file as a child of **#181** (the decomposition-quality
  umbrella), labels `track:checker`, `decision`, titled *"Split derivation into a
  disposition pass and a per-requirement obligation pass"*. Body:

  > **Pass A — disposition.** Batched as today, so the request partitioning from
  > DR-164 is unchanged. Returns exactly one disposition per requirement id and
  > **carries no obligations at all**: `yielded`, `no_obligation` with a reason, or
  > `open_question` with ids.
  >
  > **Pass B — obligations.** Scoped to **one** requirement that Pass A
  > dispositioned `yielded`:
  >
  > ```python
  > class _DerivedObligation(StrictResponseModel):
  >     obligation: _DecomposedObligation   # required, singular — no list
  >     states_further_obligations: bool
  > ```
  >
  > Re-ask while `states_further_obligations` is true, passing the obligations
  > already derived, up to a cap.
  >
  > **Non-emptiness stays structural**, via the required singular field, so #217 —
  > which settled that a `yielded` disposition naming no obligations must be
  > impossible to express rather than caught afterwards — is honoured. But there is
  > no second slot, so #256's ambiguity does not exist, and the scope-exclusion
  > case, where the echo actually concentrates, gets a schema matching the prompt's
  > "EXACTLY ONE" exactly.
  >
  > **Multiplicity becomes an explicit judgement** — a boolean the model is asked —
  > rather than something inferred from how it filled two fields.
  >
  > **What it buys beyond #256:**
  >
  > - **#231 becomes structural.** #231 is the open bug where derived obligations
  >   are not local to their requirement: a two-line edit re-split two untouched
  >   requirements and churned 27 of 33 obligation ids. Pass B's request contains
  >   one requirement, so its request key is a function of that requirement alone.
  >   An edit to requirement 7 cannot re-split requirement 12, because requirement
  >   12's call is byte-identical and replays. #231's symptom is unreachable by
  >   construction.
  > - **#277** — the bug where one requirement yields two obligations stating the
  >   same property in different voices — is less likely when the call is scoped to
  >   one requirement and the default shape is one obligation. Not eliminated; the
  >   model can still answer `states_further_obligations: true` wrongly.
  > - **#298** — where a repeated disposition with renamed ids aborts the entire
  >   review. Split, an unusable Pass B answer is a re-ask of one requirement
  >   rather than a rejected batch.
  > - **#205** — assigning obligation types in a separate pass — composes
  >   naturally.
  >
  > **Costs, stated honestly:**
  >
  > - **Call volume.** 505 yielded dispositions across the current corpus against
  >   79 batched calls — roughly six times as many, about $4.50 to re-record. A
  >   33-requirement mandate goes from about 5 calls to about 35.
  > - **But that cold-start figure overstates the steady state.** Per-requirement
  >   calls are individually cacheable and compose with #269's carry-forward
  >   ledger, so a re-run after a one-bullet edit re-issues one call rather than a
  >   batch. Gate 1 re-runs — the case that matters, since a second run only exists
  >   because the first found something — get cheaper, not dearer.
  > - **Call count becomes input-dependent**, driven by a model boolean. Still
  >   deterministic at temperature 0, but it is a new determinism surface (#184's
  >   umbrella), and hitting the cap must be recorded as an unusable answer, never
  >   silently truncated.
  > - **Two-stage disagreement** — Pass A says `yielded`, Pass B produces nothing
  >   usable — is a new failure mode needing a policy.
  > - Re-records the whole decompose corpus, so sequence it *with* #256 rather than
  >   after it. This change would be the re-record #256 is waiting for, and if it
  >   lands, #256's rename is moot.
  >
  > **Open, to settle in the issue:**
  >
  > 1. **What context Pass B sees.** Locality argues for the requirement alone, but
  >    a bullet's meaning can depend on its section — a `## Scope exclusions`
  >    heading changes the required form entirely. Pass the *structured* section
  >    context, never re-pasted markdown; the never-markdown-as-interchange
  >    invariant applies.
  > 2. **Whether Pass A can be trusted to classify without deriving.** Deciding
  >    "this yields something checkable" may be unreliable without attempting the
  >    derivation, in which case Pass A's `no_obligation` rate could rise. This is
  >    the main risk to measure before committing, and it is cheap to measure:
  >    replay the cached inputs through a disposition-only prompt and compare the
  >    `no_obligation` set against what the current single call produced.
  > 3. **Whether this supersedes #256 or subsumes it.** I believe it supersedes —
  >    the rename mitigates an encoding this removes.
  >
  > **Acceptance:** an empty `yielded` stays impossible to express; no response
  > shape can produce a byte-identical obligation pair inside one requirement;
  > #195's decompose-regression suite passes with obligation ids stable across an
  > edit to an unrelated requirement, which is #231's case; the cap and the
  > two-stage-disagreement paths each have a recorded unusable answer.

  My recommendation: worth doing, but on the strength of #231 (obligation churn
  from unrelated edits) and #298 (one bad disposition aborting a review) rather
  than #256. The duplicate-obligation cases actually blocking work — #277, #242
  and the instance recorded on #277 from #251's Gate 1 — are untouched by either
  this or the rename, and #242 is what #292's Gate 2 is stuck behind.
- **Status:** **CLOSED, resolved against, 2026-08-29.** Approved at #317's Gate 1.
  Pass B as drafted here is a call scoped to **one** requirement with a free-text
  quotation, and `docs/experiments/317-over-answering/findings.md` §7 measures
  that as the corpus's worst-performing shape: of the four recorded calls asking
  about a single `task-*` requirement, three return an obligation quoting a
  requirement they were not asked about, and the two largest instances anywhere
  are of exactly this form. #317 takes the per-requirement call but pairs it with
  a quotation restricted to that requirement's own spans, which is the version
  that works. "At least one obligation" then needs no encoding at all: one
  requirement, one required field.

### [2026-08-20] Decomposition has not raised an open question since #217, because `yielded` and `open_question` are mutually exclusive
- **Kind:** filing
- **Found during:** design discussion (no issue in flight)
- **Where:** `src/acceptance/requirement/obligations.py:352-431` (`_Yielded` / `_RaisedOpenQuestion`), `:1103` (`_in_registry_order`)
- **Severity:** blocker
- **What's wrong:** the decomposer has produced **zero** open questions since
  2026-08-06 and has never once chosen the `open_question` disposition.

  > Decompose transcripts in `.acceptance/cache/`, by recording date:
  >
  > | window | calls | open questions |
  > |---|---|---|
  > | 2026-07-21 … 2026-08-05 | 87 | 74 |
  > | 2026-08-06 … 2026-08-20 | 96 | **0** |
  >
  > Every disposition ever returned, across the whole cache (1,109):
  > `yielded` 1020, `no_obligation` 89, `open_question` **0**.

  Two commits on the boundary cause it:

  1. **#202 (`95a3856`, Aug 5)** — open questions used to flow straight from the
     response into `Decomposition`. Now they survive only if a disposition names
     them, and `_in_registry_order` silently drops any that nothing references.
  2. **#217 (`1c71535`, Aug 6)** — the dispositions became a mutually exclusive
     union. `_Yielded` carries no open-question field, so raising a question
     costs the requirement's whole obligation set.

  The prompt then settles the choice every time: `yielded` "should be the large
  majority", `no_obligation` is narrowed to bare section markers, and REFERENCES
  YOU CANNOT RESOLVE steers ambiguity back into `yielded`. A requirement that
  both yields obligations and is materially ambiguous has no way to say so.

  **The store already supports what the response schema forbids.**
  `review_state.py:379-380` gives `RequirementDisposition` independent
  `obligation_ids` and `open_question_ids` lists. #217 narrowed the wire below
  the store it writes into.

  **This contradicts a standing invariant.** CLAUDE.md: *"Uncertainty is
  first-class. `Indeterminate` and open-question outputs are valid, expected
  results — don't force a confident verdict."* The schema forces it.

  #217's stated goal was making a *self-contradictory* disposition
  unrepresentable — a `yielded` naming no obligations. Making "yielded AND
  uncertain" unrepresentable appears to be collateral; I did not find it argued
  in the commit or the module docstring, and the #217 issue should be checked
  before the filing asserts intent.

  **Confound considered and rejected as the main cause:** task-file wording has
  genuinely improved over the same period. But the cut is abrupt across one day
  rather than gradual, and the disposition has been chosen zero times — including
  on Aug 5 transcripts where the model still raised 6 questions through the old
  flat path. Better inputs produce fewer questions, not a categorical zero.
- **Why I didn't act:** it changes a response schema and re-records the decompose
  corpus, and it touches #217's settled design — the human's call.
- **Drafted fix:** file as a child of **#181**, labels `bug`, `track:checker`,
  titled *"Decomposition cannot raise an open question about a requirement that
  also yields obligations, and has raised none since #217"*. Body: the tables
  above, the two commits, the store/wire mismatch, and the invariant collision.

  Candidate directions, not settled:

  - Add `open_question_ids: list[str]` to `_Yielded`, so a requirement can yield
    and still flag an ambiguity. Smallest change; matches the store; does not
    reopen #217, whose invariant is about the obligation set being non-empty, not
    about questions.
  - Keep the union and add a fourth `yielded_with_question` shape. More explicit,
    but a fourth shape is what #217 removed and the name invites confusion.
  - Leave the schema and fix the prompt. Cheapest, but the evidence says the
    schema decides this — the model is choosing rationally given the trade.

  My recommendation: the first. Acceptance: a requirement can carry both
  obligations and open questions in one disposition; an unreferenced open
  question is a rejected response rather than a silent drop; #195's
  decompose-regression suite gains a case over a task file with a genuine
  ambiguity inside an otherwise-yielding requirement.

  Sequence with **#113** (questions dropped downstream and never gating the
  verdict) — fixing derivation alone would produce questions that still do not
  reach the verdict.
- **Status:** filed (#303, sub-issue of #181). Filed on the human's direct
  instruction rather than at a gate. Direction settled by them: make open
  questions compatible with obligations, i.e. the first candidate above.
  #217's own deliverable confirms the mutual exclusivity was never intended —
  it constrained each arm's own field to be non-empty and never said `yielded`
  must lack `open_question_ids`.

### [2026-08-20] #304 gains an instance: five of seven twin pairs unmerged, silently

- **Kind:** filing
- **Found during:** #293, Gate 1 (run `136b6616a990d48f`,
  `dogfood-logs/293-gate1-run1/`)
- **Where:** `src/acceptance/requirement/` — the obligation-linking pass
- **Severity:** should-fix
- **What's wrong:** `current-task.md` for #293 states each rule as a Constraint
  and mirrors it as a Completion expectation, producing seven twin pairs. Two
  merged (`constraint-04`/`completion-05`, `constraint-05`/`completion-06`) and
  five did not, leaving five duplicate obligations that will be judged
  independently at Gate 2. No `Unreconciled linking answers:` block appeared, so
  this is #304 (twins unmerged with no diagnostic) and not #242 (which reports
  itself).
- **Why I didn't act:** #304 is already filed under #181; this is a second
  measured instance on a different mandate, so it belongs as a comment on that
  issue rather than as new work inside #293.
- **Drafted fix:** an `add_issue_comment` on **#304**:

  > Second instance, from #293's Gate 1 (`dogfood-logs/293-gate1-run1/`, run
  > `136b6616a990d48f`).
  >
  > The mandate states each rule as a Constraint and mirrors it as a Completion
  > expectation — seven such pairs. **Two merged, five did not:**
  >
  > | Constraint | Completion expectation | Merged? |
  > |---|---|---|
  > | `constraint-01` unchanged inputs keep the stored rating | `completion-02` (first half) | **no** |
  > | `constraint-02` unchanged inputs cost no judgement request | `completion-02` (second half) | **no** |
  > | `constraint-04` mapped test set changed → judged again | `completion-05` | yes |
  > | `constraint-05` requirement text changed → judged again | `completion-06` | yes |
  > | `constraint-06` the file-touch rule is removed | `completion-07` | **no** |
  > | `constraint-07` coverage and evidence staleness decided separately | `completion-08` | **no** |
  > | `constraint-08` a repeated review produces the same review state | `completion-09` | **no** |
  >
  > No `Unreconciled linking answers:` block was printed, which is what separates
  > this from #242 — the failure is silent, and the only way to see it is to read
  > the breakdown against the task file by hand.
  >
  > Two details worth keeping. First, the merge rate is not a property of the
  > mandate's phrasing: `constraint-04`/`completion-05` and
  > `constraint-05`/`completion-06` are word-for-word identical between the two
  > sections and merged, while `constraint-06`/`completion-07` and
  > `constraint-08`/`completion-09` say the same thing in different words and did
  > not — so paraphrase, not identity, looks like the discriminator. Second,
  > `completion-02` was split into two obligations whose second is contained in
  > the first, and neither half merged with the constraint it restates, so one
  > requirement contributed two unmerged twins rather than one.
- **Status:** **filed** — approved at #293's Gate 1 and posted to #304 on
  2026-08-20 as a single comment covering runs 1 and 2, merged with the run-2
  addendum queued further down. The run-1 hypothesis that *"paraphrase, not
  identity, is the discriminator"* did **not** survive run 2 and was dropped from
  the filed text: `constraint-01` and `completion-02` are still a paraphrase and
  merged anyway.

### [2026-08-20] Decision: what decides implementation-coverage staleness once the file-touch rule is deleted

- **Kind:** decision
- **Found during:** #293, Gate 1
- **Where:** `src/acceptance/rerun.py:169` (`stale_obligation_ids`) and
  `src/acceptance/pipeline.py:309`
- **Severity:** blocker for #293
- **What's wrong:** #293 requires both that the file-touch staleness rule be
  *removed* and that coverage staleness be decided *separately* from
  test-evidence staleness — while its scope exclusions forbid *narrowing* which
  criteria are judged again in any stage other than test-evidence judgement.
  Today one predicate, `stale_obligation_ids`, gates both axes by asking whether
  any cited file was touched. Deleting it leaves coverage with no staleness rule,
  and the obvious replacement — comparing the contents of cited implementation
  spans — is strictly *narrower* than the file-touch rule and so is excluded.
- **Why I didn't act:** it decides the shape of the deliverable and changes the
  cost profile of a shipped feature (M7.5's incremental re-run), so it is the
  human's call at the gate rather than mine mid-task.
- **Drafted fix:** **coverage stops carrying and is re-derived for every
  obligation.** That satisfies all three requirements at once — the file-touch
  rule is gone, the two axes are decided by different rules, and coverage is
  *widened* rather than narrowed. The cost is near zero because
  `classify_coverage` is a **single batched call** over the whole obligation set
  (`src/acceptance/coverage/classify.py:142`), so narrowing the list only shrinks
  one prompt; it never removes a call. The same argument #293's own issue makes
  about mapping.

  Rejected alternative: give coverage its own content-level rule, keyed on the
  cited implementation spans. It preserves today's behaviour most closely and
  would be the better end state, but it narrows a non-evidence stage, which
  `current-task.md`'s fifth scope exclusion rules out, and it doubles the size of
  this task.

  Consequence either way, and it is inside #293's own area so it is part of the
  work rather than a queue item: `rerun.py::merge_carried_forward` currently takes
  a prior judgement **wholesale**, and its docstring argues explicitly against
  splicing a prior evidence class onto fresh citations. Once the predicate splits,
  an obligation can be fresh on coverage and carried on evidence, so that
  wholesale rule has to become per-axis and the docstring's argument has to be
  restated rather than deleted. That is a design change worth a Decision Record
  (`docs/DR-293-*.md`), which #286 is owed anyway.
- **Status:** **resolved** at #293's Gate 1, 2026-08-20. The human chose the
  recommendation: implementation coverage stops carrying and is re-derived for
  every requirement. They noted that a content-level rule for coverage is the
  better answer and is wanted eventually, as a defence against instability rather
  than as a cost saving — filed forward as the queue item below. No task-file edit
  was needed: widening what gets re-derived is permitted by the fifth scope
  exclusion, which forbids only *narrowing*.

### [2026-08-20] Give the code-verdict half its own content-level staleness rule

- **Kind:** filing
- **Found during:** #293, Gate 1
- **Where:** `src/acceptance/rerun.py`, `src/acceptance/pipeline.py:309`
- **Severity:** nice-to-have
- **What's wrong:** #293 deletes the "was a cited file edited?" rule and, on the
  human's call, replaces it for implementation coverage with nothing — coverage is
  simply re-derived for every requirement on every run. That is correct and nearly
  free, because `classify_coverage` is a single batched call, but it is the blunt
  answer. The sharp one is to compare the contents of the cited implementation
  spans, the way #293 does for mapped tests.
- **Why I didn't act:** deliberately deferred by the human at #293's Gate 1 —
  "a more sophisticated answer in order to prevent instability, but that's a
  future optimization". Doing it inside #293 would also have breached that task's
  own scope exclusion against narrowing any stage other than test-evidence
  judgement.
- **Drafted fix:** file as a **sub-issue of #185** (findings model, verdict and
  presentation — where coverage classification lives), sequenced after #293:

  > **Title:** Implementation coverage is re-derived only when the cited code changed
  >
  > #293 deleted the file-level staleness rule and, for the implementation-coverage
  > half, replaced it with "always re-derive". That is safe and costs almost
  > nothing — `classify_coverage` is one batched call over the whole obligation
  > set, so trimming the list shortens a prompt and never removes a call.
  >
  > It is still the blunt answer. Re-deriving a verdict is not free of consequence:
  > that is the whole finding behind #293 and #292 on the evidence side, where
  > asking the model again reliably produced a *worse* answer over unchanged
  > inputs. There is no reason to think the coverage verdict is immune, and
  > re-deriving it every run means it is exposed to that on every run.
  >
  > **Deliverable.** Decide implementation-coverage staleness by comparing the
  > contents of the spans in `coverage_refs`, not by re-deriving unconditionally.
  > Build it on `carry.py` as #291 and #293 do, not beside it.
  >
  > **Acceptance.**
  > - A requirement whose cited implementation spans are byte-identical keeps its
  >   stored coverage verdict.
  > - A requirement whose cited implementation spans changed is classified again.
  > - Editing code cited by one requirement leaves every other requirement's
  >   coverage verdict unchanged.
  > - Two reviews over the same stored state and inputs produce byte-identical
  >   review state.
  >
  > Related: #293, #292, #291, #286, #185.
- **Status:** **filed as #305**, sub-issue of #185, on 2026-08-20. The filed text
  states the motive the human gave — instability, not cost — and adds one
  acceptance item the draft lacked: an obligation citing no implementation at all
  must still always be classified.

### [2026-08-20] A reworded scope exclusion is re-derived from the new text and lands on the old, false obligation

- **Kind:** filing
- **Found during:** #293, Gate 1 (runs `136b6616a990d48f` and `a84c1b0c6e71916a`,
  `dogfood-logs/293-gate1-run{1,2}/`)
- **Where:** `src/acceptance/requirement/obligations.py` — scope-exclusion derivation
- **Severity:** should-fix
- **What's wrong:** #293's `exclusion-04` was reworded from *"Rejecting a
  re-judgement that names no change it was given"* to *"Changing how a
  re-judgement that names no change is rejected"*, precisely to stop the tool
  asserting that the delivered change must not contain behaviour that #292
  already built and that #293 depends on. **The derived obligation did not move at
  all** — same id, same description, `satisfied_by_absence` still true.
- **Why I didn't act:** rewording is the sanctioned fix for weak requirement text
  and it was tried; the controlled pair shows it is not the lever, and CLAUDE.md
  forbids rewording repeatedly to chase a gate.
- **Drafted fix:** an `add_issue_comment` on **#301**:

  > A sharper instance, with a controlled before/after pair, from #293's Gate 1
  > (`dogfood-logs/293-gate1-run{1,2}/`).
  >
  > One scope exclusion was reworded between the two runs and nothing else about it
  > changed:
  >
  > | | text | derived obligation |
  > |---|---|---|
  > | run 1 | Rejecting a re-judgement that names no change it was given. | The change does not reject a re-judgement that names no change it was given. |
  > | run 2 | Changing how a re-judgement that names no change is rejected. | The change does not reject a re-judgement that names no change it was given. |
  >
  > Byte-identical description, byte-identical id
  > (`rejecting-a-re-judgement-that-names-no-change-it-was-given-not-done`),
  > `satisfied_by_absence: true` in both.
  >
  > **This is not the carry reusing a stale entry.**
  > `.acceptance/ledger/a84c1b0c6e71916a.json` records the requirement as
  > `derivation: "revised"` with `revision_reason: "requirement text changed
  > from: Rejecting a re-judgement…"`, its `source_spans` quotes the **new**
  > sentence, and `observable_behavior` was genuinely re-derived — it differs
  > between the runs ("no work that rejects" → "no logic that rejects"). The model
  > saw the new wording and normalised *"Changing how X is done"* back into *"The
  > change does not do X"*.
  >
  > Those are different claims and the second one is false here. #292 built the
  > rejection of a re-judgement that names no change; it stays, and #293 builds on
  > it. The exclusion means "I am not touching that behaviour". The obligation says
  > "that behaviour must be absent from the change" — and marks itself
  > `satisfied_by_absence`, so at Gate 2 a diff that edits `evidence/anchoring.py`
  > and `evidence/discrimination.py` for the right reasons is set up to be reported
  > as breaching it.
  >
  > The general shape: an exclusion naming *a change to an existing behaviour* is
  > collapsed into an exclusion naming *the behaviour itself*. Those coincide only
  > when the behaviour does not already exist. Where it does, the derived
  > obligation contradicts the delivered tree, and no rewording available to the
  > task author fixes it.
- **Status:** **filed** — posted to #301 on 2026-08-20, approved at #293's Gate 1.
- **Third instance, #317's Gate 1 (2026-08-21) — drafted follow-up comment on
  #301, needs approval.** Different mandate, different exclusion shape, same
  "rewording moves nothing" outcome. `exclusion-01` read *"Whether an answer the
  review cannot read should stop the whole review or only the requirements that
  answer was asked about"* and yielded *"The review does not let an unreadable
  answer stop the whole review **or only the requirements that answer was asked
  about**"* — incoherent, since it denies both halves of an exhaustive pair. It
  was reworded into a noun phrase matching its four well-behaved neighbours,
  *"How much of a review an answer the review cannot read at all stops."* The
  requirement **was** re-derived — its obligation `type` moved `functional` →
  `compatibility`, and the run reports it among "2 revised" — and the
  description came back **byte-identical**, now corresponding to no text in the
  mandate at all. Adds to #301: the failure is not specific to
  *"changing how X is done"* phrasings; a *"whether A or B"* phrasing collapses
  the same way, and the malformed obligation outlives the wording that produced
  it. Evidence: `dogfood-logs/317-gate1-run{1,2}/`.

### [2026-08-20] #304 gains a second instance, and a meaning-preserving edit flips an untouched pair

- **Kind:** filing
- **Found during:** #293, Gate 1 run 2 (`a84c1b0c6e71916a`)
- **Where:** `src/acceptance/requirement/` — the obligation-linking pass
- **Severity:** should-fix
- **What's wrong:** run 2 merges four of the seven twin pairs where run 1 merged
  two. The only relevant edit between the runs made one trailing clause match its
  twin word for word, without changing meaning — and the merge outcome flipped for
  both halves of that requirement, including a pair whose own text was never
  edited.
- **Why I didn't act:** #304 is filed; this is evidence for it, not new work.
- **Drafted fix:** fold into the #304 comment already drafted above rather than
  filing separately — post one comment covering both runs, with run 2's table and
  this paragraph appended:

  > **Run 2 is the controlled half.** Two requirements were reworded after run 1 and
  > nothing else changed. Merges went from two pairs to four:
  >
  > | pair | run 1 | run 2 |
  > |---|---|---|
  > | `constraint-01` ↔ `completion-02` | unmerged | **merged** |
  > | `constraint-02` ↔ `completion-02` | unmerged | **merged** |
  > | `constraint-04` ↔ `completion-05` | merged | merged |
  > | `constraint-05` ↔ `completion-06` | merged | merged |
  > | `constraint-06` ↔ `completion-07` | unmerged | unmerged |
  > | `constraint-07` ↔ `completion-08` | unmerged | unmerged |
  > | `constraint-08` ↔ `completion-09` | unmerged | unmerged |
  >
  > The edit that moved it made `constraint-02`'s trailing clause identical to
  > `completion-02`'s. Meaning unchanged. And it flipped `constraint-01` too, whose
  > text was never touched — so a merge decision moved because a *neighbouring*
  > requirement was reworded.
  >
  > Lexical overlap is clearly not the whole rule — `constraint-01`'s "keeps the
  > rating stored for it" and `completion-02`'s "keeps its stored rating" are still
  > only a paraphrase, and merged. But it is enough of the rule that a task author
  > can move merge decisions by rephrasing, which is the edit CLAUDE.md forbids for
  > exactly this reason.
  >
  > One of the three still-unmerged pairs is defensible: `constraint-08` says a
  > repeated review "produces the same review state" and `completion-09` says
  > "byte-identical review state", which is a stronger claim. The other two are
  > plain restatements.
- **Status:** **filed** — merged into the single #304 comment above rather than
  posted separately, on 2026-08-20.

### [2026-08-20] A continued run keeps an obligation after its source sentence is deleted from the requirement
- **Kind:** filing
- **Found during:** #302, Gate 1
- **Where:** `src/acceptance/requirement/` — the `--continue` carry path (#269's
  mechanism), not the decomposer itself
- **Severity:** should-fix
- **What's wrong:** Editing a requirement to **delete** a sentence leaves the
  obligation derived from that sentence in the carried set. The obligation then
  traces to no text in the mandate, which breaches the standing invariant that
  every finding links to exact requirement text.

  Measured over two runs of the same task file, one carried and one fresh:

  | run | mode | `exclusion-01` obligations |
  |---|---|---|
  | `f1f9a9c986aeaafe` (run 3) | `--continue e5c2490c4a564ea5` | **2** |
  | `e884fa0078cdfdce` (run 4) | fresh, no carry | **1** |

  `exclusion-01` was trimmed from two sentences to one. Run 3 prints the trimmed
  one-sentence text and still carries
  `changes-answers-carried-and-identified-not-asked-or-decided` — *"The work
  changes how answers are carried and identified, not what is asked or decided"* —
  which is verbatim the deleted sentence. The fresh run over identical text yields
  one obligation. So the decomposer reads the current text correctly and the carry
  is what retains the orphan.

  This is a **deletion**, not a reword. #269's carry is built to hold an
  obligation stable when its requirement is reworded, which is exactly right; the
  gap is that a requirement whose text shrank still matches well enough to carry
  everything it previously produced.

  It matters more than a stray obligation, because `CLAUDE.md`'s Gate 1 tells
  every session to re-run with `--continue` after reworking `current-task.md` —
  so the defect fires precisely on the runs the procedure mandates, and the
  orphan is invisible unless a fresh run is done alongside to compare.
- **Why I didn't act:** outside #302's scope, which is response schemas. Fixing
  carry semantics would also re-key the decompose stage and force a corpus
  re-record that #302 is already going to pay once.
- **Drafted fix:** file as a **sub-issue of #181** (decomposition).

  > **Title:** A continued run keeps an obligation whose source sentence was deleted from the requirement
  >
  > **Body:** `--continue` carries obligations for a requirement whose text was
  > edited. When the edit **deletes** a sentence, the obligation derived from that
  > sentence is carried anyway, and afterwards links to no text in the mandate.
  >
  > Reproduced at #302's Gate 1 over one task file, `exclusion-01`, trimmed from
  > two sentences to one:
  >
  > | run | mode | obligations |
  > |---|---|---|
  > | `f1f9a9c986aeaafe` | `--continue` | 2 — including the deleted sentence, verbatim |
  > | `e884fa0078cdfdce` | fresh | 1 |
  >
  > Logs: `dogfood-logs/302-gate1-run3/` and `dogfood-logs/302-gate1-run4-diagnostic/`.
  >
  > Sharpest because `CLAUDE.md`'s Gate 1 requires `--continue` on every re-run
  > after reworking the task file, so this fires on the mandated path, and nothing
  > in the output reveals it — the run prints the *trimmed* requirement text above
  > the stale obligation.
  >
  > **Acceptance:** deleting a sentence from a requirement drops the obligations
  > derived from it on the next continued run; an obligation carried forward
  > still quotes text present in the current requirement; the existing reword
  > behavior (#269) is unchanged.
- **Status:** filed (#306, sub-issue of #181). Approved at #302's Gate 1.

### [2026-08-20] #242 gains a Task/Constraint duplicate pair that survives a fresh run
- **Kind:** filing
- **Found during:** #302, Gate 1
- **Where:** `src/acceptance/requirement/` — obligation merging
- **Severity:** nice-to-have
- **What's wrong:** #302's mandate states its core demand in the `# Task`
  headline and again as `constraint-01`. The two produce separate obligations
  that are never merged:

  - `task-01` → *"Every call a stage makes within one review run declares the
    same answer format."*
  - `constraint-01` → *"Every call a stage makes within one run declares the same
    answer format, whatever items that particular call asks about."*

  The tool demonstrably *can* merge a Task/Constraint pair — #265's Gate 1 run 3
  merged `task-01` with `constraint-05` into one shared obligation — so this is a
  non-merge, not a missing capability.

  Reproduced **fresh as well as carried**: run 4 with no carry produces
  `keep-stage-answer-format-stable-within-run` against
  `same-answer-format-within-run`. Not an artifact of `--continue`.
- **Why I didn't act:** the duplicate is redundant, not contradictory, and
  deleting `constraint-01` to move the tool's output would be editing the input
  to change what the review says. Left in place deliberately.
- **Drafted fix:** `add_issue_comment` on **#242**, matching how the previous
  three instances were recorded. Carry both obligation texts, the #265 run-3
  counter-example showing a merge does happen, and the run 3 / run 4 pair showing
  it is independent of the carry.
- **Status:** filed (comment on #242). Approved at #302's Gate 1.

### [2026-08-20] The mapper declines the obligation a test restates, while accepting four looser ones

- **Kind:** filing
- **Found during:** #293, Gate 2 (`dogfood-logs/293-gate2-run1/`, run
  `6f64baa7e8cf3a78`)
- **Where:** `src/acceptance/evidence/mapping.py`
- **Severity:** blocker — it was the only thing keeping #293's Gate 2 from clean
- **What's wrong:** the obligation
  `adding-test-to-unmapped-file-leaves-rating-unchanged` came back with no mapped
  test, and the prescribed test is almost word for word
  `tests/evidence/test_rejudge.py::test_a_test_appended_to_the_same_file_does_not_disturb_the_rating`,
  which is in the diff under review and which the same report cites twice under
  two other obligations.

  **Not a partitioning defect.** Transcript `c3f75a2e…` held both the obligation
  and the test in one request; the mapper returned four obligations for that test
  and none was this one, and mapped no test at all to this obligation. Mapping was
  not half-blind overall — two other obligations in the same run carry 20+ mapped
  tests each.
- **Why I didn't act:** there is no honest code change. The test exists, is
  correct, and was defect-injected. Writing a second test to coax the mapper would
  be rewriting the output rather than the software.
- **Drafted fix:** file as a sub-issue of **#182**, carrying the transcript
  evidence, the partitioning ruling-out, and one hypothesis marked as a
  hypothesis: the obligation's id reads `adding-test-to-**unmapped**-file-…`,
  which asserts the opposite of its own description, and ids are shown to the
  mapper.
- **Status:** **recorded on #173**, on 2026-08-20. Approved at #293's Gate 2.
  Filed first as #307, then found to be #173 — *"M4 mapping maps obligations to
  plainly unrelated tests while rejecting the on-point one"* — seen from the other
  side: there an obligation drew eleven unrelated tests and rejected the on-point
  one, here it drew none while its on-point test went to four looser obligations.
  #307 is closed as a duplicate of #173 and detached from #182; the evidence lives
  on #173. Filing it separately was my error — I did not check #182's existing
  children first. #293 merged with the gate deliberately not clean, on the human's
  approval, as #291 and #292 did.

### [2026-08-21] #173's premise does not survive measurement — the mapper is right 80% of the time and the pipeline takes one draw
- **Kind:** filing
- **Found during:** #173, pre-Gate-1 measurement
- **Where:** `src/acceptance/evidence/mapping.py` (the stage), measured off
  transcript `c3f75a2e067e…`
- **Severity:** blocker (for #173 as scoped — it changes what the task is)
- **What's wrong:** #173 is filed as a *precision* defect: the mapper declines
  the on-point obligation↔test pairing and accepts looser ones. Re-issuing the
  byte-identical recorded request 25 times against the same model, temperature
  and seed shows it is not a precision defect but the visible tail of per-call
  variance.

  | measurement | result |
  |---|---|
  | on-point pairing returned | **20 of 25 draws (80%)** |
  | distinct full answers | **23 across 25 draws** |
  | mean pairwise edge agreement (Jaccard, test→obligation edges) | **0.73** |
  | #173's own test — distinct id-sets | **10 variants, modal 12/25** |

  The recorded failure reproduces as 1 draw in 5, with the identical four ids.
  The stage is right about this pairing four times out of five; the pipeline
  takes exactly one draw and stores it as the finding.

  **Both standing hypotheses are null.** Two single-variable arms (N=5 each)
  against a control that already scores 4/5: correcting the contradictory
  obligation id (`adding-test-to-**unmapped**-file-…`) gave 5/5, and deleting
  the system prompt's *"a test returning five or more ids is usually a test
  whose ids were not each put to THE TEST"* sentence gave 4/5. Neither is
  distinguishable from the control. One control draw returned five ids
  *including* the on-point one, so the sentence is not acting as a hard cap.

  **Confounds checked, not assumed:** `mark_reusable_opening` is a no-op for
  `openai/gpt-5.4-mini`, so the control request is byte-identical to the
  recorded one; and `_litellm_effective_controls` confirms `temperature=0.0`
  and `seed=0` both survive to the provider rather than being silently dropped.
  The variance is the provider's own.

  **Scope of the claim, stated honestly:** this is one request, from the #293
  instance, on one model. The *original* #173 instance — an obligation drawing
  eleven plainly unrelated tests — is a different shape and I could **not**
  test it: transcript `3997392e175b…` is not in the cache and transcripts are
  gitignored, so it is unrecoverable without re-running that review against
  pre-#265 code. It may still be a systematic failure.
- **Why I didn't act:** it changes what #173 *is*, and therefore what
  `current-task.md` should mandate. That is the human's call, not mine.
- **Drafted fix:** comment on **#173** with the table above and the two null
  arms, and re-title the issue away from "maps obligations to plainly unrelated
  tests" toward per-call mapping variance. Then decide whether #173 closes into
  **#150** (mapping stability, reopened) / **#180** (judgement stability), or
  stays as the narrower mapping-layer half — the same question #180 already
  raised on this issue on 2026-08-04 and which was never answered.
- **Status:** **closed.** #173 was closed on 2026-08-21 as too narrowly scoped;
  the human is filing a larger change in its place. All measurements are
  recorded in `docs/DR-173-mapping-twin-splitting.md`. No comment was filed on
  #173 itself — the DR is the record.

### [2026-08-21] Unmerged twin obligations measurably starve each other of mapped tests
- **Kind:** filing
- **Found during:** #173, pre-Gate-1 measurement
- **Where:** `src/acceptance/requirement/` (cause) surfacing in
  `src/acceptance/evidence/mapping.py` (effect)
- **Severity:** blocker
- **What's wrong:** measured over the **recorded mapping corpus** — 53
  `_Mappings` transcripts in `.acceptance/cache/transcripts/`, no model calls,
  every judgement already recorded. Where two obligations in the same request
  state the same demand, a test that evidences it is mapped to **only one of
  them about half the time**.

  Five twin pairs, each confirmed by reading both descriptions rather than
  trusted from the similarity score:

  | twin pair | both | exactly one | split |
  |---|---|---|---|
  | `changed-rating-must-name-a-change` / `changed-rating-names-one-given-change` | 0 | 7 | **100%** |
  | `reuse-refusal-carries-reason` / `-2` | 1 | 4 | 80% |
  | `stored-rating-…-recorded-with-judgement-request` / `stored-rating-and-dependency-changes-in-request` | 6 | 4 | 40% |
  | `changed-criterion-gets-dependency-changes` / `…-stored-rating-and-dependency-changes` | 5 | 3 | 38% |
  | `reuse-rule-stated-in-one-place-constraint` / `…-no-stage-named` | 2 | 0 | 0% |
  | **total** | **14** | **18** | **56%** |

  Two similarity candidates were rejected on reading as genuinely distinct
  demands and are excluded above: `changed-criterion-gets-dependency-changes` /
  `changed-criterion-gets-stored-rating`, and
  `criterion-unchanged-inputs-no-judgement-request-2` /
  `unchanged-inputs-keep-stored-rating`.

  Restricting to the decomposer's own duplicate-slug marker alone — ids of the
  form `<base>` and `<base>-2`, the highest-precision detector available — the
  split rate is 4 of 13.

  **This is systematic, not sampling noise**, and it mechanically produces
  #173's headline symptom: if obligation X has a twin X′ and the mapper picks
  X′, X reports *no mapped test* and the recommendation stage prescribes a test
  that already exists and is cited elsewhere in the same report. That is #293's
  instance and #216's.

  **The decomposer already detects the collision.** A `-2` suffix means it
  generated the same slug twice, noticed, and disambiguated instead of merging.
  The information needed to merge is present at decomposition time and is being
  thrown away.
- **Limit on the number, stated honestly:** 53 requests but only **4 distinct
  task decompositions** among them. The 32 opportunities are distinct test
  judgements but cluster within 4 tasks, so 56% is a solid effect of uncertain
  magnitude, not a precise rate. `dogfood-logs/` (170 directories) is unmined —
  it holds rendered reports rather than transcripts and needs a different parser.
- **Why I didn't act:** the fix is at the decomposition layer (#304), which is
  out of scope for #173.
- **Drafted fix:** comment on **#304** with the table above as measured
  downstream cost — it converts #304 from a tidiness complaint into the
  probable cause of a mapping defect. Comment on **#182** that its
  mapping-precision children (#173, #245, #249) should be re-measured after
  #304 lands, since some of their symptoms are likely its.
- **Status:** open. **Replicated on independent data:** parsing the committed
  `dogfood-logs/*/output.log` reports — **76 distinct decompositions**, versus
  4 in the transcript corpus — gives both=200, exactly-one=228, **split 53%**,
  against 56% from the transcripts. Two corpora, two parsers, same answer.
  Restricted to pairs whose obligation text is **byte-identical**, splitting is
  3 of 16 — undeniable errors, but thin. Split rate by similarity band rises as
  pairs get *less* identical (45% at 0.80–0.89, 60% at 0.60–0.64), but that
  band table is **confounded and must not be read as an error curve**: below
  identity, mapping a test to only one of two obligations is often the correct
  answer, so a perfect mapper would produce a rising curve too.

  **Still open after #173 closed on 2026-08-21** — this is a filing against
  #304, not against #173, and the evidence stands on its own. Recomputable at
  any time via `acceptance.benchmark.twin_splitting`; detail in
  `docs/DR-173-mapping-twin-splitting.md` §2.

  **Fresh instance, #317's Gate 1 (2026-08-21), and it sharpens the last point
  above.** `dogfood-logs/317-gate1-run2/`: `task-01` yielded
  `combine-agreeing-accounts-2` stating the same property as `constraint-01`'s
  `combine-agreeing-accounts` — same generated slug, `-2` applied, no merge. In
  the **same run** the linker correctly merged `disagreement-stops-review`
  across `task-01` and `constraint-05` and labelled it "(also serves
  constraint-05)", so this is not a linker that was idle. And the duplicate
  survived a rewrite of `task-01` that removed the sentence stating the
  property: run 1's Task paragraph restated `constraint-01`, run 2's names only
  the topic, and the decomposer manufactured the full restatement anyway. The
  `-2` marker being the highest-precision detector available, and still unused
  while a merge lands beside it, is the concrete form of "the information needed
  to merge is present at decomposition time and is being thrown away".

### [2026-08-21] Mapping prompt wording is a well-powered null; the defect is in the response shape
- **Kind:** decision
- **Found during:** #173, pre-Gate-1 measurement
- **Where:** `src/acceptance/evidence/mapping.py` — the `_Mappings` response
  schema and its system prompt
- **Severity:** blocker (it decides what #173's mandate is)
- **What's wrong:** four arms over 46 real corpus requests, 8 draws each,
  **1,472 calls**. Metric is label-free: two obligations stating the same
  demand must get the same answer, so "mapped to exactly one" is an objective
  error. Guard metric is mean ids per test, so an arm cannot win by mapping
  everything to everything.

  | arm | split rate | vs control | correct (both) |
  |---|---|---|---|
  | control | 148/748 = 19.8% | — | 600 |
  | remove the *"five or more ids"* sentence | 149/726 = 20.5% | z=−0.35, **p=0.72** | 577 |
  | add an explicit "restatements must both be returned" rule | 111/690 = 16.1% | z=1.82, **p=0.068** | 579 |
  | both changes | 123/633 = 19.4% | z=0.17, p=0.87 | 510 |

  **The prompt-contradiction hypothesis is refuted.** The prompt does contain
  two instructions in tension — *"return every id that passes"* versus *"a test
  returning five or more ids is usually a test whose ids were not each put to
  THE TEST"* — and removing the second changes nothing, on a sample large
  enough to have caught a small effect. Recorded because it is a plausible
  story that is wrong, and someone will propose it again.

  The explicit twin rule is the only arm that moves, and weakly: 3.7 points,
  p=0.068, under a fifth of the errors. Combining both changes loses the gain
  and costs 90 correct mappings.
- **The design conclusion:** the cause is structural, not verbal. The schema
  asks for `test → [obligation_ids]` — one joint judgement in which every
  obligation competes for a slot in a single shortlist. No prose can force
  per-obligation evaluation when the output shape rewards picking a list, which
  is how two obligations with *identical text* receive different answers.
  Making each pairing its own question — `test × obligation → boolean` —
  guarantees identical obligations the same answer structurally. A per-test
  call carrying a boolean per obligation keeps the call count unchanged and
  only grows the response; that is the shape to test first.
- **Why I didn't act:** it is the mandate for #173 and wants agreement before
  `current-task.md` is written around it.
- **Note on cost:** this run was estimated at ~$2.90 and cost roughly **$13** —
  the request selector returned 46 requests where I had assumed ~8, and the
  script's own printed estimate was lost to output buffering before it
  committed. Any future arm run must assert its job size before the first call.
- **Status:** **closed** — recorded in `docs/DR-173-mapping-twin-splitting.md`
  §3. The structural fix it proposed was piloted and **failed**; see the next
  entry.

### [2026-08-21] The forced per-obligation verdict cuts splits by destroying recall — do not build it
- **Kind:** defect
- **Found during:** #173, pre-Gate-1 measurement (capped pilot, 72 calls, $0.51)
- **Where:** proposed change to `src/acceptance/evidence/mapping.py`'s response
  schema
- **Severity:** blocker (it removes the design the previous entry recommended)
- **What's wrong:** the entry above concluded the defect was structural — that
  `test → [obligation_ids]` lets obligations compete for slots in a shortlist —
  and proposed replacing it with a verdict required for **every** obligation,
  `test → {obligation_id: bool}`, enforced by `strict` mode so a shortlist is
  impossible. Piloted over 6 corpus requests, 6 draws, against control:

  | arm | splits | correct (both) | mean ids/test | tests answered | cost/call |
  |---|---|---|---|---|---|
  | control | 19/172 = 11% | 153 | 1.54 | 9.2 | $0.00423 |
  | verdicts | 1/63 = **2%** | **62** | 0.57 | 9.2 | $0.00981 |

  **The split rate improved for the wrong reason.** Both arms answered the same
  number of tests (9.2), so nothing was skipped — the verdict arm simply
  answered *false* far more often, losing **91 of 153 correct twin-mappings, a
  59% recall loss**, to remove 18 splits. Asked in isolation whether a test
  would fail if one obligation's behavior were missing, the model defaults to
  no.

  That is DR-164's failure mode — the mapping stage shedding work — which #164
  exists to prevent. The guard metric (mean ids per test, 1.54 → 0.57) is what
  caught it; a split-rate-only pilot would have reported this as a success.
- **Why I didn't act:** the variant is dead as written; anything replacing it
  must be scored on recall as well as splits.
- **Drafted fix:** none yet. Any successor must hold `both` at or above control
  while cutting `one`. Worth trying: keep the list shape but ask the model to
  re-read its own answer against every obligation it omitted, as a second pass.
- **Status:** **closed** — recorded in `docs/DR-173-mapping-twin-splitting.md`
  §3, including the rule that any successor is scored on recall as well as
  splits. The untested second-pass design is carried in the DR's closing
  section.

### [2026-08-21] Prompt caching is worth about half the mapping stage's cost and production appears to get none of it
- **Kind:** filing
- **Found during:** #173 structural pilot (usage recorded per call)
- **Where:** `src/acceptance/llm.py`, request assembly generally
- **Severity:** should-fix
- **What's wrong:** measured cache behaviour over repeated mapping calls whose
  requests share a prefix. Draws were run sequentially per request so the cache
  could warm; draw 0 is the cold reference.

  Warming curve (control arm): 48% → 73% → **94% → 94% → 94%** → 83% of prompt
  tokens served from cache.

  Once warm, **94% of input tokens are reused**, and measured cost/call fell to
  **$0.00423** against **$0.0089** for the recorded pre-#265 transcript at 0%
  cached — roughly **half**.

  **This is not the first evidence that the ordering works.** #191's branch
  measured **84–93%** of each *discrimination* verdict request served from the
  provider's cache, live, because both its prompts put the invariant code block
  first (`session-state/191.md`, 2026-08-13); #265 generalised that ordering to
  every stage. The correction matters to how this is filed: the question is not
  whether prefix ordering buys reuse, but whether #265 extended it to mapping.

  Every recorded transcript in the corpus still shows `cached_tokens: 0` and
  they all predate #265, so **mapping in a live run remains unmeasured**. Within
  one review the obligations block is shared by every partitioned mapping call,
  so it should warm after the first call.
- **A limit worth stating, because it constrains every future fix:** the
  discount applies to **input only**. The failed verdict arm's penalty was 2.5×
  *output* (787 → 1,981 completion tokens/call), which is never cached, so its
  cost stayed 2.3× control even at a 74% hit rate and does **not** amortize as
  the cache warms. No design that grows the response can be paid for by
  caching.
- **Why I didn't act:** out of scope for #173, and it belongs with #265's work
  rather than with mapping.
- **Drafted fix:** run one live review post-#265 and report `cached_tokens` per
  stage; if it is still near zero, file against #265's umbrella (#184,
  determinism & reproducibility, which owns `llm.py`). Cheap to check and worth
  roughly half the model spend of a run.
- **Status:** **open, and independent of #173** — this is a filing against #184
  and survives #173's closure on 2026-08-21. Detail in
  `docs/DR-173-mapping-twin-splitting.md` §4, including the constraint that the
  discount is input-only, which bounds the cost of any future stage redesign.

### [2026-08-21] `discovery.py`'s docstring claims a call graph the module does not have

- **Kind:** defect
- **Found during:** #312, while drafting sub-issue #314's Inputs
- **Where:** `src/acceptance/evidence/discovery.py:4`
- **Severity:** should-fix
- **What's wrong:** the module docstring says existing tests are connected to a
  changed symbol "by call graph, non-call reference, import, or naming". There
  is no call graph. `_names_called` collects the names called directly inside a
  test node, `_names_referenced` collects every identifier in it, and
  `_imported_module_stems` collects the module's top-level import stems; those
  three are intersected with `_changed_symbol_names` and
  `_changed_module_stems`. Nothing resolves a called name to a definition and
  nothing follows an edge transitively, so the module reports positive
  name overlap and cannot establish that a static path is absent.
- **Why this matters beyond tidiness:** the claim was believed. DR-312's
  resolved question 2 originally had the reachability prefilter reusing "M4.1
  discovery's call graph", taken from this docstring without reading the code.
  A code check caught it before #314 was filed, and the DR now carries an
  amendment; had it not, #314 would have been scoped against machinery that does
  not exist. A docstring that overstates its module is a live trap for exactly
  the design work that reads docstrings to scope an issue.
- **Why I didn't act:** out of scope for #312, which ships a design record and a
  backlog split and touches no source.
- **Drafted fix:** one line. Replace "by call graph, non-call reference, import,
  or naming" with wording that matches the implementation — e.g. "by overlap
  between the names a test calls or references, or the modules it imports, and
  the symbols and modules the change touched". Optionally add the limitation
  the amendment turns on: this reports positive overlap and cannot prove a path
  absent. No behavior change, no transcript impact.
- **Status:** open

### [2026-08-21] One requirement split across twelve `yielded` dispositions aborts the whole review — a second cause for #298's crash

- **Kind:** filing
- **Found during:** #313, Gate 1 (runs 1 and 2 —
  `dogfood-logs/313-gate1-run1/`, `dogfood-logs/313-gate1-run2/`)
- **Where:** `src/acceptance/requirement/obligations.py:1275` (the raise), with
  the guard that misses it at `:1214-1244`
- **Severity:** blocker — it produced no decomposition at all, so #313's Gate 1
  cannot be reached on this task file
- **What's wrong:** decompose batch 1 was asked about `exclusion-05`,
  `exclusion-06` and `task-01`, and returned fourteen dispositions: the two
  exclusions, then **twelve** for `task-01`. All twelve say `yielded` and each
  carries a *different* obligation — the model split one requirement across
  twelve dispositions instead of nesting twelve obligations inside one
  disposition's `more_obligations`. Only the first copy used that field; the
  other eleven left it empty. `_requirement_map` treats any two non-identical
  dispositions for one requirement as a self-contradiction and raises, ending
  the run. Three of the four batches had answered cleanly; eighteen
  requirements were decomposed and none survive.
- **Why this is not #298:** #298 is the same crash at the same line, from
  #265's Gate 1, but its cause is a *verbatim repeat* with `-dup` appended to
  every id — a degenerate generation. Its proposed fix, comparing dispositions
  for equality while ignoring ids, does not catch this: the copies here differ
  in every field, not only their ids. Nor is it #248 (a repeated obligation
  *inside* one disposition). What all three share is the abort site.
- **Why I didn't act:** the fault is in `requirement/`, the #181 decomposition
  umbrella's area, not #313's. The §4 fix-it-now exception needs both
  "unachievable Acceptance" *and* "inside the task's own area"; only the first
  holds.
- **Drafted filing — child of #181, labels `bug`, `track:checker`:**

  **Title:** One requirement split across many `yielded` dispositions aborts
  the whole review

  **Body:**

  Child of #181. A second, distinct cause of the crash #298 reports; #298's
  proposed fix does not cover it.

  From #313's Gate 1 (`dogfood-logs/313-gate1-run1/`):

  ```
  acceptance: model error: requirement 'task-01' was disposed more than once
  ```

  Batch 1 was asked about three requirements and returned fourteen
  dispositions — `exclusion-05`, `exclusion-06`, and `task-01` twelve times.
  Every `task-01` copy says `yielded`. Each carries a different obligation,
  with its own description, type and `source_quote`, and the twelve together
  are a reasonable decomposition of the Task paragraph — distinct, grounded in
  its text, nothing invented. The model expressed one answer twelve times
  instead of once with twelve obligations in `more_obligations`; only the first
  copy used that field at all.

  **Why the existing guards miss it.** `_batch_dispositions`
  (`obligations.py:1214-1244`) drops only an EXACT repeat (`previous == entry`).
  #298 proposes widening that to equality-ignoring-ids. Neither test fires here:
  the copies differ in every field. So they reach `_requirement_map`
  (`:1275`), which raises.

  That raise implements #217's ban on a self-contradictory disposition — "two
  different answers for one requirement". Twelve dispositions all agreeing on
  `yielded` are **one** answer, badly shaped. A contradiction would be
  `yielded` against `no_obligation`, or two copies disagreeing about the same
  obligation's type or text.

  **Consequence.** The whole review is abandoned, not the malformed part. Three
  of four batches answered cleanly and are discarded with the fourth. The
  response is recorded, so the failure is permanent for that input: run 2
  replayed it and died identically. Clearing it means finding and deleting the
  transcript by hand, which nothing in the output suggests. And a crashed run
  writes no ledger entry, so there is no run id for `--continue` and the next
  attempt cannot carry anything forward.

  This collides with the standing invariant that uncertainty is first-class. A
  requirement whose obligations arrived across several agreeing dispositions is
  at worst an indeterminate result about one requirement; it is not grounds for
  producing nothing.

  **Suggested direction.** When every disposition returned for one requirement
  agrees on its `disposition` kind, merge them rather than raise: union their
  obligations in returned order, `_unique` the ids as it already does for
  collisions, and record the merge on `UnusableAnswerLog` so it is visible
  rather than silent. Keep the raise for the case #217 actually names — copies
  whose `disposition` values differ, or which disagree about a shared
  obligation. Deliberately narrower than "drop any duplicate": the twelve
  obligations here are real work and dropping eleven of them would silently
  lose most of a requirement's decomposition, which is worse than the abort.

  Worth deciding alongside it, and shared with #298: whether one batch's
  `SchemaValidationError` should end the run at all, or be recorded against
  that batch's requirements while the rest of the review proceeds. Same
  argument #275 makes about one omitted recommendation aborting thirteen.

  **Acceptance**
  - A response returning one requirement's disposition several times, all
    agreeing on the disposition kind and each carrying different obligations,
    yields the union of those obligations and completes.
  - The merge is recorded on `UnusableAnswerLog`, not silent.
  - Copies whose `disposition` values differ still raise.
  - A test drives `decompose` through the path, not only the helper.

  Evidence: `dogfood-logs/313-gate1-run1/judgement.md` (batch-by-batch
  disposition ids and the twelve obligations), `dogfood-logs/313-gate1-run2/`
  for the deterministic replay.

  Related: #181, #217, #248, #275, #298.
- **Status:** FILED as #317 (2026-08-21), attached to #181, and taken as the
  task in flight ahead of #313 — the human's call at #313's Gate 1.



### [2026-08-29] #317's issue body proposes the wrong fix and must be rewritten before it can be closed

- **Kind:** filing
- **Found during:** #317, Gate 1 (runs `7cb6be48b0942761` and `0b7c947eb8c27f5c`,
  `dogfood-logs/317-gate1-run{4,5}/`), on the evidence in
  `docs/experiments/317-over-answering/findings.md`
- **Where:** GitHub issue #317
- **Severity:** blocker — the issue is the plan, and the plan is wrong
- **What's wrong:** #317's Acceptance asks for agreeing dispositions to be
  merged. `findings.md` §1 shows the fourteen dispositions in the recorded
  failure are not one requirement split twelve ways: entries 3-13 quote
  `constraint-01` … `constraint-12` verbatim, one per constraint, and the
  `requirement_id` enum collapsed eleven intended labels onto the one value it
  was allowed to write. Merging gives `task-01` sixteen obligations, eleven of
  which `_resolve_attributions` then scatters onto constraints another batch
  already derived — manufacturing eleven duplicate pairs to avoid an abort.
- **Why I didn't act:** rewriting the backlog is a change to the plan, and the
  human approves those.
- **Drafted fix:** replace #317's body with the text below, keeping its title's
  subject but restating it, its labels (`bug`, `track:checker`) and its parent
  (#181, the umbrella for decomposition defects). Close it when this lands.

  > **Title:** The decomposer answers for requirements it was only shown as
  > context, and the summary paragraph is where it happens
  >
  > Child of #181. Supersedes this issue's own original proposal, which was to
  > merge agreeing dispositions; `docs/experiments/317-over-answering/findings.md`
  > shows that repairs the wrong thing.
  >
  > **What the evidence says.** Over the 1,748 recorded transcripts: 8 of 35
  > decompose batches containing a `task-*` requirement return an obligation
  > quoting a requirement the call was not asked about, against 0 of 68 batches
  > without one (Fisher one-sided p = 0.0001). Five of the eight return the right
  > number of dispositions and misattribute silently; only three crash. The crash
  > `#298` and this issue both report is the loud minority of one defect.
  >
  > **Why the count is the wrong thing to constrain.** A response model with one
  > required field per requirement id accepts five of the eight recorded failures
  > unchanged and converts the other three from a crash into silent
  > misattribution. `DR-302` already priced fixed slots and rejected them; on this
  > stage the schema goes from 11 KB to 93 KB at batch size 8.
  >
  > **The change.** Three pieces, one re-record:
  >
  > 1. **One requirement per call**, with `source_quote` an enum of that
  >    requirement's own spans. An obligation about `constraint-03` becomes
  >    unrepresentable in a call about `task-01` — unsayable, not detected
  >    afterwards. Measured schema cost: +1,506 bytes, +14%, against 93 KB for
  >    the fixed-slot shape. `_locate_quotation` and `_resolve_attributions`
  >    retire. This makes #231's per-requirement request key structural.
  > 2. **The summary paragraph is accounted for last**, in a step of its own
  >    that divides it into spans of its own words and decides, per span,
  >    whether the obligations already derived require the same thing. That step
  >    returns no obligations; uncovered spans are handed to the ordinary
  >    per-requirement decomposer. Measured over 20 draws on two mandates, this
  >    shape never once marked a genuinely uncovered property as covered, and
  >    marked a covered property as uncovered in 4 of 20 — a duplicate
  >    obligation rather than a lost requirement.
  > 3. **The prompt contradictions** `findings.md` §6 names. Two disappear
  >    structurally under (1). The third does not: the shared preamble tells the
  >    model it is given material and then instructions, while `assemble` sends
  >    instructions first.
  >
  > The summary step needs `openai/gpt-5.4`; `gpt-5.4-mini` failed it in three
  > different ways across three prompts, at $0.011 per review for that call. So a
  > step gains the ability to name its own model.
  >
  > **Acceptance**
  > - A call accounting for a requirement other than the summary is asked about
  >   that one requirement and returns exactly one account of it.
  > - An obligation's quotation is drawn from the requirement its call was asked
  >   about; a quotation belonging to another requirement is unrepresentable.
  > - No call accounting for another requirement is asked about the summary.
  > - The summary's spans are substrings of the summary and each is decided
  >   exactly once; a span the derived obligations already require yields no
  >   obligation; a span they do not require yields one, quoting that span.
  > - A step naming its own model runs on it; a completed run says which model
  >   each step used.
  > - A test drives the whole path from mandate to obligations, not one step.
  > - Two recorded runs over the same input are byte-identical.
  >
  > **Deferred, deliberately:** the re-record. The test suite injects its own
  > `completion_fn` and reads no recorded transcript, `decompose` defaults to
  > record-on-cache-miss, and only `check` (which defaults to replay) and the
  > benchmark corpora need rebuilding. Benchmark figures do not span this change.
  >
  > Evidence: `docs/experiments/317-over-answering/findings.md` and the four
  > experiment arms beside it; `dogfood-logs/313-gate1-run{1,2}/` for the
  > original crash.
  >
  > Related: #181, #217, #231, #248, #275, #298, #306, `DR-302`.
- **Status:** **FILED** — #317's title and body replaced on 2026-08-29. Approved
  at #317's Gate 1.

### [2026-08-29] A continued run does not merely orphan an obligation — it inverts a replaced scope exclusion

- **Kind:** filing
- **Found during:** #317, Gate 1 (`dogfood-logs/317-gate1-run{4,5}/`)
- **Where:** `src/acceptance/requirement/` — the `--continue` carry path (#269's
  mechanism), already filed as #306
- **Severity:** should-fix
- **What's wrong:** #306 records that a continued run keeps an obligation whose
  source sentence was deleted, leaving it tracing to no text. This instance is
  worse. `current-task.md` was replaced wholesale, and run 4
  (`--continue 40c12c90018b3526`) produced, for `exclusion-04` — *"Combining
  obligations that state the same thing as one another"*, a **scope exclusion** —
  the obligation `combine-agreeing-accounts-2`: *"The review combines agreeing
  accounts of the same requirement into one account and carries on."* That
  requires the delivered change to do the excluded work. `completion-06`
  likewise kept the id `combined-agreeing-accounts-stop-review` from the
  replaced mandate while printing a description about summary spans.

  The fresh run over identical text (`0b7c947eb8c27f5c`, run 5) yields
  *"The change does not alter combining obligations that state the same thing as
  one another"* — correct. So the decomposer reads the new text correctly and
  the carry is what inverts it.
- **Why I didn't act:** #306 is the issue for this path and out of scope for
  #317; and `--continue` was the wrong flag here anyway, since #269's carry
  exists to hold an obligation stable across a **rewording**, not a replacement.
- **Drafted fix:** an `add_issue_comment` on **#306**:

  > A stronger instance from #317's Gate 1, where the carried obligation does not
  > merely orphan — it **inverts** the requirement.
  >
  > `current-task.md` was replaced wholesale between the runs. Run 4 continued
  > from the previous mandate's run; run 5 was fresh over identical text.
  >
  > | | `exclusion-04` text | derived obligation |
  > |---|---|---|
  > | run 4, `--continue` | Combining obligations that state the same thing as one another. | The review combines agreeing accounts of the same requirement into one account and carries on. |
  > | run 5, fresh | Combining obligations that state the same thing as one another. | The change does not alter combining obligations that state the same thing as one another. |
  >
  > Run 4's obligation requires the delivered change to do the work the mandate
  > **excludes**. `completion-06` in the same run kept the id
  > `combined-agreeing-accounts-stop-review` from the replaced mandate while
  > printing a description about summary spans, so the id no longer names what
  > the obligation says either.
  >
  > Suggested guard: a carried obligation whose requirement's text has been
  > replaced rather than reworded is dropped, and the requirement re-derived. The
  > ledger already records `derivation` and `revision_reason`, so the signal is
  > present.
  >
  > Logs: `dogfood-logs/317-gate1-run{4,5}/`.
- **Status:** **FILED** as a comment on #306 on 2026-08-29
  (`#306#issuecomment-5463979670`). Approved at #317's Gate 1.

### [2026-08-29] The shared preamble orphans every stage's transcripts at once, and #317 measured what that costs

- **Kind:** filing
- **Found during:** #317, Gate 2
- **Where:** `src/acceptance/request_blocks.py::SHARED_PREAMBLE`
- **Severity:** should-fix — a fact about sequencing, not a bug in the code
- **What's wrong:** CLAUDE.md says a change to common request-assembly moves
  every stage's key at the same time. #317 is the first change to make one, and
  the cost was measured rather than estimated. Reverting the preamble alone and
  re-running `tests/prompts` gave 21 passed / 28 errors; with the new preamble,
  15 passed / 6 failed / 28 errors. The 28 errors are #317's own prompt and
  schema edits orphaning the decomposition and linking corpora — unavoidable.
  The 6 are the disposition-prompt corpus and the corpus-mechanism tests,
  orphaned purely by the shared preamble, on stages #317 does not touch.
- **Why I didn't act:** the preamble change is required by #317's own mandate —
  the old sentence told the model material came before instructions, which
  `assemble` contradicts — and it is done. What is queued is recording the
  measurement where the next person planning a shared-prefix change will find it.
- **Drafted fix:** an `add_issue_comment` on **#265**, the prompt-cache work
  that owns `request_blocks.py`:

  > #317 made the first edit to `SHARED_PREAMBLE` and measured what a shared
  > request-assembly change costs, by reverting the preamble alone and
  > re-running `tests/prompts`:
  >
  > | preamble | tests/prompts |
  > |---|---|
  > | old text | 21 passed, 28 errors |
  > | new text | 15 passed, 6 failed, 28 errors |
  >
  > The 28 errors are #317's own decomposition and linking prompt edits. The 6
  > extra are the disposition corpus and the corpus-mechanism tests, on stages
  > #317 never touches — the shared-prefix cost, isolated.
  >
  > The committed corpus also grew from 7 transcripts to 25, because derivation
  > went from batches of eight to one call per requirement. A future shared
  > change re-records all 25, not 7.
- **Status:** open

### [2026-08-29] Two decomposition-prompt quality assertions now fail and are held as strict xfails

- **Kind:** filing
- **Found during:** #317, Gate 2 (the re-recorded prompt corpus)
- **Where:** `tests/prompts/test_decomposition_prompt.py`
- **Severity:** should-fix — decomposer judgement, which #317's mandate excludes
- **What's wrong:** on the corpus recorded against the new prompts, two
  long-standing quality assertions fail:
  1. `constraint-02` ("The export escapes embedded commas in the customer
     name") yields its own behaviour obligation **and** a second one typed
     `test_demand` restating `completion-02`, which is what demands a test of
     it. `findings.md` §9 predicts exactly this: constraining `source_quote` to
     the answering requirement's spans makes an obligation about another
     requirement unsourceable but not unwritable, so misattribution degrades to
     duplication. This is that residue, observed.
  2. `exclusion-01` writes its `observable_behavior` as *"...the CSV export's
     supported-currency behavior is **unchanged**..."*. The prompt forbids
     "preserve", "keep", "maintain" and "unchanged" in that field by name. The
     `description` is correct, so this is the milder half of #219.
- **Why I didn't act:** *"Whether the obligations derived for a requirement are
  the right ones for it"* is a Scope exclusion of #317's mandate. Both are held
  visible as `xfail(strict=True)` naming the cause, the pattern CLAUDE.md
  records for #152, so each fails the moment it is fixed.
- **Drafted fix:** a new issue, child of **#181** (the decomposition-quality
  umbrella), labels `bug`, `track:checker`:

  > **Title:** One requirement per call leaves the paraphrase residue #317
  > documented, and it is now visible in the prompt corpus
  >
  > #317 constrained `source_quote` to the answering requirement's own spans, so
  > an obligation about a different requirement cannot be sourced from one. It
  > can still be *written*: the model paraphrases the other requirement while
  > quoting its own text. `findings.md` §9 says so explicitly and calls the
  > result duplication rather than misattribution — the milder failure, and the
  > linking stage's existing job.
  >
  > It is now observable rather than predicted. On the corpus recorded at #317,
  > `constraint-02` of `tests/prompts/test_decomposition_prompt.py`'s invoice
  > task yields two obligations: the behaviour, and a `test_demand` restating
  > `completion-02`. Linking did not merge them.
  >
  > Held by `xfail(strict=True)` on that parameter, so it fails when fixed.
  >
  > A second, unrelated slip in the same corpus: `exclusion-01`'s
  > `observable_behavior` says the supported-currency behaviour is "unchanged",
  > which the prompt forbids in that field by name. Also held as a strict xfail.
- **Status:** open

### [2026-08-29] The `decompose` command still does not pass its unusable-answer log to `decompose`

- **Kind:** defect
- **Found during:** #317, while wiring the summary step
- **Where:** `src/acceptance/cli.py::run_decompose`
- **Severity:** should-fix — Gate 1 loses diagnostics it already renders
- **What's wrong:** `run_decompose` builds an `UnusableAnswerLog`, passes it to
  `link_duplicate_obligations`, and renders it — but calls
  `decompose(parsed, client, prior=prior)` without it. So every unusable answer
  derivation records is dropped on the `decompose` path, and only linking's
  reach the reader. `run_check` passes it correctly, so the two commands report
  different things about the same stage. #317 adds more for it to drop: a
  quotation outside its requirement, and a summary partition that could not be
  used.
- **Why I didn't act:** it is a one-argument fix on a line #317 already touches,
  but it changes what Gate 1 prints, which is outside this issue's scope.
- **Drafted fix:** pass the log through —
  `derived = decompose(parsed, client, unusable, prior=prior)` — and add a test
  that a decomposition recording an unusable answer has it rendered by
  `acceptance decompose`. File as a child of **#181**, labels `bug`,
  `track:checker`.
- **Status:** open
