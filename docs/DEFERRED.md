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

### [2026-08-10] Duplicate-description comparison is exact, not normalised
- **Kind:** decision
- **Found during:** #248, Gate 1
- **Where:** `src/acceptance/requirement/obligations.py`, `decompose`
- **Severity:** should-fix
- **What's wrong:** #248 leaves open whether two obligation descriptions count as
  duplicates on exact string equality or after normalising case, whitespace and
  a trailing period.
- **Why I didn't act:** resolving a design decision quietly is forbidden; it is
  queued with a recommendation rather than stopping the work.
- **Drafted fix:** **exact equality.** It covers the observed case — the two
  descriptions in #248 are byte-identical — and cannot collapse two obligations
  that differ in meaning, which a normalising comparison eventually will. The
  issue itself recommends starting exact. **Rejected alternative:** normalise
  first, which would catch a near-miss duplicate but makes the drop a judgement
  call, and a wrongly dropped obligation is the failure this project treats as
  worst (#202, #214). If normalisation is wanted later it is a separate change
  with its own evidence.
- **Status:** open

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
- **Status:** open
