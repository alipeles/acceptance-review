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

### [2026-08-10] Split #180 into children; this slice is the first
- **Kind:** filing
- **Found during:** #180, Gate 1
- **Where:** issue #180
- **Severity:** should-fix
- **What's wrong:** #180's Acceptance carries four separable pieces — per-criterion
  request isolation, the enumeration-count sensitivity in `strength.py`, the
  determinism component, and reporting an unreproducible rating. It cannot reach
  Gate 2 in one session, which `CLAUDE.md` *Working in small sessions* says is the
  signal to split the issue rather than run a longer session.
- **Why I didn't act:** the backlog is the plan; splitting an issue is a change to it.
- **Drafted fix:** file four children of **#183** (evidence judgement), and keep #180
  open as the measured evidence and corpus that they close into:
  - **#180.1 — A criterion's discrimination judgement is requested per criterion.**
    The slice in flight. Covers #180 Acceptance 1 and 2.
  - **#180.2 — `strongly_supported` requires all named defects caught, so the rating
    moves with how many defects the model chose to enumerate.** `strength.py:132-139`
    computes `caught == total`; naming one easy defect and catching it yields STRONG.
    This is the mechanism behind #180's "STRONG issued unearned" — its Acceptance 3,
    the criterion the DR calls the one that matters.
  - **#180.3 — Determinism controls become one owned component.** #180 Acceptance 5;
    overlaps #184 and may belong there instead.
  - **#180.4 — A rating that could not be reproduced is reported as such.**
    #180 Acceptance 6.
  #180 Acceptance 4 (the corpus's three real findings still found) is a verification
  condition on each child, not a child of its own.
- **Status:** open

### [2026-08-10] Mapping misses the three on-point tests for "no live model calls"
- **Kind:** filing
- **Found during:** #244, Gate 2 (`dogfood-logs/244-gate2-run1/`)
- **Where:** src/acceptance/evidence/mapping.py
- **Severity:** should-fix
- **What's wrong:** `tests-issue-no-live-model-calls` was rated **nominally supported**,
  mapped to `test_decompose_cannot_reach_a_diff_or_a_head_revision` and
  `test_decompose_replay_without_transcript_fails_cleanly` — both only loosely related.
  The three tests that directly evidence the property were not mapped at all:
  `tests/test_determinism.py::test_replay_reproduces_a_recorded_run_with_no_live_call`,
  `tests/test_llm.py::test_recorded_transcript_replays_with_zero_live_calls`, and
  `tests/test_llm.py::test_replay_without_a_transcript_raises_rather_than_calling_live`.
  The resulting recommendation asks for network-blocked execution of the suite —
  infrastructure the replay-default architecture already makes unnecessary.
- **Why I didn't act:** mapping is #182, a different umbrella, and #244's Scope
  exclusions do not cover it either way.
- **Drafted fix:** file as a child of **#182**, labels `bug`, `track:checker`.
  Title: *"An architecture-level property is rated nominally supported because its
  on-point tests are never mapped"*. Body: the evidence above, with the observation
  that the mapped set was not empty but *wrong* — so the partitioning guard from
  DR-164, which watches for shed work, cannot see this. Worth relating to the #214
  lane's evidence on #180 (`issuecomment-5245416368`), where a mapped set collapsed
  from two tests to zero on an untouched obligation: both are mapping selecting badly
  rather than judgement rating badly, which is why the umbrellas are separate.
- **Status:** open

### [2026-08-10] One requirement yields the identical obligation twice
- **Kind:** filing
- **Found during:** #244, Gate 1 re-run (`dogfood-logs/244-gate1-run2/`)
- **Where:** src/acceptance/requirement/obligations.py
- **Severity:** should-fix
- **What's wrong:** `constraint-10` ("A requirement keeps every obligation whose quotation
  lies within its span") produced two obligations with **byte-identical descriptions**,
  distinguishable only by `_unique` appending `-2` to the second id. Both are correctly
  attributed to that requirement, so #244's attribution check does not touch them. The
  pair then joins a transitive link cluster with the near-identical obligations from
  `task-01`, `constraint-02` and `constraint-03`, one pair inside it is denied, and the
  run ends with five unreconciled obligations.
- **Why I didn't act:** #244's Scope exclusions put "how many obligations one requirement
  may yield" in #117, so acting would have been working outside the mandate I gated on.
- **Drafted fix:** file as a child of **#181**, labels `bug`, `track:checker`.
  Title: *"One requirement yields the identical obligation twice, and only `_unique`
  tells them apart"*. Distinguish it from #117 in the body: this is not a granularity
  judgement but exact duplication, mechanically detectable without asking the model —
  same requirement, same description. Recommend the same enforce-in-code shape as #244:
  drop an obligation whose description already appears under the same requirement, and
  record it on `UnusableAnswerLog` so the collapse is not silent. Note that it inflates
  obligation counts, and so distorts #211's decomposition-accuracy figures.
- **Status:** open

### [2026-08-10] Decomposer re-derives other requirements' obligations under the Task sentence
- **Kind:** filing
- **Found during:** #180, Gate 1 (runs 2 and 3)
- **Where:** src/acceptance/requirement/obligations.py
- **Severity:** blocker — Gate 1 for #180 cannot pass on this breakdown
- **What's wrong:** A one-sentence Task requirement yielded seven obligations: three
  paraphrases of itself, and three that are the content of `constraint-07`,
  `constraint-08` and `constraint-09` re-derived under `task-01`. Two of those then
  collide with the obligations those constraints produced in their own right — the same
  requirement under two ids. The linking stage correctly refuses to merge on the
  contradiction, leaving eight unreconciled obligations. Deleting a redundant seven-word
  clause between runs took `task-01` from 2 obligations to 7 and the unreconciled set
  from 4 to 8. A repeat run was byte-identical, so this is stable and reproducible, not
  determinism noise.
- **Why I didn't act:** it is a decomposition defect, outside #180's area, and one
  sanctioned rewrite already made it worse — a second would be tuning the input until
  the tool agrees.
- **Drafted fix:** file as a child of **#181**, labels `bug`, `track:checker`.
  Title: *"A one-sentence Task requirement yields seven obligations, three of them other
  requirements' content"*. Body: the evidence above, pointing at
  `dogfood-logs/180-gate1-run{2,3}/` for the minimal pair and
  `180-gate1-run3/judgement.md` for the analysis. Note the connection to #180: redundant
  obligations are rated independently, so three obligations saying the same thing can
  carry three different ratings and present as rating instability even when the judge is
  perfectly consistent — meaning an unknown share of #180's measured instability may
  originate in decomposition rather than judgement. Also worth recording that the
  linking guard behaved correctly and is what made this visible.
- **Status:** open

### [2026-08-10] DR-164 decision 2 no longer holds for the discrimination stage
- **Kind:** decision
- **Found during:** #180, Gate 1
- **Where:** docs/DR-164-mapping-stage-request-partitioning.md, decision 2; src/acceptance/partition.py:14-18
- **Severity:** should-fix
- **What's wrong:** DR-164 declined to partition the diff-dominated stages, costing
  "~3.8x the tokens on stages with no observed failure." Discrimination is one of
  those stages and that clause is now false: #180, #216, #232 and #153 are four
  recorded failures on it, three of them with a byte-identical mapped set.
- **Why I didn't act:** revisiting a recorded decision is the human's call, and it is
  a cost trade rather than a correctness one.
- **Drafted fix:** partition discrimination per criterion (batch size 1, configurable
  and folded into the request key via `Batch.request_partition`). Recommended over
  the alternative of a batch size k > 1, which only dilutes the contamination instead
  of removing it and leaves the guarantee untestable. Amend DR-164 with a decision 2a
  recording that the no-observed-failure premise expired, rather than editing
  decision 2 in place. Accepted cost: N x the diff tokens on this stage, and a full
  transcript re-record.
- **Status:** open
