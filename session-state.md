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

**#217 — M1.2.r2**, branch `issue-217-disposition-unrepresentable`, three commits
(`76b847b`, `007966f`, `6c06517`). Not pushed, no PR.

**Gate 2 is NOT clean.** Do not open a PR. See *Where it stands* below.

## How #217 came to exist

#216 was the intended task. Its **Gate 1 never passed**: 8 of 31 requirements
came back `yielded` with an empty id list. The transcript showed the model had
supplied a substantive `no_obligation` reason for every one, and
`_requirement_map` discarded it because the label disagreed with the payload,
recording the requirement as unaccounted-for instead.

So the fourth disposition `M1.2.r1` added, `UNDISPOSED`, was turning malformed
responses into soft findings that still reached a verdict. #202 is correctly
closed — its acceptance genuinely passed — and #217 supersedes it.

**#216 is still open and still unstarted.** Its Gate 1 must be re-run after #217
lands; the run that exposed all this is in `dogfood-logs/216-gate1-run1/`.

## What #217 delivered

- three disposition shapes, each carrying only its own payload; `UNDISPOSED` and
  every path assigning it deleted
- reconciliation raises `SchemaValidationError` on a missing requirement, a
  duplicate, an unknown id, or a claim naming only outputs never produced
- a supplied reason is preserved, never replaced by a diagnostic
- `constrain()` walks unions — **without this the `requirement_id` constraint
  would have vanished silently** under the new shape, with every test still green
- DR-202 decision 3 amended in place

772 tests pass, ruff clean.

## Two things not to rediscover

- **A pydantic tagged union cannot go on the wire.** `Field(discriminator=...)`
  renders `oneOf` + `discriminator`; OpenAI strict mode accepts neither, and
  `inline_schema_refs` leaves the mapping pointing at `$defs` it just inlined.
  Plain `Union` renders `anyOf`, which works; `Literal` tags still disambiguate.
- **"At least one" cannot be `min_length` either** — strict mode rejects
  `minItems`. It is a required scalar field beside a list (`obligation_id` +
  `more_obligation_ids`), so the guarantee is carried by the shape.

## Where it stands — the 5 open findings

Gate 2 run 3 (`6ae97fd` → `6c06517`): INCOMPLETE, 5 obligations with
non-discriminating test evidence. Down from 11 → 7 → 5. Nothing unaddressed, no
`separable` change, mandate coverage correct.

Judgement in `dogfood-logs/217-gate2-run3/judgement.md`. In short:

- **2 are meta-obligations** — the task file asks that *a test exist*, so the
  evidence stage is hunting for a test proving a test exists. Probably a
  task-file authoring fix: state the behaviour, not the artifact.
- **3 have direct, on-point tests** and still read non-discriminating. Whether
  that is #183 (judgement) or #182 (mapping) is **not established** — check the
  mapping transcript before assuming (DR-164).

Each of the five needs a fix or a filed defect before a PR. None may be waived.

Run 3's recommendation 2 is worth writing regardless: union members carrying
*misleading* fields, which `extra="forbid"` turns into the strongest proof that
dispatch is by literal tag alone.

## Still open from the same root

**The decomposer declines scope exclusions outright** — 7 of 8 in #216's Gate 1,
against the instruction already at `obligations.py:150`. #217 makes those
declines visible and reasoned; it does not make them right. **Not yet filed.**
Belongs in the #204/#205/#206 prompt batch, where the re-record is paid once.

## The re-record cost was paid

`request_key` hashes the response schema (`llm.py:81-87`), so changing
`_RequirementDisposition` invalidated **every** recorded decompose transcript.
Decomposition-accuracy figures are non-comparable across this change.

## Known open, not this task's problem

- **#210** — false links; fired again in #217's own Gate 1 (five exclusions
  linked to an obligation that does not state them).
- **#216** — nested bullets dropped silently; unstarted.
- **#153**, **#191**, **#196**, **#178**, **#193**, **#214**, **#129**.

## Traps

- **`decompose|check --mode record` writes nothing to stdout when redirected.**
  Record once, then re-run in replay to capture. Cost real time this session.
- **A text search for a removed symbol flags its own explanation.** Use an AST
  walk for "no code references X" so the docstrings recording *why* survive.
- **Test doubles returning `requirement_dispositions: []` no longer parse.**
  `tests/support.py::declining_dispositions` completes them from the ids the
  call supplied, read off the outgoing schema's enum.
- **Python here is 3.10** — no `enum.StrEnum`. Use `(str, Enum)`.
- **The repo is `alipeles/acceptance-review`**, not the local dir name.
- **`gh api ... -f` sends strings**; sub-issue ids need `-F` for integers.
- **Adding a sub-issue returns the PARENT**, so `-q .number` echoes the umbrella.

## What to ignore

- **`.acceptance/cache/`** — transcripts and cached reviews, regenerable.
