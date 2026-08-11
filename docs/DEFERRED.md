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
- **Why I didn't act:** it is a process question about how this repo dogfoods,
  not a defect in the tool, and resolving it quietly is forbidden.
- **Drafted fix:** **recommendation — commit process artifacts on a separate
  branch or after the gate**, so the reviewed diff holds only the change under
  review. **Rejected alternative:** teach the tool to ignore known bookkeeping
  paths, which makes the tool aware it is being dogfooded and violates the
  standing rule that it must never be. A third option, accepting the noise, is
  what happens today.
- **Status:** open

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
