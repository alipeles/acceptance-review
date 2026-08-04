# CLAUDE.md — project context for coding sessions

Read this first. It captures the decisions and conventions for this repo so an
agent can work productively without re-deriving them. The source of truth for
scope and detail is `docs/AI-Assisted-Software-Development-Review-Spec.md` (the
spec); section refs (§) point at it. **GitHub is authoritative for anything with
a lifecycle** — tasks, open decisions, milestone sequencing. Files are
authoritative only for things with no lifecycle: the spec, resolved decisions
(`docs/DR-*.md`), and the standing invariants below. If a file and an issue
disagree about what the work is, the issue wins (#168).

## What this is

An independent **acceptance review** for software written by AI coding agents.
Given a change mandate and a proposed implementation, it decides whether the
tests actually demonstrate that the requested behavior was delivered, and
prescribes the evidence still needed. Personal project; goals: sharpen AI-domain
credibility, grow agentic skills, and build something individually useful without
enterprise setup.

## Stage 1 scope (what we're building now)

A **Local Completion Checker** plus the **validation benchmark** that measures
whether the checker works. GitHub Acceptance Review is Stage 2 — out of scope.

## Invariants — do not violate these

- **The checker stays local/GitHub-independent.** Its only inputs are a task
  file, Git revisions, source, tests, and an optional builder declaration. No
  GitHub App, hosted service, or CI access in the Stage-1 checker (§3.1, DoD #1).
  (Managing *our own* backlog on GitHub is separate from the product's inputs.)
- **Evidence-tier discipline is a data-model invariant, not a display choice.**
  Tiers: builder-claim < static < coverage-confirmed < defect-killed < CI-confirmed.
  A component may only raise a finding to a tier it's authorized to produce; a
  static analyzer can never emit `defect-killed` (§8.1, M0.3).
- **Every finding is typed and linked.** It carries a tier and links to exact
  requirement text / code lines / test locations. No free-text conclusions (§13.6).
- **Uncertainty is first-class.** `Indeterminate` and open-question outputs are
  valid, expected results — don't force a confident verdict (§9.3, §7.3).
- **Structured, persisted review-state**, not an unstructured model transcript
  (§12, §15). Build this store first (M0) so later components write into it.
- **Replay-first + determinism.** Model calls are schema-constrained and recorded
  for replay; capability tests run off recorded transcripts, no live calls
  (M0.4, M0.5). Two recorded runs over the same input must be byte-identical.
- **Positive results are bounded.** "No material gaps at the achievable tier,"
  never "proven correct" (§3.7).
- **`current-task.md` is an input to the checker — never a work log, and never
  edited to change what the review says.** Suppressing a finding or open question
  destroys the only signal that the tool is wrong; adding progress notes or
  decisions changes the decomposition. The one sanctioned edit is rewriting a
  *weak obligation* — requirement text that is genuinely badly worded — which is
  encouraged. **Fix the wording, never the output.** Session state belongs in
  `session-state.md`.

## Tech

- Tool language: Python — it must parse Python ASTs and drive pytest.
- Code under review: Python; tests pytest; VCS Git; requirements as Markdown.
- Any execution (M8) runs sandboxed: no network, no secrets, targeted test
  subsets, short time budget, skipped when a hermetic-feasibility probe fails.

## How the tool runs — read before your first command

- **Replay is the default mode.** `RunConfig.mode` defaults to `Mode.REPLAY`, so
  the CLI, the test suite and CI never issue a live model call and need no API
  key. Opt into `RECORD` explicitly to call a provider.
- **Transcripts and cached reviews live in `.acceptance/cache/`** (gitignored).
  Record-if-missing, then replay.
- **Changing a prompt, the model, or the seed invalidates recorded transcripts**
  — the request key hashes all three, deliberately: a determinism control changed,
  so recordings must be re-verified. It also makes benchmark accuracy figures
  non-comparable across the change, so sequence prompt work to pay that cost once.
- Interpreter is `.venv/`. Provider keys, needed only when recording, come from
  `.env` (gitignored).

## Repo layout

- `docs/` — the spec (source of truth for the product), plus Decision Records
  (`DR-<issue>-<slug>.md`). No task list lives here; tasks are GitHub Issues.
- `.github/workflows/` — `ci.yml` (lint + tests) and `benchmark.yml` (accuracy
  report stub for M-B*.report).
- `tests/` — unit tests, plus `tests/fixtures/archetypes/` — the labelled cases
  the benchmark scores against.
- `current-task.md` — the task being worked right now, in the tool's own input
  format.
- `session-state.md` — rolling state of the task in flight, carried across
  context resets. Gitignored and disposable.
- `dogfood-logs/`, `.acceptance/` — local run artifacts. Gitignored, never
  committed.

### `src/acceptance/` — the review pipeline

`pipeline.py::run_review` is the spine, and both consumers call it: the CLI
(`acceptance check`) and the benchmark (`benchmark/coverage.py::classify_case`).
A test pins that they share it — they had drifted before, leaving the CLI on an
M3-era chain. Stage order follows §10.1:

- `requirement/` — parse the task file, decompose into obligations, ingest the
  builder declaration (§7).
- `change/` — resolve revisions and build the diff under review.
- `evidence/` — discover candidate tests, **map** them to obligations, then
  extract evidence, judge discrimination, and classify strength.
- `coverage/` — classify implementation coverage per obligation, detect
  unrequested changes and their dispositions, resolve open questions, recommend
  tests, compare the declaration.
- `verdict.py` / `report.py` — derive the completion verdict from findings and
  render the §16 report.

Supporting: `review_state.py` + `review_store.py` (the persisted structured
review), `llm.py` + `config.py` (schema-constrained calls, determinism controls,
transcript record/replay), `serialization.py` (canonical form — byte-identical
reruns depend on it), `evidence_tier.py`, `source_ref.py`.

`benchmark/` is the measurement harness; it is not part of a review run.

## How work is tracked

GitHub **Milestones** (M0 … M9) group tasks; **Issues** are the individual tasks
(Inputs / Deliverable / Acceptance); labels `track:checker` / `track:benchmark`,
`human-gate` (needs human sign-off), `decision` (open design decision). The
Project board has an **Order** number field giving the strict sequence.

**The backlog is the plan.** There is no separate planning document — milestone
descriptions carry sequencing and dependencies, issue bodies carry task detail.
Write task detail into the issue, never into a file. A task revised *after* it
was delivered gets a **superseding issue** (`M7.3.r1` supersedes `M7.3`), not an
edit in place: the original acceptance check genuinely passed, and that record is
worth keeping. See #34 → #167.

**Tool defects found by dogfooding hang off a subsystem umbrella**, one per area
of `src/acceptance/`, labelled `umbrella` and holding its children as GitHub
sub-issues. Dogfooding generates defects faster than they can be fixed, and they
cluster: several children of one umbrella touch the same file, share one prompt,
and force the same transcript re-record, so they are sequenced together rather
than independently.

| umbrella | area |
|---|---|
| #181 | decomposition — `requirement/` |
| #182 | test discovery & mapping — `evidence/discovery.py`, `mapping.py` |
| #183 | evidence judgement — `evidence/discrimination.py`, `strength.py` |
| #184 | determinism & reproducibility — `llm.py`, `serialization.py`, `partition.py` |
| #185 | findings model, verdict & presentation — `coverage/`, `verdict.py`, `report.py` |
| #186 | benchmark — `benchmark/` |

File a new defect **as a child of its umbrella**, not standalone. Mapping and
evidence judgement are deliberately separate umbrellas: #167's Gate 2 showed they
fail independently — a byte-identical mapped set with a flipped judgement over it.

Which milestone proves which §13.5 demonstration scenario:

| # | Scenario | Proven by |
|---|---|---|
| 1 | Missed obligation | M1 + M3 |
| 2 | Qualifier missed | M3 |
| 3 | Superficial test (asserts existence) | M5 |
| 4 | Non-discriminating input | M5 (+ M8 to confirm) |
| 5 | Circular expected result | M5 |
| 6 | Critical behavior mocked out | M5 |
| 7 | Declaration mismatch | M6 |
| 8 | Unrequested change | M3 + M3.5 + M7 (M7.6 advisory presentation) |
| 9 | Local revision cycle (rerun) | M7 (incremental re-run over M0 state) |
| 14 | Execution-confirmed weak test | M8 |

Scenarios 10–13 depend on GitHub/CI and are Stage 2.

## Working conventions

- **One issue per branch and PR.** Keep diffs small and reviewable — that's how
  the human builds understanding without reading every line.
- **Before coding**, read the issue body and its Acceptance check, and state the
  plan before editing.
- **Dogfooding is a hard gate on shipping.** See *Dogfooding — the review gates*
  below, and follow it literally.
- **Test the wiring, not just the function.** Defect injection has repeatedly
  found the same shape of hole: a helper with a good unit test that the pipeline
  never actually calls. When you add a helper, test that the pipeline invokes it.
- **Measure as you build:** each capability milestone ends with a scoring hook
  into the benchmark harness (M-B0) — don't defer measurement to the end.
- **Surface open decisions, don't silently resolve them.** Open design decisions
  are tracked as `decision`-labeled issues, each owned by a milestone — that
  label *is* the list. Raise a new one rather than picking quietly.
- **Write a Decision Record when one is resolved**, or when a non-obvious finding
  changes the design: `docs/DR-<issue>-<slug>.md`, referenced from the issue. A
  decision that lives only in a commit message or a chat session is lost. See
  `DR-081` and `DR-164`.

## Dogfooding — the review gates

We run the tool against our own work in progress. It is the only place the tool's
own failures become visible, so it is a hard constraint on shipping. Two gates,
both mandatory, neither skippable because the change looks small.

Always save the output of dogfood runs in the dogfood-logs folder.

### Gate 1 — before writing any code

**1.** Write `current-task.md` for the issue (its Deliverable and Acceptance),
then decompose it:

```bash
.venv/bin/acceptance decompose --task current-task.md
```

**2. Read the obligation breakdown and confirm it is accurate** — no invented
obligations, none of the real ones missing. An inaccurate decomposition
invalidates every downstream stage, so do not proceed past a breakdown you would
not defend.

**3. Triage every open question it raises.** Each falls into exactly one of three
cases:

| Case | Action |
|------|--------|
| **Fair question** — `current-task.md` was genuinely inadequate or ambiguous | **Fix `current-task.md`.** This is the sanctioned rewrite of weak wording (see invariants). |
| **Implementation detail** deliberately left to the coding agent | **No action.** It is a correct observation about a decision that is yours to make; silencing it would be dishonest. |
| **Wrong question** — answerable from the task file plus the repo | **Stop and tell the human. Do not proceed.** State why it is answerable, and whether you believe the cause is already accounted for in the backlog (e.g. a known decomposition or mapping defect). Never fix it silently, never work around it. |

**Tie-break on rewriting:** rewrite when the tool's response makes you regret
your wording; otherwise leave it. This is independent of whether to escalate — a
question can be both worth rewording and worth reporting. Report it either way;
the rewrite is not the report.

**4. Record in `session-state.md`** that Gate 1 passed, at which SHA, and who
confirmed the decomposition. That confirmation is a human judgement — unwritten,
the next session either repeats it or assumes it.

### Gate 2 — after coding, before opening a PR

```bash
.venv/bin/acceptance check --task current-task.md --base <rev> [--head <rev>]
```

**Move forward only on a completely clean check.** Clean means all of:

- every obligation **addressed**;
- every obligation **strongly supported by test evidence** — supported is not
  enough;
- every open question **resolved**;
- **no** recommended tests;
- no other flag, caveat, or indication that something needs attention.

Anything short of that is a stop. It is not a judgement call and not a threshold
to negotiate down. Record the result in `session-state.md` — clean or not, and at
which SHA.

### Rules that apply at both gates

- **Read the test recommendations before forming an opinion.** When an obligation
  is less than strongly supported, the recommendations state exactly what evidence
  is missing. Read them *first* — do not pronounce on whether the finding is
  meaningful, correct, or worth acting on until you have.
- **Anything marked as requiring non-code evidence or human review is a pause.**
  Surface it and wait; that flag exists because the tool cannot settle the
  question alone.
- **Any correction made in response to a dogfood finding re-arms the gate.**
  Re-run the stage that raised it — `decompose` for Gate 1, `check` for Gate 2 —
  and get a clean result before moving on. A fix is finished when the re-run comes
  back clean, not when it was written.
- **Every negative finding has exactly two permitted dispositions:** (1) **address
  it** with a code or documentation change, or (2) **attribute it to a defect in
  the tool**, in which case **a backlog item must exist before you move forward**
  and the finding is recorded against it. There is no third option. Attribution
  converts a finding into tracked work; an untracked attribution is
  indistinguishable from suppressing it, and is treated as such.
- **A clean verdict is only as trustworthy as the mapping step behind it.** A
  review whose M4 mapping call returned mostly empty `obligation_ids` is
  half-blind, not clean. Check the mapping transcript before believing a clean
  Gate 2 — see `docs/DR-164-mapping-stage-request-partitioning.md`.

## Working in small sessions

Sessions are kept short and context reset often, deliberately: a long session
accumulates dead ends and superseded versions that compete for attention, and
compaction keeps the shape of that history while dropping the specifics. The cost
of resetting is paid in whatever was never written down, so: **externalise state
continuously, reset at the cheap moments.**

**Start of session — do this and nothing more:**

1. `session-state.md` — rolling state of the task in flight.
2. `current-task.md` — the task itself.
3. `git log --oneline -10` and `git status`.

Do **not** read `.acceptance/next-instruction.md` at startup. It is a single
fixed path overwritten by whichever `check` run last found gaps, keyed to no task
and no SHA, and never cleaned up — so it routinely describes a different task on
a different branch. #167 (M7.3.r1) replaces it with on-demand retrieval.

Then start work. Do **not** "get oriented" by reading the source tree; the
`src/acceptance/` map above exists so you don't have to.

**Reset at the gates.** Gate 1 passing and Gate 2 coming back clean are the
natural reset points: all the state is external and re-derivable, so resetting
costs almost nothing. Mid-implementation is where real work is lost. It follows
that a task should fit one session, gate to gate — if it can't reach Gate 2
without a reset, split the issue rather than run a longer session.

**Keep `session-state.md` current.** Rolling, fixed headings, rewritten wholesale
rather than appended to. Update it before you stop and any time losing the last
hour would hurt — not as an end-of-session ceremony, which is expensive enough to
get skipped. Keep it short; cheap to rewrite means it actually gets rewritten.

**Push exploration into subagents.** Searching the repo — "where is X handled",
"which tests cover Y" — produces far more output than answer. Delegate it and
keep the conclusion, not the transcript. This is the biggest lever on in-session
context.

## Sequencing

**Where the work currently stands is deliberately not recorded here** — a status
line goes stale within days and then misdirects. Live state is `session-state.md`
and `current-task.md`.

What is durable is the load-bearing order: the review-state store, evidence-tier
primitives and LLM harness (M0) and the benchmark harness (M-B0) come before
capabilities, so nothing ships unmeasured. The execution tier (M8) comes after the
static pipeline (M7) — it only confirms what static analysis already maps.

## Commands

```bash
.venv/bin/pip install -e ".[dev]"   # first-time setup
.venv/bin/pytest -q                 # full suite — replay mode, no API key needed
.venv/bin/ruff check .              # lint, as CI runs it
.venv/bin/acceptance check --task current-task.md --base <rev> [--head <rev>]
gh issue view <n>                   # read a task
```

Other subcommands: `decompose`, `diff`, `classify`.

---

Keep this file short. Add a line when an agent would otherwise rediscover
something expensive or get something wrong; delete a line when it stops being
true. Status belongs in `session-state.md` and git history, not here.
