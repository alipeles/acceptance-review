# DR-338: A coding agent as the last edit builder

**Issue:** #338, add a headless coding agent as a third way of building a
defect-injecting edit, behind the same checks as the others.
**Decided:** 2026-10-05, at #338's Gate 1, by the human.
**Code:** `src/acceptance/mutation/agent.py`; routing in `runner._attempt`.

## Context

The mutation stage plants a named defect in a copy of the code and runs the
tests against it. The edit is written by a builder. The one-call builder
(`descriptor.py`) is shown only the lines the defect names, and #45 traced many
of its bad edits to that: it cannot see what the edited code calls. #334 added
several candidates per defect; a defect whose every candidate is set aside ends
with no usable edit. #338 asks whether an agent that opens files as it needs
them does better on exactly those defects.

## Decision 1 — The agent is the last candidate, through the same loop

`run_mutations` takes an optional `fallback` builder. `_attempt` asks the
one-call builder up to `max_candidates` times and then the fallback once, in one
loop with one body, so the agent's answer meets the text checks, the test run,
the broken-edit check and the breadth refusal exactly as any other candidate
does. It is counted as one more candidate asked, so `MutationAttempt`'s
candidate validator holds unchanged. Configured by `ExecutionSettings.agent`;
`None`, the default, builds no agent and sends exactly the requests a review
sent before.

The agent's change is reduced to one span replacement in one file
(`descriptor_from_changes`). Anything else — two spans, two files, a new or
deleted file, a file the defect did not name, a run that did not finish or
changed nothing — is no usable answer. It is never repaired into one.

The agent cannot decline or claim the code is already defective: those are
typed answers only a schema can carry, and reading them out of the agent's
prose would treat its account as evidence. Making no change is its decline.

## Decision 2 — The guard test is not edited

#338's Acceptance asks that `tests/test_unverified_mutation_is_inert.py`, which
checks that an edit nobody confirmed adds nothing to the review, pass unchanged
with this builder selected. That file has no way to select a builder.

The confirmation step and the "counts for nothing" rule run after an edit is
written and do not depend on who wrote it. So rather than edit the guard,
`tests/test_unverified_mutation_is_inert_with_agent.py` inherits its
whole-review cases and runs them with a fake agent configured and every one-call
candidate refused, so each case's edit is the agent's. A control case there
fails if the agent is never reached.

**Rejected:** parametrizing the guard file over builders. Simpler, but
"unchanged" was the point.

## Decision 3 — Confinement uses the agent's own mechanism, verified live

The copy the agent works in has every file `is_test_path` matches deleted — the
one definition the one-call builder's withholding uses too — plus `.claude/`
and `.codex/`, whose hooks and permission rules would otherwise run inside our
agent. That keeps tests out of its folder, but the original project, tests
included, is still on disk. Claude Code is therefore confined by its own flags,
passed per run and never written to the user's settings:

- `--tools Read,Edit,Glob,Grep` — no shell, so nothing can `cat` a path the
  file tools may not open, and no tool that creates files;
- `--settings` with deny rules on the original for `Read` and `Edit`, and allow
  rules for both under the working folder only;
- `--permission-mode dontAsk` — anything not allowed is refused rather than
  waiting for an approval nobody will give.

Claude Code's sandbox setting is not used: it governs shell commands, and there
is no shell here. **Rejected:** an OS-level sandbox around the agent. Stronger,
but per platform, and every future adapter would need its own.

**Verified live, 2026-10-05, Claude Code 2.1.289.** A probe ran the real
`ClaudeCodeAgent` through the real `agent_copy` over a throwaway project and
asked it, by absolute path, to read a test file and a non-test file in the
original, search the original, and edit the original. Claude Code's own result
object listed five `permission_denials`: `Read` of both files, `Glob` over the
original, a `Read` and an `Edit` of the original's `loan.py`. The original was
byte-identical afterwards, no marker from either file reached the copy, and the
one allowed edit, inside the copy, landed. Two runs, $0.11 in total.

One observation from it: the agent named the original as `/tmp/...` while the
deny rule names its resolved form `/private/tmp/...`. The denial held anyway, so
at least `dontAsk`'s refusal of paths outside the working folder is doing the
work; whether the deny rule alone matches a symlinked spelling was not isolated.

## Decision 4 — The diff is recorded, through the model client's store

`ModelClient.replay_or_run` records any non-completion work keyed by its
request, in the same store and mode as model calls: the agent run is the first
user. The request holds the agent, its model, the prompt and the time limit;
the record holds the run's outcome and, per changed file, its unified diff and
its hunks as span replacements. No transcript, no session id, no timing — so a
replay applies the recorded diff without starting the agent, and two recordings
of the same input are byte-identical. A missing executable raises rather than
being recorded, so it cannot replay as "no usable edit" forever.

The prompt reuses the one-call builder's typed defect fields and numbered
regions (`descriptor._subject`), and its list of refused candidates, under
instructions for editing files instead of answering a schema.

## Decision 5 — Cost per defect, by a label on the usage record only

`ModelClient.complete` and `replay_or_run` take an optional `label`, copied into
the call's usage record and never into the request, so no request key moves and
nothing recorded before this change re-records. The one-call builder passes the
defect id; so does the agent builder. `usage.per_label` sums cost and live time
per defect and stage, and the CLI and `run_audit.py` print both builders side by
side whenever a defect reached the agent. Cost stays out of review state, as it
already did. No historical data is transformed and none needs to be.

## Supporting another agent

`CodingAgent` is the whole interface: run a prompt in a folder under a time
limit, report whether it finished and what it cost, and be unable to reach the
folder it is told is forbidden by its own enforcement. Adding Codex is one class
and one entry in `AGENTS`. Its confinement must be verified live the way
Decision 3's was before it is trusted, because each agent enforces it
differently.
