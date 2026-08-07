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

**None.** #217 landed (`1c71535`, PR #221) and #218 landed (`1ea8904`, PR #222),
both with CI green. `main` is clean, 781 tests pass.

`current-task.md` holds #218's mandate — it refers back to a finished task,
which is expected.

## What landed

**#217 (M1.2.r2)** — a self-contradictory requirement disposition is now
unrepresentable. Three disposition shapes, each carrying only its own payload;
`UNDISPOSED` and every path assigning it deleted; reconciliation raises on a
missing requirement, a duplicate, an unknown id, or a claim naming only outputs
the response never produced. DR-202 decision 3 amended in place.

**#218** — a test recommendation exists exactly when test evidence is below
strongly-supported. Each renders inside its obligation's block; a weak
obligation with no recommendation now raises instead of vanishing.

## Start here next

**#148 is the highest-value next task**, and this session escalated it twice.
Three comments were added with live evidence.

Until now it produced honest `unsupported` readings that *blocked* gates. In
#218's Gate 2 run 4 it manufactured a **green** one:

```
12. Represent typed schemas as pydantic models.
       code evidence: addressed
         (no corresponding change)
       test evidence: strongly supported  [tier: static]
         12.1  ...::test_recommendation_round_trips_through_persistence
         12.2  ...::test_completion_result_round_trips_through_persistence
```

Both cited tests pass whether or not the schemas are pydantic. **The evidence is
inverted** — the code axis, where the answer lives, cites nothing; the test
axis, which cannot hold it, carries citations.

Two findings that reshape #148's deliverable:

- **The destination already exists.** `requires_other_evidence` is a valid
  `evidence_class` (`review_state.py:213,220`) and `verdict.py:81` already
  routes it to `needs_non_code_review`. It is simply never produced —
  `strength.py:15-18` explicitly declines to invent it and defers to a coverage
  status that does not route it either. So the work is "decide what routes into
  the existing tier", not "build a tier".
- **Open question to settle first:** is `needs_non_code_review` even the right
  verdict for a design/approach obligation? It fits "docs, visual, deploy"; it
  arguably does not fit "the import is there in the diff", which should be
  satisfiable on code evidence alone.

## Also open, filed this session

- **#219** — scope exclusions declined as `no_obligation` against the prompt's
  own instruction at `obligations.py:150`, with the reason stating the
  obligation. Fired in two consecutive Gate 1 runs. Belongs in the
  #204/#205/#206 prompt batch, where the re-record is paid once.
- **#220** (`decision`) — every carried rating change classified into three
  exhaustive cases: unchanged / changed with inputs moved / changed with inputs
  unmoved. The third is the reportable event. Classification is **computed**
  from `rerun.py::stale_obligation_ids`, so no model call and no re-examination.
  `restated` is deferred behind measurement, deliberately: v1 makes case 3
  countable, which is what a before/after comparison needs.
- **#216** — nested bullets dropped silently. **Still unstarted**; its Gate 1 is
  what set this whole session off. Re-run it now that #217 has landed;
  `dogfood-logs/216-gate1-run1/` holds the original.

## Judgement failures worth not repeating

Two dogfood recommendations were dismissed wrongly, both toward "already
covered", and both are corrected in their judgement files:

- #218's `closing-line-points-at-retrieval-command` — called a tautology
  "asserted by existing report tests". Only the *negative* branch was; the line
  the obligation names appeared in no test at all.
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
  non-comparable across it — and it silently re-derived #218's obligation set
  mid-review: byte-identical task file, 12 of 14 obligations reworded.
- **A stable obligation count can conceal a total re-split.** Compare aligned
  sets, not counts.
- **Test doubles returning `[]` no longer parse** for decomposition or
  recommendations. `tests/support.py::_completed` fills both from the ids the
  call supplied, read off the outgoing schema's enum via `_supplied_enum`.
- **A text search for a removed symbol flags its own explanation.** Use an AST
  walk so the docstrings recording *why* survive.

## Traps

- **`decompose|check --mode record` writes nothing to stdout when redirected.**
  Record once, then re-run in replay to capture.
- **A commit subject starting with `#` is deleted during `rebase --continue`.**
  `git commit -m` uses `--cleanup=whitespace` and keeps it; rebase re-reads
  `COMMIT_EDITMSG` under `--cleanup=default` and strips it as a comment. Put the
  issue ref at the end: `Subject line (#218)`.
- **Two branches adding a helper to the same file in different regions
  auto-merge cleanly and silently.** #217 and #218 both added `_completed` to
  `tests/support.py`; git reported no conflict and left two definitions, the
  second shadowing the first. Grep for duplicate `def` after any rebase.
- **Python here is 3.10** — no `enum.StrEnum`. Use `(str, Enum)`.
- **The repo is `alipeles/acceptance-review`**, not the local dir name.
- **`gh api ... -f` sends strings**; sub-issue ids need `-F` for integers.
- **Adding a sub-issue returns the PARENT**, so `-q .number` echoes the umbrella.

## Known open, not the next task's problem

**#210**, **#180**, **#193**, **#153**, **#191**, **#196**, **#178**, **#214**,
**#129**.

## What to ignore

- **`.acceptance/cache/`** — transcripts and cached reviews, regenerable.
