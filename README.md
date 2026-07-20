# AI Acceptance Review

Independent **acceptance review** for software written with AI coding agents.
Given a change mandate and a proposed implementation, it determines whether the
tests actually demonstrate that the requested behavior was delivered, and
prescribes the evidence still needed.

Stage 1 (this milestone) ships a **Local Completion Checker** plus the
**validation benchmark** that measures whether the checker actually works — run
entirely from local artifacts (a task file + Git revisions + source/tests), with
no GitHub App, hosted service, or CI access required. Stage 2 adds the GitHub
Acceptance Review on top of the same engine.

## Repository layout

- `docs/` — the product spec and the Stage-1 development plan (source of truth).
- `planning/backlog/` — one Markdown file per plan task (M0.1, M-B0.1, …). Each
  is mirrored as a GitHub Issue and doubles as a future `current-task.md` input.
- `.github/workflows/` — CI (lint + tests) and the benchmark accuracy-report stub.

## How the work is tracked

- **Milestones** (M0, M-B0, M1 … M9) group the work and show progress.
- **Issues** are the individual tasks, each with Inputs / Deliverable / Acceptance.
- **Labels**: `track:checker` vs `track:benchmark`, `human-gate` for tasks needing
  human sign-off, `decision` for open design decisions.
- **Project board** gives the Kanban view across it all.

Start with milestone **M0 — Foundations & walking skeleton**.

## Development

```bash
# once tooling lands in M0:
pip install -e ".[dev]"
pytest -q
```

CI runs on every push/PR to `main`. See `docs/Stage-1-Development-Plan.md` for the
full sequencing and exit criteria.
