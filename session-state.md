# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed, so it survives a context reset or a machine change — but still a
scratch record, not a plan. **The GitHub issue stays authoritative** (#168).
Clear it out when the task lands rather than letting it accrete.

*Last updated: 2026-08-06*

---

## Task in flight

**#218**, branch `issue-218-recommendations-by-obligation`, rebased onto main
after #217 landed. Not pushed, no PR.

**#217 (M1.2.r2) is merged** — `1c71535`, PR #221, CI green.

## What #218 does

A test recommendation exists exactly when an obligation's test evidence is below
strongly-supported. Two halves:

- **Placement.** Each recommendation renders inside the obligation it explains,
  on the test-evidence axis. §16 organises output by obligation "so a criterion's
  two axes sit together rather than in separate lists the reader must join by
  eye", and its example report has no recommendations block at all. In #217's
  Gate 2 the obligation and its recommendation sat ~200 lines apart, joined only
  by a `--criterion` slug appearing nowhere in the obligation's block.
- **Completeness.** `recommend_tests` kept whatever the response returned, so a
  response answering 3 of 5 weak obligations produced a report where two carried
  none — M1.2.r1's missing disposition, one stage downstream. Missing, duplicate
  and non-weak recommendations now raise.

Not in scope: whether an obligation needs test evidence at all, which is #148.

## The rebase had a silent hazard — look for it again next time

`tests/support.py` **auto-merged cleanly and was semantically wrong**. Both
branches added a `_completed` helper in different regions, so git reported no
conflict and left two definitions; the second shadowed the first, which would
have disabled #218's recommendation completion with nothing failing at merge
time.

Folded into one: `_supplied_enum(field, **kwargs)` walks the outgoing schema for
any id field's enum, `declining_dispositions` is built on it, and one
`_completed` handles both `requirement_dispositions` (#217) and
`recommendations` (#218). `supplied_requirement_ids` is gone — it was the
single-field version of `_supplied_enum`.

## Where #218 stands

Gate 1 passed. Gate 2 run 4 (`1c71535` → `e52a57c`) reports **NO-MATERIAL-GAPS**
— and it should not be read as a clean gate. Judgement in
`dogfood-logs/218-gate2-run4/judgement.md`.

- **Not comparable to run 3.** The task file is byte-identical, yet 12 of 14
  obligations were reworded, because #217 changed `_Decomposition`'s schema and
  `request_key` hashes it, so the decomposition was re-derived. The 3-weak → 0
  movement is not evidence the added tests closed anything.
- **One false positive.** Obligation 12, *"Represent typed schemas as pydantic
  models"* — the #148 obligation that read `unsupported` in runs 1-3 — is now
  `strongly supported`, citing two `*_round_trips_through_persistence` tests
  that pass whether or not the schemas are pydantic. `addressed` is claimed with
  `(no corresponding change)`.
- Mapping is sound (DR-164 check): 14 of 14 obligations carry mapped tests, 33
  links, measured from the persisted review.

**The work itself is complete and genuinely tested.** The unreliability is in the
tool's judgement of one obligation, not in the change.

**#148 escalated.** Until now it produced honest `unsupported` readings that
blocked gates. Here it manufactured a green one. Evidence attached to #148.

## A correction worth not repeating

Two recommendations across the two branches were dismissed wrongly, both toward
"already covered":

- #218's `closing-line-points-at-retrieval-command` was called a tautology
  "asserted by existing report tests". Only the *negative* branch was; the line
  the obligation names appeared in no test at all. Real gap, now covered.
- #217's `pydantic-typed-schemas` was reported as a mapping miss (#182) because
  a test matched the recommendation's prescription. That test would pass whether
  or not the production schemas are pydantic, so it cannot discriminate the
  obligation. It is #148.

**The shape**: naming a test that resembles the recommendation without checking
it would fail if the obligation were violated. Recorded in both judgement files.

## Filed this session, not built

- **#219** — scope exclusions declined as `no_obligation` against the prompt's
  own instruction at `obligations.py:150`, with the reason stating the
  obligation. Fired in two consecutive Gate 1 runs. Belongs in the
  #204/#205/#206 prompt batch, where the re-record is paid once.
- **#220** (`decision`) — every carried rating change classified into three
  exhaustive cases: unchanged / changed with inputs moved / changed with inputs
  unmoved. The third is the reportable event. Classification is **computed**
  from `rerun.py::stale_obligation_ids`, so no model call and no re-examination.
  `restated` deferred behind measurement.
- **#148** — this session's evidence attached. It now blocks Gate 2 on
  consecutive PRs and is the strongest candidate for the next capability task.

## Do not rediscover

- **A pydantic tagged union cannot go on the wire.** `Field(discriminator=...)`
  renders `oneOf` + `discriminator`; strict mode accepts neither, and
  `inline_schema_refs` leaves the mapping pointing at `$defs` it just inlined.
  Plain `Union` renders `anyOf`; `Literal` tags still disambiguate.
- **"At least one" cannot be `min_length`** — strict mode rejects `minItems`.
  Use a required scalar beside a list.
- **`request_key` hashes the response schema** (`llm.py:81-87`). #217 paid this
  for the whole decompose corpus; accuracy figures are non-comparable across it.
- **A text search for a removed symbol flags its own explanation.** Use an AST
  walk so the docstrings recording *why* survive.

## Traps

- **`decompose|check --mode record` writes nothing to stdout when redirected.**
  Record once, then re-run in replay to capture.
- **Python here is 3.10** — no `enum.StrEnum`. Use `(str, Enum)`.
- **The repo is `alipeles/acceptance-review`**, not the local dir name.
- **`gh api ... -f` sends strings**; sub-issue ids need `-F` for integers.
- **Adding a sub-issue returns the PARENT**, so `-q .number` echoes the umbrella.

## Known open, not this task's problem

**#148** (blocks Gate 2), **#216** (unstarted — its Gate 1 started this whole
session), **#219**, **#220**, **#210**, **#180**, **#193**, **#153**, **#191**,
**#196**, **#178**, **#214**, **#129**.

## What to ignore

- **`.acceptance/cache/`** — transcripts and cached reviews, regenerable.
