# The bundled queue

Things found mid-iteration that were deliberately not acted on at the time.
Claude queues here instead of interrupting; the queue is presented at the next
gate and worked with `/triage`. See `CLAUDE.md` *Working agreement* §4.

Entries are never deleted — a closed entry keeps its record.

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

### [2026-08-08] Scope exclusions are reframed inconsistently within one section

- **Kind:** filing
- **Found during:** #144, Gate 1
- **Where:** `src/acceptance/requirement/obligations.py` (decomposition prompt), observed in `dogfood-logs/144-gate1-run1/output.log`
- **Severity:** should-fix
- **What's wrong:** Five sibling `## Scope exclusions` bullets were split two ways by
  the same call. Three became "handled by another change and is not part of this task's
  delivered behavior" (`human_review` / `docs_config`). Two became "**Preserve** the
  scope exclusion that …" typed `invariant` — a positive obligation to keep something,
  which downstream stages will hunt for test evidence of. Positive reframing of a
  prohibition is by design; doing it to two of five siblings and not the other three is
  not, and the split does not track any difference in how the bullets are worded.
- **Why I didn't act:** decomposition prompt wording, which #144's own task file
  excludes (#205 / #206 / #219 own it).
- **Drafted fix:** File as a child of **#181** (decomposition).
  Title: *Scope exclusions in one section are reframed inconsistently — three as
  out-of-scope, two as invariants to preserve*
  Body: the five `exclusion-*` entries from `dogfood-logs/144-gate1-run1/output.log`
  quoted verbatim, with the observation that `exclusion-04` and `exclusion-05` differ
  from `exclusion-01..03` in type and framing but not in wording, and that an
  `invariant` obligation derived from an exclusion will be scored for test evidence
  that cannot exist. Labels: `track:checker`. Parent umbrella: #181.
- **Status:** filed (#230, attached to #181)

### [2026-08-08] Does the linking pass itself need partitioning?

- **Kind:** decision
- **Found during:** #144, Gate 1
- **Where:** `src/acceptance/requirement/` — the new pass
- **Severity:** should-fix
- **What's wrong:** Not a defect — an open design point DR-204 explicitly left live.
  Derivation is partitioned at 8 requirements per call (#204). This pass reasons across
  *all* obligations at once, so it cannot be partitioned the same way: a duplicate pair
  split across two batches is invisible to both. At 15 obligations partitioning was
  unnecessary; this run produced 30, and #204's Gate 2 produced 71.
- **Why I didn't act:** it is a design decision, and *Working agreement* §4.3 says
  surface rather than resolve quietly.
- **Drafted fix:** **Recommend: do not partition in #144.** Build the pass unpartitioned,
  and record the observed obligation count in provenance so the ceiling is measured
  rather than guessed. Partitioning this pass means choosing which obligations can
  possibly be compared, which is a correctness change disguised as a cost control — a
  pair in different batches is silently under-merged, and under-merging is the failure
  this issue's bias deliberately accepts, so the damage would be invisible.
  Rejected alternative: partition now by requirement-section, on the theory that
  duplicates cluster across Constraints/Completion. This run contradicts it — cluster A
  spans Task prose *and* Constraints, so section-based batching would miss it.
  If the count later forces partitioning, #211's link-precision measure should exist
  first so the loss is measurable.
- **Status:** resolved — approved, do not partition

### [2026-08-08] Record this run's duplication measurement on #144

- **Kind:** filing
- **Found during:** #144, Gate 1
- **Where:** `dogfood-logs/144-gate1-run1/`
- **Severity:** nice-to-have
- **What's wrong:** Nothing is wrong — the run is unusually good evidence for the issue
  it belongs to, and evidence like this has been lost before. The task file *for the
  de-duplication feature* is itself heavily duplicated: 30 obligations from 19 distinct
  requirements, 11 redundant.
- **Why I didn't act:** a backlog comment is a filing, and filings wait for the gate.
- **Drafted fix:** Comment on **#144** with the nine duplicate clusters, the largest
  being three obligations for "the pass runs after derivation" (`task-01`, `task-03`,
  `constraint-01`) and three for "the surviving obligation is named by every stating
  requirement" (`task-01`, `constraint-02`, `completion-02`). Note that cluster A spans
  Task prose and Constraints rather than the Constraints/Completion pairing the issue's
  Context section describes, which is a third source span shape beyond the two already
  recorded (cross-section, and single-sentence rationale from #189).
- **Status:** filed (comment on #144)

### [2026-08-08] Widen #230 — scope-exclusion handling is unstable across runs, not just inconsistent within one

- **Kind:** filing
- **Found during:** #144, Gate 1 (run 3)
- **Where:** `src/acceptance/requirement/obligations.py` (decomposition prompt)
- **Severity:** should-fix
- **What's wrong:** #230 was filed on run 1, where five sibling `## Scope exclusions`
  bullets were split three-as-out-of-scope / two-as-`invariant`. Run 3 declines all five
  uniformly and correctly. The five bullets are byte-identical across all three runs —
  only `constraint-08` and `completion-08`, in other sections, were removed. So the
  finding is sharper than filed: exclusion handling is not stably wrong, it is
  *unstable*, and run 1's inconsistency was one sample of that.
- **Why I didn't act:** prompt wording, excluded by #144's task file (#205/#206/#219).
- **Drafted fix:** Comment on **#230** with the run 1 / run 2 / run 3 decline counts
  (1 / 1 / 6), noting the exclusion bullets were unchanged throughout, and that a fix
  which only makes the five consistent within a run would not catch this. Suggest the
  acceptance gain a stability clause: the same scope exclusion receives the same
  treatment across runs whose own text is unchanged. Cross-reference **#231**, which is
  the same instability observed on a different section.
- **Status:** open
