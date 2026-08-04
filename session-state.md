# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed, so it survives a context reset or a machine change — but still a
scratch record, not a plan. **The GitHub issue stays authoritative** (#168).
Clear it out when the task lands rather than letting it accrete.

*Last updated: 2026-08-04*

---

## Task in flight

**#190 — turn the rating-stability corpus into an executable regression suite.**
Branch **`190-rating-corpus-regression-suite`** (renamed this session from
`190-decompose-corpus-regression-suite`, which named the wrong corpus; never
pushed, so the rename was local). Cut from `5723a07`. Nothing implemented yet.

Working files changed: `current-task.md` (rewritten three times — the third for
the design change below), `dogfood-logs/190-gate1-run{1..5}.log`. No source
touched.

## Gate status

| Gate | Status |
|------|--------|
| Gate 1 | **Run 5 complete, 29 obligations, decomposition confirmed accurate by Claude.** Awaiting human confirmation of the #178 escalation (below) before it counts as passed. SHA `5723a07`. |
| Gate 2 | not reached — nothing implemented yet |

## THE DESIGN CHANGED THIS SESSION — read this before anything

#190 as filed assumed the corpus cases must be **rebuilt as synthetic fixtures**
in the `tests/fixtures/archetypes/` shape, because "the corpus holds rendered
reports rather than recorded transcripts". That assumption is wrong and the human
has decided against it.

**The inputs survive.** Each run dir holds the exact `current-task.md` it was
given, and `revisions.txt` names the commit it judged. **All six commits still
resolve in this repo's history.** So a case supplies the *real* input, not a
reconstruction.

What the corpus does *not* hold is the model's own responses — `check-output.log`
is the rendered report, downstream of them. So the runs cannot be replayed, and
the judgement each case is scored under is **supplied by a stub in the test**.

**Human's decision: real revisions + stub judges.** Rationale — the corpus's
no-committed-transcripts rule exists because a transcript embeds the full
request. Recording against real revisions would put this repo's own diffs into
`tests/fixtures/`, i.e. exactly what that rule prevents. The three combinations:

| | verdict |
|---|---|
| synthetic fixture + recorded judge | allowed, but low fidelity |
| **real revisions + stub judge** | **chosen** |
| real revisions + recorded judge | violates the corpus's own design rule |

**Accepted cost:** the suite cannot catch a *prompt* regression. It does still
score real code — `evidence/strength.py` is a deterministic reduce over the
stub's discrimination verdicts, so mapping wiring, the strength reduce,
coverage→finding derivation and the verdict are all genuinely exercised. That
covers much of #191, which is largely a code restructuring.

## Verified facts — do not re-derive

**Base revisions**, verified by checking each log's cited hunk headers against
the real diff, with `7de7d71` as a negative control (missed all 4 hunks):

| case | base | head |
|---|---|---|
| `163-gate2-run1` | `4d13ba1` | `41cd0da` |
| `167-gate2-run1..5` | `839ea47` | `07075a6`, `7de7d71`, `95b880a`, `52c52b8`, `dd0a6a5` |

- **Diffs are modest** — 10 files (#167 runs 1–3), 24 files (runs 4–5), 13 (#163).
- **Runs 4 and 5 include the corpus's own 14 files in their diff** — the corpus
  contains itself. Harmless, but expect it.
- **`discovery.py` walks the filesystem, not the git revision.** So a case
  pointed at the live repo would discover *today's* tests. Each case must
  materialize a detached `git worktree` at its head SHA — cheap, shares the
  object store, keeps the real SHAs resolvable.
- **`score_case` already fails in both directions; no new scoring code needed.**
  `evidence_agreement` is recall over `(description, evidence_class)` pairs, so
  an always-STRONG judge matches only genuinely-STRONG obligations and a
  never-STRONG judge only the rest. Both-directions is a property of the **case
  mix**, not of new code. `gap_recall` catches the permissive judge,
  `gap_precision` the pessimistic one.
- **`strength.py`'s reduce**: all defects caught → `strongly_supported`; some →
  `partially_supported`; none → `nominally_supported`; no mapped test →
  `unsupported`; no defect judged → `indeterminate`. **Stubs must supply
  discrimination verdicts (`would_be_caught` booleans), not evidence classes** —
  that is what keeps real code in the loop.
- **`ArchetypeMeta` requires `scenario: int`**, so these cases do not belong
  under `archetypes/`. Decision: sibling `tests/fixtures/rating-regression/`
  holding only `labels.json` + a small `case.json` (base/head) per run. No source
  copied.

## The plan

1. `current-task.md` rewrite + Gate 1 re-run — **done** (run 5).
2. Materializer: corpus run dir → worktree at head → `BenchmarkCase`. The
   analogue of `materialize_archetype`.
3. `labels.json` per run from its `judgement.md`.
4. Stub judges (always-STRONG, never-STRONG) + per-case assertions.
5. `163-gate2-run1` control carries the same assertion kinds.
6. Corpus README updated.

## Gate 1 run 5 — open-question triage

| question | triage |
|---|---|
| `how-to-map-runs-to-cases` | implementation detail — mine. No action. |
| `what-to-do-with-partly-real-gap` | implementation detail. `GroundTruthGap` has no partial notion; encoding is mine. |
| `what-readme-wording-to-use` | implementation detail. No action. |
| `which-corpus-files-to-add` | **ESCALATED — #178, 4th consecutive run.** |

**The escalation:** it asks which files to create under
`tests/fixtures/rating-stability/`, when the task file's scope exclusion limits
that directory to its README — and the decomposer emitted that very constraint as
`preserve-rating-stability-readme-only` in the same run. Answerable from the task
file it just read. Human confirmed the #178 attribution at run 2; this is the
fourth instance, reworded with a new id each time.

## Findings recorded against tracked defects this session

- **#196 filed** (new, child of #181): decomposer typed four automatable
  obligations `human_review`. `ObligationType.HUMAN_REVIEW` is assigned but
  **read nowhere in `src/`** — so it is inert today, and it does **not** trigger
  the CLAUDE.md gate pause (that keys on
  `CoverageStatus.REQUIRES_NON_CODE_EVIDENCE`, a different axis). Filed as a
  latent trap: the moment anything routes on the type, a mistyped obligation
  escapes the evidence bar.
- **#193 commented**: the *same* requirement's type oscillated
  `functional` → `regression` → **dropped** → `functional` → `human_review`
  across Gate 1 runs 1–5, on a byte-identical source block between runs 4 and 5.
  #196 is deliberately kept separate: #193 is "unstable", #196 is "wrong". Fixing
  stability would not stop it stabilising on the wrong value.
- **Process gap noticed:** `current-task.md` is not preserved per dogfood run, so
  the run-4 text is evidenced only by the session transcript. Worth fixing if
  task-file provenance is ever load-bearing.

## Earlier ground truth — still current, do not re-derive

**#190 as filed had both counts wrong**; the issue body has been corrected and
carries the tables. Unearned `strongly supported`: five obligations, seven
run-instances. Real gaps: seven strictly real plus one partly real
(`replace-written-file-with-command` r1, only its *defaulting to JSON* clause).
Rewritten judgements are runs 3 and 5; the corrected reading is ground truth in
both.

The issue's original "three real findings" was the dangerous error: it omitted
all three of run 3's, including the silent `--json` deletion the corpus calls
*"the most serious finding in the corpus"*. Human's call was to require all seven.

## Findings worth not re-deriving

- **Mapping quality must be measured filtered to the current task's obligation
  ids.** #189's Gate 2 read 76% unfiltered and **97% filtered**; DR-164's
  half-blind failure was ~17%.
- **A stable obligation count can conceal a re-split.** Compare aligned sets.
- **Two runs of silence is not evidence of resolution.**

## Outstanding, small (carried, not started)

- **`docs/DR-180` §Open is stale** — lists two settled questions. Own small PR.
- **A DR for the content-vs-shape distinction is arguably owed.**
- **#193's body describes five runs; the corpus is seven.**
- **The instability harness has never been run live.**

## The inference to avoid (DR-180)

> *The diff was purely additive; added tests cannot weaken evidence; therefore a
> rating that fell did so for reasons outside the diff.*

Both premises true, conclusion false. **Instability is not a licence to dismiss a
finding** — check it on its merits first.

## Traps

- **`ModelClient` is a plain class, not pydantic.** Set defaults in `__init__`.
- **Python here is 3.10** — no `enum.StrEnum`. Use `(str, Enum)`.
- **The repo is `alipeles/acceptance-review`**, not the local dir name.
- **`tee FILE | head -N` writes an empty file** — redirect first, then read.
- **`gh api ... -f` sends strings**; sub-issue ids need `-F` for integers.
- **Adding a sub-issue returns the PARENT**, so `-q .number` echoes the umbrella.
  Verify with `gh api repos/.../issues/<umbrella>/sub_issues`.
- **Project `Order` is a custom field**, not the `order` key in `item-list` JSON.

## What to ignore

- **`.acceptance/cache/`** — transcripts and cached reviews, regenerable.

`dogfood-logs/` is no longer in this list: as of `c5cc707` it is committed, and
each run should be saved as a directory carrying its task file, output,
revisions and judgement. The existing 25 flat `.log` files predate that and
have no saved inputs.
