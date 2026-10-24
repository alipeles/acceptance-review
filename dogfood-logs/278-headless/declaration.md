# Declaration — #278, a fresh install picks up a litellm that cannot make a live call

## What I implemented

- `pyproject.toml`: the litellm requirement went from `litellm>=1.50` to
  `litellm>=1.93,<1.97`, with a comment saying why each side sits where it
  does and what to re-check before raising the ceiling. The dependency list was
  reflowed to one entry per line so the comment sits next to the bound. pydantic,
  markdown-it-py and pathspec are unchanged.
- `tests/test_litellm_smoke.py`, new, two tests:
  - `test_litellm_builds_a_model_response_on_the_default_completion_path` calls
    `llm._default_completion_fn` (the real door to `litellm.completion`) with
    litellm's `mock_response`, so litellm builds its `ModelResponse` as it would
    for a provider reply but answers locally.
  - `test_a_recording_run_completes_through_the_installed_litellm` runs a
    `ModelClient` in `RECORD` mode whose completion function is
    `_default_completion_fn` plus `mock_response`, so the request the client
    builds, litellm's response object and the transcript extraction all run.
  - Both block `socket.socket.connect` and `socket.create_connection`, so a
    test that tried to reach a provider would fail rather than call out.

## What I tested

- I verified the regression test fails for the reason in the issue: on Python
  3.10.20 with litellm 1.97.0 and pydantic 2.13.4 both tests fail with
  `APIConnectionError: ... Message is not fully defined`, raised from
  `litellm/main.py` line 5160, the same line the issue quotes.
- I verified that after the change, a fresh Python 3.10 environment installed
  from `pyproject.toml` alone resolves litellm 1.96.2 and both tests pass.
- I swept litellm versions on Python 3.10 with the smoke test (wheel installs
  only): 1.92.2, 1.93.0, 1.96.2 pass; 1.97.0 fails (`Message` not fully
  defined); 1.98.1, 1.99.4, 1.100.5 fail to import (`typing.NotRequired`, which
  Python 3.10 lacks); 1.101.0 through 1.106.0 pass. On Python 3.12, 1.96.2,
  1.97.0 and 1.106.0 all pass.
- Full suite, `ruff check` and `ruff format --check` pass (see `notes.md`).

## What I left out

- CI still runs only Python 3.12. The 1.97.0 break does not appear there, so the
  smoke test in CI would not have caught this specific break. I did not change
  `.github/workflows/ci.yml`; it is outside the files this run may change. Queued
  under `Deferred` in `notes.md`.
- I did not widen the ceiling to admit 1.101 to 1.106, though they pass the
  smoke test on 3.10. Only 1.93.0 and 1.96.2 have been through a real recording
  run on the project's floor Python.

## What I assumed

- That the Python 3.10 floor in `requires-python` is the environment that
  matters most, since the human's worktrees are macOS Python 3.10.
- That litellm's `mock_response` builds the response through the same
  construction as a real reply. I believe this because the 1.97.0 failure
  reproduced through it at the same line as the live failure.

## What is unverified

- I did not make a live recording run on Python 3.10 myself. The decompose run in
  this directory was live, but on Python 3.13 with litellm 1.106.0, before the
  bound changed.
- I did not test litellm releases between 1.50 and 1.92, or patch releases of
  1.98 to 1.100 other than the ones listed.
- Nothing on macOS; everything here ran on Linux.
