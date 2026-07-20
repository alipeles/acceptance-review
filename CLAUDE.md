# CLAUDE.md — project context for coding sessions

Read this first. It captures the decisions and conventions for this repo so an
agent can work productively without re-deriving them. The source of truth for
scope and detail is `docs/AI-Assisted-Software-Development-Review-Spec.md` (the
spec) and `docs/Stage-1-Development-Plan.md` (the plan). Section refs (§) point
at those.

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

## Tech

- Tool language: Python (default; it must parse Python ASTs and drive pytest).
- Code under review: Python; tests pytest; VCS Git; requirements as Markdown.
- Any execution (M8) runs sandboxed: no network, no secrets, targeted test
  subsets, short time budget, skipped when a hermetic-feasibility probe fails.

## Repo layout

- `docs/` — spec + Stage-1 plan (source of truth).
- `planning/backlog/` — one Markdown file per task (M0.1, M-B0.1, …), mirrored as
  a GitHub Issue. `issues.tsv` / `milestones.tsv` are the machine index.
- `.github/workflows/` — `ci.yml` (lint + tests) and `benchmark.yml` (accuracy
  report stub for M-B*.report).

## How work is tracked

GitHub **Milestones** (M0 … M9) group tasks; **Issues** are the individual tasks
(Inputs / Deliverable / Acceptance); labels `track:checker` / `track:benchmark`,
`human-gate` (needs human sign-off), `decision` (open design decision). The
Project board has an **Order** number field giving the strict plan sequence.

## Working conventions

- **One issue per branch and PR.** Keep diffs small and reviewable — that's how
  the human builds understanding without reading every line.
- **Before coding a task**, read its issue body and its Acceptance check; state
  the plan before editing.
- **Dogfooding:** when starting a task, copy its Deliverable/Acceptance into a
  `current-task.md` — that file is exactly the kind of input the checker will
  ingest, so we build the product and its future test cases together.
- **Measure as you build:** each capability milestone ends with a scoring hook
  into the benchmark harness (M-B0) — don't defer measurement to the end.
- **Surface open decisions, don't silently resolve them.** The plan §3.2 lists
  decisions owned by specific milestones (LLM orchestration boundary, determinism
  strategy, obligation schema, code-context retrieval budget, test-strength
  rubric, mutation targeting, feasibility probe). Raise these as `decision`
  issues/notes rather than picking quietly.

## Sequencing

Start at **M0 — Foundations & walking skeleton**, issue **M0.1**. The load-bearing
order: build the review-state store + evidence-tier primitives + LLM harness (M0)
and the benchmark harness (M-B0) before capabilities, so nothing ships unmeasured.
Execution tier (M8) comes after the static pipeline (M7) — it only confirms what
static analysis already maps.

## Commands

```bash
pip install -e ".[dev]"   # once M0 lands packaging
pytest -q                 # tests (CI treats "no tests yet" as pass until M0)
gh issue view <n>         # read a task
```

Once real code exists, you can augment this file via Claude Code's `/init`, but
keep the invariants above intact.
