# #278 — A fresh install picks up a litellm that cannot make a live call

Child of #184. Found in #275's Gate 1, run 1.

## The problem

`pyproject.toml:12` floors the dependency at `litellm>=1.50` with no ceiling. A fresh `.venv` created for the #275 worktree resolved **litellm 1.97.0** against **pydantic 2.13.4**, and every live call died inside litellm's own response construction, before reaching a provider:

```
File ".../litellm/main.py", line 5160, in completion
    model_response: Final = ModelResponse()
File ".../litellm/types/utils.py", line 1290, in __init__
    super().__init__(
pydantic.errors.PydanticUserError: `Message` is not fully defined; you should define
all referenced types, then call `Message.model_rebuild()`.

litellm.exceptions.APIConnectionError: litellm.APIConnectionError: `Message` is not
fully defined; ...
```

It surfaces as an `APIConnectionError`, which reads as a network or key problem and is neither.

The other worktrees hold **1.96.2** and work. `pip install litellm==1.96.2` fixed it with no other change, and Gate 1 then completed.

## Why nothing caught it

`RunConfig.mode` defaults to `REPLAY`, so the CLI, the suite and CI never issue a live call — the whole point of the replay-first stance. This break lives entirely on the record path, which is exactly the first thing a **new worktree** must do: no transcripts exist yet for a task file that was just written, so `decompose` records. So the failure mode is "every new environment, on its first real command, with an error that points at the network."

## Acceptance

- `pyproject.toml` constrains litellm to a range in which a recording run works.
- Something exercises the live-call construction path against the installed version — a smoke check that builds the request and the response model without calling a provider is enough; the point is to fail in CI rather than in a new worktree.
- The chosen bound records *why* it exists, so the next upgrade does not silently reopen it.

## Evidence

`dogfood-logs/275-gate1-run1/judgement.md`, final section. Observed at `5c5d9de`, macOS, Python 3.10, pydantic 2.13.4 / pydantic_core 2.46.4, openai 2.54.0.

## Comments (summarised)

1. (2026-08-20) Root cause is a litellm packaging bug: `Message` is annotated with
   `ChatCompletionReasoningSummaryTextBlock` imported under `TYPE_CHECKING`, so pydantic
   cannot resolve it at runtime. Only the litellm version matters. Also reported that
   `litellm==1.93.0` would not install (sdist needing Rust).
2. (2026-08-20) Correction: the 1.93.0 install failure was a sandbox denial, not a pip
   failure; with the sandbox off 1.93.0 installs and records. 1.93.0 and 1.96.2 are both
   confirmed good. The range should be bounded on both sides, and the check must run in
   the environment it will be used in.
