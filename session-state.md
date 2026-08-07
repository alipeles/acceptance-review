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

**Gate 1 run 2 did not pass**, at `efa2cab` — but the human reviewed it and
cleared implementation to start. Run saved to `dogfood-logs/216-gate1-run2/`.
No code written yet.

**Next action: design and implement #216.** Its own open design fork —
*is nested content a requirement in its own right, or a continuation of its
parent?* — is undecided and is part of the issue. Both are defensible; #216 says
what is not defensible is the current behaviour, which is neither.

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

## #216's design is settled — `docs/DR-216-parser-accounts-decomposer-splits.md`

Five decisions, all made. Implementation can start from the DR without
re-deriving anything:

1. Every leaf block (markdown-it AST node) is inside a registry span or an
   `unclaimed` span, never neither.
2. Nested content under a claimed list item gets **its own requirement**, not a
   widened parent span. Covers nested bullets and 2nd+ paragraphs in a list item.
3. **The parser never judges block type.** Nested fences, tables and bullets are
   treated alike — no "fences are illustrative" rule.
4. Splitting and declining stay with the decomposer. Both already work:
   `task-01` yielded 4 obligations; `completion-01` was declined with a reason.
5. The coverage assertion needs **purpose-built fixtures**.

**Why 5 matters:** the repo's task files contain **zero nested bullets** —
verified across `current-task.md`, every `dogfood-logs/*/current-task.md`, and
all of `tests/fixtures/decompose-stability/`. #216's acceptance item "runs over
the repository's own committed task files" would pass **vacuously** without new
fixtures. Fixtures must exercise nested bullets, multi-paragraph list items,
nested fences and nested tables.

**#216's body contradicts itself** and the DR resolves it: its `Open:` paragraph
offers "own requirement vs continuation of parent", its Acceptance offers "five
requirements vs two plus three unread". Continuation yields two-and-nothing-
unread, which the Acceptance does not admit. **The Acceptance stands as written
— five requirements.**

**#224** filed (child of #181): nothing detects when the decomposer under-splits
a block. Out of #216's scope, not closable by the parser. Measure first.

## Decision taken — proceed with #216

Human decided: **finish #216, then #204 with no linking at all, then #144 owning
linking.** Recorded in `docs/DR-204-derivation-performs-no-linking.md`.

Gate 1's findings are all attributed and tracked, and the substance of #216 is
covered faithfully by the 13 obligations — both deliverable halves, the
region-coverage invariant, both regression cases, the reproduction, the design
fork. The damage is confined to two cross-cutting constraints and five
exclusions, none of which is #216's actual work. **Implementation may start.**

Note for reading the log: nothing is unlinked and nothing is unaccounted-for.
Both absorbed constraints carry a link to a plausible-looking obligation. The
defect is only visible by reading the obligation's text against the
requirement's. **Read the obligation text, not the arrow.**

`constraint-11` is **not** boilerplate — an earlier note calling it that is
withdrawn. It is code-evident (`BaseModel` in the diff) and is #148's canonical
case; `constraint-12` is test-evident via a network-disconnected test.

## The sequencing decision, recorded

`docs/DR-204-derivation-performs-no-linking.md`. Derivation may split a
requirement or decline it, but may **not** attach a requirement to an obligation
derived from another. Enforced as a **validator, not a prompt rule** — within a
response each obligation id appears in exactly one requirement's disposition;
violations go through `UnusableAnswerLog`. The many-to-one mapping #202
established survives, as **#144's** output rather than derivation's.

Partly reverses DR-202 decision 2, on the ground that derivation's failure is
**lossy** and a merge pass's is **noisy**. #204's partitioning alone would have
blocked every mis-link seen in run 2 (all cross a batch boundary), but batches
are contiguous runs, so within-batch adjacency — #210's trigger — stays exposed.

#204 and #144 must land adjacently: between them the obligation set is unmerged
(~29 vs 13 on run 2's file) and every downstream stage is per-obligation.

Amendments commented on #204 and #144. #211 must score link precision over
#144's output, not derivation. #210 and #223 stay open as evidence.

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
**#129**, **#223**, **#224**.

## What to ignore

- **`.acceptance/cache/`** — transcripts and cached reviews, regenerable.
