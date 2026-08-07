# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed, so it survives a context reset or a machine change — but still a
scratch record, not a plan. **The GitHub issue stays authoritative** (#168).
Clear it out when the task lands rather than letting it accrete.

*Last updated: 2026-08-07*

---

## Task in flight

**#216** — nested bullets and multi-paragraph list items dropped silently, and
the unread-source guard reports zero. Child of #181, board order 413.05.

**Gate 1 run 2 did not pass**, at `efa2cab`. Run saved to
`dogfood-logs/216-gate1-run2/`. No code written. **Awaiting a human decision on
whether to proceed** — see *The open decision* below.

## Gate 1 run 2 — what it found

`Requirements: 29   with obligations: 28   deliberately none: 1`, no
unaccounted-for line. All findings verified against the recorded response
(`.acceptance/cache/transcripts/9c83cd8d…json`), not the rendering.

Three defects, all attributed to the tool, all now tracked:

1. **#223 (new, child of #181)** — `constraint-11` ("Typed schemas are pydantic
   models") and `constraint-12` ("Tests issue no live model calls") both
   dispositioned `yielded` onto `obligation-region-level-total-coverage-tests`,
   which states neither. **No obligation in the set states either.** The content
   is gone and `with obligations: 28` counts them as read.
2. **#210** — all five scope exclusions over-merged onto another requirement's
   obligation, 5 of 5. Evidence commented on the issue.
3. Redundant obligation: `…region-level-total-coverage-tests` restates
   constraint-06/07/08's three obligations, and is then what absorbs
   constraint-11/12. Recorded on #223; touches #144 (inverted) and #193.

**None attributable to task-file wording.** Both absorbed bullets are
word-for-word from #218's task file, where each yielded its own obligation —
same code, model and seed.

**Zero open questions**, second consecutive run on this file, on a task file that
explicitly states a design fork as undecided. Noted against #206.

## The open decision

Whether to proceed to implementation on this breakdown. The tension is real:

- **Against** — CLAUDE.md Gate 1 step 2 says do not proceed past a breakdown you
  would not defend, and two requirements' content is stated by no obligation.
  (Both *are* linked to one — the log shows no gap. The obligation just doesn't
  say what they say. Read the obligation text, not the arrow.)
- **For** — the substance of #216 is covered faithfully by the 13 obligations
  (both deliverable halves, the region-coverage invariant, both regression
  cases, the reproduction, the design decision). The damage is confined to two
  cross-cutting hygiene constraints and five exclusions, none of which is
  #216's actual work.

Separately, and honestly: `constraint-11` may be **inapplicable boilerplate**
here — #216 concerns spans and parse coverage and may introduce no new typed
schema. Reconsidering that bullet is legitimate authoring; it is *not* the
disposition of finding 1, and must not be used as one.

## Also open, filed earlier this session-block

- **#219** — exclusions declined as `no_obligation`. Did **not** fire in run 2;
  the opposite did. Commented: exclusions fail in two opposite directions and
  which one fires is unstable across task files. Wants one measure and one fix
  pass with #210.
- **#220** (`decision`) — carried rating changes classified into three exhaustive
  cases; case 3 is the reportable event, computed from
  `rerun.py::stale_obligation_ids`.

## Carry this warning through the #181 block

**#148 sits at 414.5, behind all of it, and until it lands a clean Gate 2 can be
false.** In #218 it manufactured a green one:

```
12. Represent typed schemas as pydantic models.
       code evidence: addressed
         (no corresponding change)
       test evidence: strongly supported  [tier: static]
```

Both cited tests pass whether or not the schemas are pydantic. **The evidence is
inverted** — the code axis, where the answer lives, cites nothing; the test axis,
which cannot hold it, carries citations. Three comments on #148 hold the
evidence.

Note the same bullet is now implicated in #223. It is a reliable troublemaker.

Two findings that reshape #148's deliverable when it comes up:

- **The destination already exists.** `requires_other_evidence` is a valid
  `evidence_class` (`review_state.py:213,220`) and `verdict.py:81` already routes
  it to `needs_non_code_review`. It is simply never produced —
  `strength.py:15-18` declines to invent it and defers to a coverage status that
  does not route it either. The work is "decide what routes into the existing
  tier", not "build a tier".
- **Settle first** whether `needs_non_code_review` is even the right verdict. It
  fits "docs, visual, deploy"; it arguably does not fit "the import is there in
  the diff", which should be satisfiable on code evidence alone.

## Judgement failures worth not repeating

Dogfood recommendations dismissed wrongly, all toward "already covered":

- #218's `closing-line-points-at-retrieval-command` — called a tautology
  "asserted by existing report tests". Only the *negative* branch was.
- #217's `pydantic-typed-schemas` — reported as a mapping miss (#182) because a
  test matched the recommendation's prescription. That test would pass whether
  or not the obligation held.

**The shape**: naming a test that *resembles* the recommendation without
checking it would fail if the obligation were violated. Surrounding instability
makes "probably noise" an easy and wrong default — DR-180's warning is exactly
this.

## Do not rediscover

- **A pydantic tagged union cannot go on the wire.** `Field(discriminator=...)`
  renders `oneOf` + `discriminator`; strict mode accepts neither, and
  `inline_schema_refs` leaves the mapping pointing at `$defs` it just inlined.
  Plain `Union` renders `anyOf`; `Literal` tags still disambiguate.
- **"At least one" cannot be `min_length`** — strict mode rejects `minItems`.
  Use a required scalar beside a list (`obligation_id` + `more_obligation_ids`).
- **`request_key` hashes the response schema** (`llm.py:81-87`). #217 paid this
  for the whole decompose corpus, so decomposition-accuracy figures are
  non-comparable across it.
- **A stable obligation count can conceal a total re-split.** Compare aligned
  sets, not counts. And `with obligations: N` counts *dispositions, not
  coverage* — #223 is exactly that gap.
- **Test doubles returning `[]` no longer parse** for decomposition or
  recommendations. `tests/support.py::_completed` fills both from the ids the
  call supplied, read off the outgoing schema's enum via `_supplied_enum`.
- **A text search for a removed symbol flags its own explanation.** Use an AST
  walk so the docstrings recording *why* survive.

## Traps

- **`decompose|check --mode record` writes nothing to stdout when redirected.**
  Record once, then re-run in replay to capture.
- **A commit subject starting with `#` is deleted during `rebase --continue`.**
  Put the issue ref at the end: `Subject line (#218)`.
- **Two branches adding a helper to the same file in different regions
  auto-merge cleanly and silently.** Grep for duplicate `def` after any rebase.
- **Python here is 3.10** — no `enum.StrEnum`. Use `(str, Enum)`.
- **The repo is `alipeles/acceptance-review`**, not the local dir name.
- **`gh api ... -f` sends strings**; sub-issue ids need `-F` for integers, and
  the id is the REST `.id`, not the issue number.
- **Adding a sub-issue returns the PARENT**, so `-q .number` echoes the umbrella.
- **`cd` inside a Bash call persists to the next call.** `cd` back, or use
  absolute paths.

## Known open, not the next task's problem

**#210**, **#180**, **#193**, **#153**, **#191**, **#196**, **#178**, **#214**,
**#129**, **#223**.

## What to ignore

- **`.acceptance/cache/`** — transcripts and cached reviews, regenerable.
