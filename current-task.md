# Task

A task file can carry an optional `## Context` section, for background that
helps a reader understand the mandate but is not itself something the change
must deliver: the problem being fixed, how the system behaves today, or
measurements already taken.

Parsing a task file records the Context section as its own field, each block
with its span back to the source. Context is not reported as unread source, and
it is not a requirement: it gets no requirement id and no disposition, and
adding or removing it does not move the mandate coverage counts.

Decomposition shows the context to the model, labelled as context and kept
apart from the list of requirements, so the model can use the background
without being asked to account for it. A task file with no Context section
produces exactly the same model requests and the same results as it does today.

The spec's description of the task file format (§7.1) describes the Context
section, and the repository's contributor guide, `CLAUDE.md`, says when an
author should use it.

## Scope exclusions
- Recognising background that is not under a Context heading.
- Context sections nested inside other sections; there is one top-level Context
  section.
- Adding a Context section to the existing task files under `tests/fixtures/`
  and `dogfood-logs/`.
