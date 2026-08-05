---
name: orient
description: Re-orient in this repo after a context reset — read CLAUDE.md, session-state.md and current-task.md, check git and the tracking issue, then report where the work stands before touching anything. Use ONLY when the user explicitly invokes /orient. A question about project status, what's left, or what a file does is not a request for this; answer it directly instead.
---

# Orient after a context reset

Re-orient before doing anything. Do not edit, plan, or run the tool until the
final step.

## 1. Read, in this order

1. `CLAUDE.md` — conventions, invariants, and the dogfooding gates. Follow it
   literally; it is the authority on how work happens in this repo.
2. `session-state.md` — the task in flight. Assume it is accurate; it is the
   work log, carried across context resets.
3. `current-task.md` — the mandate most recently under review, in the tool's own input format.

## 2. Check the ground truth

Run `git status` and `git log --oneline -5` so you know the branch and whether
the tree is dirty.

Then read the GitHub issue named in `session-state.md` for the **Deliverable**
and **Acceptance** you are working against. GitHub is authoritative for task
state — the issue is the plan, not any file in the repo (#168).

## 3. Do not

- **Do not read `.acceptance/`.** It is per-run output, regenerated from the
  current review, and can be stale relative to the report.
- **Do not start implementing.** Orienting is the whole job here.

## 4. Then stop and report

Tell the user, briefly:

- Where the work stands — branch, what has landed, what is uncommitted.
- What remains on the issue's Acceptance check, item by item.
- What you propose to do next, and why.

Then wait for a go-ahead before editing anything.
