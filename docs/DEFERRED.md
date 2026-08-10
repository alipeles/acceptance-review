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

### [2026-08-10] One spurious link stops a genuine duplicate from merging
- **Kind:** filing (new issue, child of #181)
- **Found during:** #214, Gate 1 run 2
- **Where:** `src/acceptance/requirement/linking.py:382` (`_confirmed_clusters`)
- **Severity:** should-fix
- **What's wrong:** de-duplication asks the model pairwise "same requirement?",
  then merges confirmed clusters. When a cluster is transitively linked but one
  pair inside it was denied, the cluster is inconsistent and **nothing in it is
  merged**. So a single false link can prevent a correct merge that had nothing
  to do with it. Observed live: `constraint-05` and `completion-06` produced two
  functional obligations with byte-identical descriptions ("An open question the
  change does not answer yields no obligation.") and stayed unmerged, because
  `exclude-split-granularity` — from an unrelated scope exclusion — was linked
  into the same cluster. Six other constraint/completion pairs in the same run
  merged correctly, so the pattern is sound and this is not a task-file wording
  problem.
- **Why I didn't act:** `requirement/linking.py` is decomposition, outside
  #214's area, and #214's obligation set is usable with the redundancy present.
- **Drafted fix — issue body as it would be filed:**

  > **Title:** One spurious link blocks a correct merge: an inconsistent cluster
  > merges nothing, so a false positive protects a true duplicate
  >
  > Child of #181. Found in #214's Gate 1 run 2
  > (`dogfood-logs/214-gate1-run2/`).
  >
  > `_confirmed_clusters` treats a transitively-linked cluster containing any
  > denied pair as inconsistent and merges **none** of it
  > (`linking.py:382-396`). The intent is sound — do not guess which answer to
  > believe — but the failure mode is inverted: **the presence of a false link
  > preserves a true duplicate.**
  >
  > Observed on an ordinary mandate. Three obligations formed one cluster:
  >
  > | obligation | from | relationship |
  > |---|---|---|
  > | `constraint-05-unanswered-open-question-yields-no-obligation` | constraint-05 | genuine duplicate of the next |
  > | `unanswered-open-question-no-obligation` | completion-06 | genuine duplicate of the previous |
  > | `exclude-split-granularity` | exclusion-05 | unrelated |
  >
  > The first two have byte-identical descriptions. They did not merge, because
  > the third was linked in and some pair among the three was denied. Six other
  > constraint/completion pairs in the same run merged correctly, so the
  > redundancy is caused entirely by the spurious third member.
  >
  > This is the inverse of #210 (mapping over-merges), and the same root cause
  > drives both: an over-eager `same_requirement` judgement. There it merges
  > what it shouldn't; here it drags an unrelated obligation into a cluster and
  > the conservative policy then discards a correct merge with it.
  >
  > Redundancy in the obligation set is not cosmetic — CLAUDE.md makes
  > non-redundancy a property the obligation set must have, and every downstream
  > stage judges the set. A duplicated obligation is rated twice, recommended
  > for twice, and counted twice in any coverage figure.
  >
  > **Candidate directions** (not settled): drop only the denied pair and merge
  > the rest of the cluster; or keep the all-or-nothing policy but exclude a
  > member whose links are contradicted by every other member; or re-ask the
  > contradicted pairs.
  >
  > **Acceptance**
  > - Two obligations with identical descriptions merge even when a third,
  >   unrelated obligation is linked into their cluster by one answer.
  > - A genuinely ambiguous cluster still refuses to merge rather than guessing.
  > - The reported unusable answer names which pair was denied, not only the
  >   cluster.
  >
  > Labels: `bug`, `track:checker`. Parent umbrella: #181.
- **Status:** open
