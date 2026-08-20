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
