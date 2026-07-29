# acceptance-review

Independent **acceptance review** for software written with AI coding agents.

Coding agents interpret a task, implement it, write tests, and report that they
are done. That creates a circular assurance problem: the system that did the
work also produces much of the evidence that the work was done. This tool is an
**independent check** — given what you asked for and what changed, it asks
whether the implementation and tests actually demonstrate that the requested
behavior was delivered, and what evidence is still missing before you accept
the change.

It is intended to confirm both:

1. that the agent did **what it was told to do**, and
2. that the agent’s claims about what it did are **backed by evidence** — not
   merely asserted in a completion summary.

Stage 1 ships a **Local Completion Checker** plus a **validation benchmark**,
driven from local artifacts only (task file + Git revisions + source/tests). No
GitHub App, hosted service, or CI access is required for that mode. A later
stage adds repository-native acceptance review (GitHub first) on the same
engine.

This is an early personal project: useful today as a local checker and a place
to measure the reviewer’s own accuracy, and designed so others can try it as it
matures.

## Install

Requires Python 3.10+ and Git.

```bash
pip install -e ".[dev]"
pytest -q
```

CLI entrypoint: `acceptance`.

```bash
acceptance check --task path/to/task.md --base <rev> [--head <rev>]
acceptance decompose --task path/to/task.md
acceptance diff --base <rev> [--head <rev>]
acceptance classify --task path/to/task.md --base <rev> [--head <rev>]
```

## Repository layout

| Path | Contents |
|------|----------|
| `src/acceptance/` | Checker, evidence analysis, report, benchmark harness |
| `docs/` | Product spec and Stage-1 development plan (source of truth) |
| `planning/backlog/` | One Markdown file per plan task |
| `tests/` | Unit tests, fixtures, and archetype cases |
| `.github/workflows/` | CI (lint + tests) and benchmark report stub |

## How the work is tracked

- **Milestones** (M0, M-B0, M1 … M9) group the work.
- **Issues** are individual tasks (Inputs / Deliverable / Acceptance).
- **Labels**: `track:checker` vs `track:benchmark`, `human-gate`, `decision`.

See `docs/Stage-1-Development-Plan.md` for sequencing and exit criteria, and
`docs/AI-Assisted-Software-Development-Review-Spec.md` for the full product
definition.

## Disclaimer

This software is early and experimental. An acceptance review is **not** a proof
of correctness, a substitute for human judgment, CI, security review, or your
own testing.

Findings are judgments — often assisted by language models — that can be wrong,
incomplete, or overly confident. Treat positive results as *no material gaps
found at the achievable evidence tier*, not as certification that the change is
safe to ship. Use at your own risk.

## License

MIT — see [LICENSE](LICENSE).
