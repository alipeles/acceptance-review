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

Branch **`216-parser-accounts-for-blocks`**. Design was settled beforehand in
`docs/DR-216-parser-accounts-decomposer-splits.md`; implementation followed it
without re-deriving anything.

**Gate 2 closed by attribution** — it never came back clean, and every remaining
finding is a filed tool defect (#223, #173, #180, #225), not a gap in the work.
See *Where it stands* below.

## What landed

| commit | what |
|---|---|
| `2ae0fed` | the parser change + fixtures + coverage assertion |
| `77ae7cb` | Gate 2 run 1 fixes: count-insensitivity test, DR-216 decision-record tests |
| `616f505` | Gate 2 run 2 fix: the pre-#216 parse pinned as a regression |
| `63acea6` | three dogfood logs with judgements |
| `e1c0e8a`+ | session state, attributions recorded |

`parse_task_file` now descends into lists and list items, emitting one span per
leaf block. Nested content gets its own requirement (DR-216 decision 2); block
type is never judged (decision 3).

Full suite green at **840**; `ruff` clean.

## Two facts worth not re-deriving

**Every committed task file parses byte-identically** across the change —
verified by dumping both parses from a HEAD worktree and diffing. **No recorded
transcript is invalidated**, so decomposition-accuracy figures stay comparable.
The method is worth repeating for any future parser change.

**The real corpora cannot falsify the coverage guard.** Zero nested bullets in
`current-task.md`, every `dogfood-logs/*/current-task.md`, and all of
`tests/fixtures/decompose-stability/`. Hence `tests/fixtures/nested-blocks/`,
and hence `test_each_purpose_built_fixture_actually_exercises_nesting`, which
fails a fixture that could not tell the fixed parser from the broken one.
Verified empirically: run against the pre-#216 parser, **all five fixtures fail
and both real corpora pass**.

## Where it stands — Gate 2, three runs, still not clean

Runs at `2ae0fed`, `77ae7cb`, `616f505`, all in `dogfood-logs/216-gate2-run*/`.
Mapping checked before the verdict each time (DR-164); it was dense and accurate,
never half-blind.

**Runs 1 and 2 each found a real gap and each was addressed.** Both were worth
having:

- the coverage assertion was never exercised against a parse that was right on
  one axis and wrong on the other, so nothing showed it sees what a count
  cannot;
- run 2 then sharpened that correctly — a *damaged span* is not #216's shape; a
  *dropped block* with every remaining span exact is. Now pinned.

**Run 3 found nothing attributable to the work, and moved backwards.** Five
findings, up from two, after a commit that only strengthened the suite. Three
obligations lost a tier while their evidence improved:

- committed-task-files coverage: strongly → nominally on a **byte-identical
  mapped set** — the cleanest instance of #180 seen so far;
- decompose-stability coverage: strongly → nominally, having lost one mapped
  test that did not change;
- decision-recorded-in-repository: strongly → partially **after** gaining the
  three on-point `test_dr_216_*` tests, with a recommendation prescribing
  `test_dr_216_records_the_nested_content_decision_as_resolved` — a test **in
  its own mapped set**.

**My judgement: the implementation is complete and correctly evidenced, and the
gate cannot say so.** That claim is the human's to check, not mine to act on.

## The four attributions — reviewed, approved, filed

Gate 2 never came back clean. The branch moved forward under CLAUDE.md's second
permitted disposition: attributed to a tool defect, backlog item filed first.

| finding | tracked as |
|---|---|
| `constraint-11`/`constraint-12` absorbed into an obligation stating neither, **all three runs, same obligation id** as Gate 1 run 2 — deterministic, not noise | #223 (comment 5220684032) |
| prescribed test supplied, mapped accurately to five neighbours, withheld from the obligation that asked | #173 (comment 5220724039) |
| two ratings fell, one on a **byte-identical mapped set** | #180 (comment 5220738963) |
| rating falls as evidence improves; recommendation names a test in its **own** mapped set | **#225**, new child of #183 |

#225 is the one to read first — it is the residual failure mode left once #180
and #173 are fixed, which is why it needed its own item rather than a comment.

## Judgement failures worth not repeating

**Run 2 upgraded `obligation-decision-recorded-in-repository` to *strongly
supported* and it was not my fix that did it.** The mapped set that run held no
`test_dr_216_*` test at all — four unrelated tests were re-scored upward. I read
the green movement as my work landing before checking the mapped set.

A green movement is not self-justifying. *"My fix landed"* has to be checked
against the mapped set exactly like a red one — and it is the direction where
checking feels unnecessary.

The older instances, same family, all toward "already covered": #218's
`closing-line-points-at-retrieval-command`, #217's `pydantic-typed-schemas`.
**The shape**: naming a test that *resembles* the claim without checking it would
fail if the obligation were violated.

## Carry this warning through the #181 block

**#148 sits at 414.5, behind all of it, and until it lands a clean Gate 2 can be
false.** In #218 it manufactured a green one: both cited tests passed whether or
not the schemas were pydantic. **The evidence is inverted** — the code axis,
where the answer lives, cites nothing; the test axis, which cannot hold it,
carries citations. Three comments on #148 hold the evidence, and `constraint-11`
is implicated again in #223 and in all three runs above. It is a reliable
troublemaker.

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

## The sequencing decision, recorded

`docs/DR-204-derivation-performs-no-linking.md`. Derivation may split a
requirement or decline it, but may **not** attach a requirement to an obligation
derived from another. Enforced as a **validator, not a prompt rule**. Human
decided: **#216, then #204 with no linking at all, then #144 owning linking.**

#204 and #144 must land adjacently: between them the obligation set is unmerged
and every downstream stage is per-obligation. #211 must score link precision over
#144's output, not derivation. #210 and #223 stay open as evidence.

## Do not rediscover

- **A pydantic tagged union cannot go on the wire.** `Field(discriminator=...)`
  renders `oneOf` + `discriminator`; strict mode accepts neither. Plain `Union`
  renders `anyOf`; `Literal` tags still disambiguate.
- **"At least one" cannot be `min_length`** — strict mode rejects `minItems`.
  Use a required scalar beside a list.
- **`request_key` hashes the response schema** (`llm.py:81-87`).
- **A stable obligation count can conceal a total re-split.** Compare aligned
  sets, not counts. `with obligations: N` counts *dispositions, not coverage*.
- **Test doubles returning `[]` no longer parse** for decomposition or
  recommendations. `tests/support.py::_completed` fills both from the ids the
  call supplied.
- **A text search for a removed symbol flags its own explanation.** Use an AST
  walk.
- **`tests/` is a namespace package** — shared helpers import as
  `tests.requirement.region_coverage`, never as a relative import. `pythonpath =
  ["."]` in `pyproject.toml` is what makes it work.

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
- **`cd` inside a Bash call persists to the next call.** Use absolute paths.

## Known open, not the next task's problem

**#210**, **#180**, **#193**, **#153**, **#191**, **#196**, **#178**, **#214**,
**#129**, **#223**, **#224**, **#173**.

## What to ignore

- **`.acceptance/cache/`** — transcripts and cached reviews, regenerable.
