# DR-405 — run a project's tests with the command the user already runs them with

**Issue:** #405 (`check` runs no tests when the Python project is in a
subdirectory with its own `pyproject.toml` and virtualenv).
**Resolved:** 2026-10-23, in conversation with the owner, before implementation.
**Status:** resolved. Amends spec §17 (execution safety) and §13.7 (non-goals);
leaves DR-170 Decision 6 (the interpreter is configuration, not inference)
standing.

## What was wrong

The execution tier ran a project's tests with the checker's own interpreter,
from the repository root, inside a sandbox that blocks the network (loopback
included) and drops every environment variable outside a short allowlist.

On a repository laid out as `api/pyproject.toml` + `api/.venv/` + `api/tests/`,
with a suite that needs Postgres and `DATABASE_URL`, that ran nothing:

1. pytest took `api/` as its root and named tests `tests/x.py::t`, while the
   review asked for `api/tests/x.py::t`, so no collected test matched.
2. The checker's interpreter had none of the project's dependencies.
3. The sandbox removed `DATABASE_URL` and blocked the connection to Postgres.

Every test was reported as one pytest "declines", and every defect as
`not_attempted`. A check could never come out clean on such a repository.

## Decision 1 — the user names the command; nothing is inferred

The user sets, once per repository, the command they already run their tests
with (`acceptance set-test-command "cd api && .venv/bin/python -m pytest"`).
The tool runs exactly that command and adds only the plugin and the tests to
run.

**Rejected: working out the interpreter and directory from the project's
files** — nearest pytest configuration, a `.venv`, `uv.lock`, `poetry.lock`.
Every such rule is wrong for some repository, each needs its own exceptions,
and the owner wanted no judgement applied to how tests are run. A command the
user runs every day is known to work. This is DR-170 Decision 6's position
("the interpreter is configuration, not inference"), widened from the
interpreter to the whole command.

## Decision 2 — under the user's command, tests run as on the user's machine

With a test command set, the run inherits the user's whole environment and the
network block is off. Only the time budgets remain. This is a deliberate change
to spec §17's "sandbox with no network/secrets": these are tests the user runs
anyway, and a database-backed suite cannot run any other way. Without a test
command, the locked-down sandbox is unchanged.

**The risk is real and is not the user's everyday one.** The tool runs the
tests against copies of the code broken on purpose. A planted defect can delete
every row instead of one, against whatever `DATABASE_URL` names, or call an
outside service once per defect.

## Decision 3 — the safeguards are generic; the protection is the project's

Only the project can make its tests point at a throwaway database. What the
tool does for every project:

- **Agreement, from a person.** `set-test-command` shows the risk in plain
  words and saves only on a typed "yes" at a terminal. There is no `--yes`
  flag: a coding agent runs commands without a terminal, and an agreement it
  could give for the user protects nothing.
- **The agreement is bound to what was agreed.** The saved file carries a
  fingerprint of the command and the parallel count. A file edited by hand no
  longer matches and is refused, not run. Setting a different command asks
  again and names what it replaces.
- **Visible every run.** `check` prints the command and the names of the
  environment variables passed — never their values, which would print a
  database password.
- **One run at a time, unless the user says otherwise.** See Decision 4.

**Rejected: judging whether a database "looks like production".** That is
guessing again, and a wrong "looks safe" is worse than none.

## Decision 4 — parallel runs are the user's to allow

Two runs against one database can corrupt each other's results, so by default
the tool never runs two copies of the suite at once. The owner asked for
parallelism wherever possible, because slow runs will become a problem: the
user may say `--parallel N` when setting the command. Runs then hold one of N
numbered slots, and each is told its number in `ACCEPTANCE_WORKER` (1 to N),
so a project can give each run its own database — the same convention as
pytest-xdist's `PYTEST_XDIST_WORKER`.

The limit is on test runs only. The model calls that build each broken copy
stay concurrent as before, so `--parallel 1` slows only the part that touches
the user's services.

## Decision 5 — test ids are matched relative to the project root, in both modes

The plugin renames every test it reports from pytest's own root to the
project root, and writes the collected names to a file rather than having the
runner parse pytest's printed output. Ids on the command line are absolute
paths under a test command, because the command may change directory first.
This fixes cause 1 for the locked-down run too.

## Consequences

- **Copies link `.venv` back to the original** instead of leaving it out, so
  a command naming `.venv/bin/python` works in the copies broken code runs in.
  A copy handed to a coding agent to edit gets no link.
- **Test discovery no longer offers fixtures as tests.** A changed file under
  `tests/` is a source of tests only if pytest would collect from it by
  default — `test_*.py` or `*_test.py` — so `conftest.py` is not.
- **The "pytest declines this test" message** says to set a test command when
  no command is set and nothing at all could be collected.
- **No model request changes**, so every recorded transcript keeps replaying.
- **Not decided here:** a way to name the setting file, or to read a test
  command from the project's own files.
