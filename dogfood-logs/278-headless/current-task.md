# Task: constrain litellm to versions that can make a live call

## Task

A fresh `pip install -e .` must resolve a litellm release with which a recording
run works. The litellm requirement in `pyproject.toml` is bounded on both sides,
to a range of releases that install and that can build a model response, and the
bound carries a comment saying why each side is where it is, so that the next
person widening it knows what to re-check.

The test suite includes a smoke test, which is itself a deliverable, that drives
litellm's own completion path against the installed version far enough to build
its response model, without contacting a provider. It runs in the ordinary
replay-mode suite, so CI fails when an installed litellm cannot construct a
response.

## Scope exclusions

- No change to how model requests are assembled or recorded.
- No change to the pinned versions of pydantic or openai.
