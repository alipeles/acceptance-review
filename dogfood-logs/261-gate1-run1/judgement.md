# Judgement — #261/#239 Gate 1, run 1

**Superseded by run 2.** Kept because the input differs in a way worth having on
record, not because the output was wrong.

## Outcome

26 requirements → 25 obligations, one deliberate none (`completion-01`,
"Implementation"). No open questions. No unreconciled cluster. Every obligation
is a faithful restatement of its requirement.

**No tool defect was found in this run.** It was discarded for an error in the
*input*.

## Why it was discarded

The task file's Completion expectations demanded six tests, five of which asserted
properties of the repository's tooling rather than of the code:

- a test asserting every Python file is formatter-clean;
- a test asserting no Python file violates a lint rule;
- a test asserting the build's lint step does not discard its exit code;
- a test asserting the build runs a formatting check;
- a test asserting the build checks out full history;
- a test asserting the dev dependencies pin an exact `ruff` version.

Human correction, mid-run: *tests should be focused on the behavior of the code;
they should not be aware of the linter or run it.* An external tool already checks
these, and the automated build is the gate for them. A pytest that shells out to
`ruff` is a second, weaker copy of a check that already exists, and it couples the
suite to the tooling.

Run 2 drops all six. Its Completion expectations are `Implementation` alone.

## Difference worth recording

`task-01` decomposed differently across the two runs over near-identical headline
text:

| run | `task-01` yields |
|---|---|
| 1 | **two** obligations — sources are clean / the build fails otherwise |
| 2 | **one** composite carrying both clauses |

Run 1's split is the better decomposition: the headline states two separable
claims and they are separately checkable. Not filed as an instability instance —
the task file did change between the runs, so the two are not a controlled pair.

## Type inconsistency across the exclusions

Present here as in run 2, and already queued against #205: five structurally
identical scope exclusions were typed `regression` ×4 and `functional` ×1.
Run 2 spread the same five across **three** types. See run 2's judgement.
