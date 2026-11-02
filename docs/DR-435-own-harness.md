# DR-435 — The pipeline stays on our own harness; no agent framework

Decided 2026-10-28, while planning the decomposition redesign (#435, the
umbrella for rebuilding decomposition around claims, synthesis, pruning,
expectations and clarifications).

## Decision

The review pipeline keeps its own harness: `pipeline.py::run_review` as the
spine, schema-constrained calls through `llm.py`, review-state as the
persisted store, recorded transcripts for replay. No agent framework
(LangGraph, the Agents SDK, or similar) is adopted for the redesign or after
it.

The provider layer is a separate question and is decided at #432, where a
provider interface of our own wraps a native Anthropic adapter and keeps
LiteLLM for breadth. That lands before #436 (claims and schema), so the
redesign's transcripts are recorded once.

After the redesign milestone, the integration surface becomes a local MCP
server running over stdio, wrapping the same functions the CLI calls. The
CLI stays as a thin wrapper. #442 (clarifications) builds its two commands
as functions in one module for that reason.

## Why

The redesign looks agentic and is not, in the sense frameworks mean. It is a
fixed sequence of nine steps, each a schema-constrained call writing into
review-state, with one bounded loop (the omission check, capped at two
passes) and one interaction that happens across sessions through a file (the
clarification record). The questioning loop is run by the coding agent, not
by us: it calls the tool to list open questions and append answers, and its
own framework does the looping. Our side is stateless per invocation over a
persisted store, which is the local, no-setup shape the product is meant to
have.

What a framework would own for us is control flow, tool-use loops and
checkpointing. Checkpointing already exists (review-state and `--continue`).
The invariants that matter most, byte-identical replay, canonical
serialization and recorded transcripts, are exactly the things a framework
would take over in its own shape, and keeping them would mean working around
it.

## Rejected

- **Adopt an agent framework for the multi-step pipeline.** Buys control
  flow we do not need and takes ownership of state and replay we do.
- **Move the questioning loop inside the tool.** Would make the tool a
  long-running agent that drives the coding agent, inverting the integration
  and dropping the local, per-invocation shape.

## Consequences

- MCP tool descriptions become the place where the coding agent learns how
  the tool is used; a `setup` prompt or resource carries the longer
  explanation. That replaces hand-written `CLAUDE.md` integration blocks for
  users.
- "The tool never answers a question itself" remains a rule for the MCP
  server as much as for the CLI.
- Whether the coding agent reliably calls back with answers over MCP depends
  on those descriptions, and deserves a small evaluation of its own when the
  server is built.
