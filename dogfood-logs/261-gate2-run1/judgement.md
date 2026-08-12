# Judgement — #261/#239 Gate 2, run 1

**Gate 2 is NOT clean.** The run did not complete: `check` aborted before
producing a report.

```
acceptance: model error: no recommendation for 9 of 12 weak obligation(s):
partition-test-is-not-ignored, dev-dependencies-pin-ruff-exact-version,
build-runs-formatting-check, build-fails-on-formatting-check-report,
build-fails-on-lint-check-error, lint-step-preserves-lint-exit-code,
checkout-action-not-node20-major, python-setup-action-not-node20-major,
python-sources-formatter-and-lint-clean
```

Base `548e303` (pre-format `main`), head `5d46b62`. Revisions in
`revisions.txt`; the exact task file is alongside.

## What completed before the abort

Everything up to and including coverage classification. **All 19 obligations
were classified `addressed`, unanimously** — no `unclear`, no `not_addressed`.
The rationales cite real diff hunks; the classification for
`python-files-ruff-format-clean`, for instance, points at `ci.yml#2` and two
reformatted test files.

So the failure is not "the work is incomplete." It is one stage downstream of a
complete and confident coverage answer.

## The defect: the recommender has no way to say "no test can evidence this"

`coverage/recommendations.py:182` requires a recommendation for **every** weak
obligation and raises `SchemaValidationError` otherwise. The check is deliberate
and its comment explains why: a response answering 3 of 5 used to produce a
report where two silently carried no recommendation, which was indistinguishable
from a complete answer. That reasoning is sound.

What it does not allow for is a weak obligation for which *no test is the right
instrument*. The model's answer here was not partial — it was **principled**. It
returned recommendations for exactly the three obligations a pytest could
evidence:

| answered | why a test fits |
|---|---|
| `python-files-ruff-format-clean` | a test could invoke the formatter |
| `python-files-ruff-check-clean` | a test could invoke the linter |
| `partition-test-expects-specific-exception` | it *is* a test |

and declined the nine that are properties of `ci.yml` steps, GitHub Action major
versions, and a version pin in `pyproject.toml`. There is no pytest that
sensibly evidences "the build's checkout action is not on Node 20." The model
was right; the stage treats being right as a schema violation.

**Consequence, and why this is more than cosmetic: a configuration-only change
cannot be reviewed at all.** The failure is a hard abort, not a degraded report,
so the tool produces nothing — not a verdict, not the 19 `addressed`
classifications it had already computed. Any future change to CI, packaging or
tooling hits this.

Recorded before the run, in `dogfood-logs/261-gate1-run2/judgement.md`: *"none of
the 19 obligations can be supported by a pytest… the question to settle at that
gate is whether the tool has any evidence path for a configuration-only change."*
The answer is that it has none, and the absence is fatal rather than graceful.

Filed as a child of **#185** (`coverage/`, verdict, presentation).

## Disposition

Attributed to a tool defect, with the filing drafted in `docs/DEFERRED.md` before
moving forward, per *Rules that apply at both gates*.

**Not addressed by adding tests, deliberately.** The three obligations the
recommender *did* answer include two that want a test invoking ruff — and the
human ruled at Gate 1 run 1 that tests exercise the behaviour of the code and
must not be aware of the linter. Writing them to move a rating would be chasing
the gate, and would not touch the nine that caused the abort.

**Not addressed by rewriting the task file.** The nine obligations are faithful
restatements of what #239 actually asks for. Softening them to dodge the
recommender would hide the defect, which the gate forbids.

## Second, smaller finding: the recommendation stage does not partition

`recommend_tests` makes **one** `client.complete` carrying every weak obligation
— 12 here — and passes no partition. That is the same shape #191 is fixing in
`judge_discrimination`, and it means the stage is invisible to
`partition_sizes_in_force`. It did not cause this failure (the split was
principled, not a truncation), but it is worth recording on the same filing:
the abort message's severity scales with the batch, since one unanswerable
obligation among twelve discards the other eleven.

## Acceptance items — status

| # | item | status |
|---|---|---|
| #261 | `ruff format --check .` exits zero | **verified** — 117 files clean |
| #261 | CI fails a PR introducing an unformatted file | **written, not observed** — needs a CI run |
| #261 | formatting commit changes no behaviour | **verified** — 1107 passed before and after; AST byte-identical for 51 of 52 files |
| #239 | `ruff check .` exits 0 | **verified** — "All checks passed!" |
| #239 | B017 fixed by asserting the specific exception | **verified** — `ValidationError`, no noqa |
| #239 | ruff version-pinned | **verified** — `ruff==0.16.2` |
| #239 | `ci.yml` fails on lint errors, `\|\| echo` gone | **written, not observed** |
| #239 | actions bumped off Node 20 | **written, not observed** — v7 / v7 |
| #239 | `fetch-depth: 0` still behaves | **NOT verified** — needs a CI run |

The last one is the item #239 flags as able to turn #190's suite red wholesale.
It cannot be checked locally: it depends on how `actions/checkout@v7` behaves on
a runner. The release notes say the v5→v7 breaking changes are fork-PR checkout
for `pull_request_target`/`workflow_run` and a move to ESM, neither touching
fetch semantics — but that is an argument, not evidence, and #239 explicitly
says to verify rather than bump blind.
