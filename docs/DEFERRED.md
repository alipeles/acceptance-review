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

### [2026-08-10] What exempts a declined requirement from the coverage bound
- **Kind:** decision
- **Found during:** #214, Gate 1
- **Where:** `src/acceptance/verdict.py` (new coverage bound), reading
  `RequirementMap.unyielding()`
- **Severity:** blocker
- **What's wrong:** #214's Acceptance items 2 and 4 are in direct tension. Item 2:
  *"A review in which requirements produced no obligation cannot return
  `no_material_gaps`."* Item 4: *"A task file whose only unyielding requirement is
  a bare section marker is not penalised."* Both can hold only if some declines
  are exempt from the bound, and the issue does not say which — its Deliverable is
  explicitly *"Not settled"*. It gives the discriminator in prose only: *"nine of
  ten scope exclusions declining with one boilerplate reason is not the same as
  one section marker."*
- **Why I didn't act:** picking silently would resolve an open design decision
  inside the code, which CLAUDE.md forbids; the recommendation below is
  implemented, and this entry is the surfacing.
- **Drafted fix — recommended: structural exemption.** A `no_obligation` decline
  is exempt from the bound only when the requirement's own text is structurally
  non-normative, decided in code from the parse, never from the model's reason:
  normalized text of ≤3 words with no terminal punctuation. `- Implementation`
  (1 word) is exempt; `The change does not alter X` (6 words) is not. Deterministic,
  needs no NLP dep, and — the point — it judges *the requirement*, not the
  decomposer's story about it, so a decomposer cannot talk its way out of the
  bound. Gate 1 run 1 supplies the live fixture: `completion-01` is exactly this
  case, declined as *"A standalone section marker with no requirement under it."*
  **Its weakness, stated plainly:** a word count is a crude proxy for "states no
  checkable expectation", and a terse real requirement (`- Idempotent retries`)
  would be wrongly exempted. It fails toward *under*-bounding, which is the
  permissive direction #214 exists to close — so it is the part to revisit first
  if the bound proves too weak in practice.
- **Alternative rejected — uniformity of the decline reason.** Count declines
  whose normalized reason is shared by 2+ requirements as systemic (a rule the
  decomposer applied), and exempt a decline whose reason is unique. This is what
  the issue's own prose gestures at, and it fires exactly on the #202 evidence.
  Rejected on two grounds: it is evadable by varying the wording, and — worse —
  it lets a *single* silently-dropped real requirement through unbounded, which
  is the common case and the one item 2 is written to catch.
- **Status:** open

### [2026-08-10] #214 names a requirement disposition that no longer exists
- **Kind:** filing (comment on #214)
- **Found during:** #214, Gate 1
- **Where:** `src/acceptance/review_state.py:311` (`Disposition`), `:399`
  (`RequirementMap.unyielding`), `:385` (`unread_source`)
- **Severity:** should-fix (it changes what #214's Deliverable can mean, not
  whether it is achievable)
- **What's wrong:** #214's Deliverable says *"A requirement disposed `undisposed`
  is a gap — the decomposer failed to read it, which is unambiguous."* There is no
  `undisposed`. `Disposition` has exactly three values — `yielded`,
  `no_obligation`, `open_question` — and M1.2.r2 deliberately removed the fourth:
  a response that fails to account for a requirement no longer parses, so no
  `RequirementMap` containing one exists to query. The docstring says so directly.
  The Deliverable bullet therefore describes a state the verdict can never see,
  and taken literally it is unimplementable.
- **Why I didn't act:** editing the issue body is a backlog write, and this is a
  judgement about what the issue meant, which is the human's call.
- **Drafted fix — comment to post on #214:**

  > **`undisposed` no longer exists (M1.2.r2).** The Deliverable's second bullet —
  > *"A requirement disposed `undisposed` is a gap"* — refers to a `Disposition`
  > value that was deliberately removed. There are exactly three, and a response
  > that leaves a requirement unaccounted for is rejected at parse rather than
  > recorded, so the verdict can never observe one. See `Disposition`'s docstring
  > in `review_state.py`.
  >
  > **`unread_source` is the surviving carrier of that meaning.** Task-file text
  > that became no requirement at all is still recorded, still unambiguous data
  > loss, and still invisible to the verdict — the same defect this issue is
  > about, one hop earlier in the chain (source text → requirements →
  > obligations). #214 is being implemented reading the bullet's *intent* onto
  > `unread_source`: a non-empty `unread_source` bounds the verdict exactly as an
  > obligation-free requirement does. Flagging it because that is an
  > interpretation of the Deliverable, not a literal reading of it.
  >
  > The other three Acceptance items are unaffected.
- **Status:** open
