# Notes — #278 headless run

## Decompose

Run `594187e0065a80e0`, exited 0, 4 requirements, 12 obligations, 1 open question.
Note: this decompose made live calls on litellm 1.106.0, Python 3.13, before the
bound changed, and they worked.

Invented or doubtful obligations:

- `smoke-test-included` ("the test suite includes a smoke test") and
  `litellm-completion-path-builds-response-model` say nearly the same thing as
  `litellm-can-build-model-response` from task-01. Not invented, but three
  obligations for one property. Possible duplicate-merge miss.
- `litellm-installable-release-range` ("constrain ... to a range of releases that
  install") and `litellm-requirement-bounded-both-sides` overlap; acceptable split.
- `keep-pydantic-openai-pins-unchanged` says "pinned versions", which is my wording
  in the task file and is slightly wrong: pydantic is `>=2` and openai is not
  declared at all. The task file wording is weak, not the tool.

Missing: none that I can see.

Open question `task-02-span-01-disagreement` — about the clause "which is itself a
deliverable". I believe this is a **fair question**: the clause is an aside in my
wording, not a property, and the task file could say the smoke test is required
without that phrase. It is also an instance of the tool's internal coverage step and
per-span call disagreeing (the question text says so).

## Reproduction

The bug does not reproduce on Python 3.12 or 3.13 — litellm 1.97.0 works on both.
It reproduces only on Python 3.10, the project's `requires-python` floor and the
version the human's macOS worktrees use. I built a Python 3.10 environment with `uv`.

Failing output — Python 3.10.20, litellm 1.97.0, pydantic 2.13.4, openai 2.54.0,
`python -m pytest -q tests/test_litellm_smoke.py`, before the `pyproject.toml` change:

```
E       pydantic.errors.PydanticUserError: `Message` is not fully defined; you should define all referenced types, then call `Message.model_rebuild()`.
E       For further information visit https://errors.pydantic.dev/2.13/u/class-not-fully-defined
.../site-packages/litellm/types/utils.py:1290: PydanticUserError
>                   raise APIConnectionError(
E                   litellm.exceptions.APIConnectionError: litellm.APIConnectionError: `Message` is not fully defined; you should define all referenced types, then call `Message.model_rebuild()`.
E                   Traceback (most recent call last):
E                     File ".../site-packages/litellm/main.py", line 5160, in completion
```

This is the issue's traceback, at the same line.

After the change, a fresh Python 3.10 environment installed from `pyproject.toml`
alone (`uv pip install -e ".[dev]"`) resolved litellm 1.96.2 and:

```
..                                                                       [100%]
2 passed in 5.76s
```

Version sweep on Python 3.10, smoke test only, wheel installs, pydantic 2.14.1:

| litellm | result |
|---|---|
| 1.92.2, 1.93.0, 1.96.2 | pass |
| 1.97.0 | FAIL — `Message` is not fully defined |
| 1.98.1, 1.99.4, 1.100.5 | FAIL — `ImportError: cannot import name 'NotRequired' from 'typing'`, inside litellm's anthropic compaction module |
| 1.101.0 – 1.101.6, 1.102.4, 1.103.5, 1.104.3, 1.105.1, 1.106.0 | pass |

On Python 3.12 (what CI runs): 1.96.2, 1.97.0, 1.106.0 all pass.

I chose `>=1.93,<1.97` rather than excluding only 1.97–1.100: 1.93.0 and 1.96.2 are
the only releases a real recording run has been confirmed on in the human's
environment, and CI cannot see a 3.10-only break, so the ceiling is what stops a fresh
install drifting into an untested release.

## Suite and linters

- First full run: 24 failed, 1854 passed. All 24 were `tests/benchmark/test_corpus.py`
  and `tests/benchmark/test_rating_regression.py` failing because the cloud clone was
  shallow and had no `corpus/*` tags (`UnresolvableRevisionError`). After
  `git fetch --unshallow` and `git fetch --tags`, all 24 passed when re-run.
- Full re-run after that, on the fix commit: `1878 passed, 2 xfailed in 421.63s`.
- `ruff check .`: All checks passed. `ruff format --check .`: 262 files already formatted.

## Check

Run from a main checkout (`/tmp/main-checker-wt`), run `88cbdc1752620600`. Verdict
INCOMPLETE. Every obligation shows `(no mapped test)`, including the ones the new smoke
test file plainly exercises — that looks like a mapping failure, not a judgement on the
tests. Most enumerated defects are "the ceiling is too low" or "the floor is too high",
i.e. the tool treats a deliberately conservative bound as a defect. Not acted on.

## Deferred

### [2026-10-19] CI runs only Python 3.12, so it cannot see the 3.10-only litellm break #278 was about
- **Kind:** defect
- **Found during:** #278, headless run
- **Where:** .github/workflows/ci.yml, `python-version: "3.12"`
- **Severity:** should-fix
- **What's wrong:** litellm 1.97.0–1.100.x break only on Python 3.10, the
  `requires-python` floor and the human's worktree Python. CI on 3.12 passes them, so
  the new smoke test in CI would not have caught #278's break. The ceiling in
  `pyproject.toml` is what protects us now.
- **Why I didn't act:** `.github/` is outside the files this run may change.
- **Drafted fix:** run the test job as a matrix over `["3.10", "3.12"]`, or at least
  run `tests/test_litellm_smoke.py` on 3.10 as a second job.
- **Status:** open

### [2026-10-19] The fixbug-cloud worktree command fails as written
- **Kind:** defect
- **Found during:** #278, headless run
- **Where:** .claude/commands/fixbug-cloud.md, step 8
- **Severity:** nice-to-have
- **What's wrong:** `git worktree add --no-track /tmp/main-checker origin/main` fails
  with `fatal: --[no-]track can only be used if a new branch is created`, and still
  leaves `/tmp/main-checker` behind containing only the `.venv` the next line creates.
- **Why I didn't act:** `.claude/` is on the no-go list.
- **Drafted fix:** `git worktree add --detach /tmp/main-checker origin/main`, which is
  what this run used (at `/tmp/main-checker-wt`).
- **Status:** open

### [2026-10-19] Cloud clones are shallow and tagless, so 24 corpus tests fail on a fresh session
- **Kind:** defect
- **Found during:** #278, headless run
- **Where:** tests/benchmark/test_corpus.py, tests/benchmark/test_rating_regression.py
- **Severity:** nice-to-have
- **What's wrong:** the cloud session's clone is shallow and has no `corpus/*` tags, so
  the corpus tests fail by design until `git fetch --unshallow` and `git fetch --tags`.
  A headless run that does not know this reads 24 failures as its own.
- **Why I didn't act:** the failure is designed behaviour; the fix is in setup.
- **Drafted fix:** add `git fetch --unshallow origin; git fetch --tags origin` to the
  fixbug-cloud setup steps (or a SessionStart hook).
- **Status:** open

### [2026-10-19] check maps no test to any obligation when the change's own new test file is the evidence
- **Kind:** filing (child of #182, test discovery & mapping)
- **Found during:** #278, headless run, check run `88cbdc1752620600`
- **Where:** src/acceptance/evidence/mapping.py (believed, not verified)
- **Severity:** should-fix
- **What's wrong:** every obligation in `check.log` reads `(no mapped test)`, including
  "The selected litellm release can build a model response", which
  `tests/test_litellm_smoke.py::test_litellm_builds_a_model_response_on_the_default_completion_path`
  tests directly. Yet the defect-injection section says "2 candidate test(s) ran", so
  tests were found but not mapped.
- **Why I didn't act:** out of scope; not investigated.
- **Drafted fix:** filing — check the mapping transcript for run `88cbdc1752620600`
  and record whether `obligation_ids` came back empty (see DR-164, where an M4 mapping
  call returning mostly empty `obligation_ids` was found to make a review half-blind).
- **Status:** open
