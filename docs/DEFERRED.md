# The bundled queue

Things found mid-iteration that were deliberately not acted on at the time.
Claude queues here instead of interrupting; the queue is presented at the next
gate and worked with `/triage`. See `CLAUDE.md` *Working agreement* §4.

Resolved entries are deleted. Anything filed lives on GitHub, which is
authoritative (#168), so keeping a second copy here only costs context; an
entry resolved without a filing is recorded in the commit that resolved it.

Kind: `defect` (a bug, smell, missing test, spec inconsistency, dependency
problem, outside the current task's scope) · `filing` (a drafted issue,
sub-issue, or comment asserting a new finding — nothing reaches GitHub until
approved at a gate) · `decision` (an open design decision, with the
recommendation and the alternative rejected).

Severity: `blocker` (an Acceptance item of the task in flight depends on it) ·
`should-fix` (real defect, no Acceptance item blocked) ·
`nice-to-have` (cleanup, ergonomics, docs).

---

### [2026-08-10] Dev tool versions are unpinned, so two checkouts lint differently
- **Kind:** defect
- **Found during:** #153, implementation
- **Where:** `pyproject.toml:15` — `dev = ["pytest", "ruff"]`
- **Severity:** should-fix
- **What's wrong:** Neither tool is pinned. A fresh `pip install -e ".[dev]"` in
  the #153 worktree resolved **ruff 0.16.2**; the main checkout has **0.15.22**.
  The same tree lints clean on one and reports **85 errors** on the other, none
  of them from any change — new rules in the newer ruff. CI does a fresh install
  too, so the version it lints with is whatever the index served that day, and a
  green CI is not evidence the next run is green. This bit directly: 85 errors
  appeared on a two-file change and had to be diagnosed before the real lint
  result was visible.
- **Why I didn't act:** pinning changes the dependency stance repo-wide and is
  not in #153's scope; it also wants a decision on floor-vs-exact pinning.
- **Drafted fix:** file as a child of **#184** (determinism & reproducibility as
  an owned component — this is the same class of defect one level out: the
  toolchain is an uncontrolled input). Pin exactly, `ruff==0.15.22` and a pytest
  pin, so CI, main and every worktree agree; bump deliberately as its own commit
  where the new rules can be read as a diff.
- **Status:** open

### [2026-08-10] #234 reproduced on main, with a fresh CI log
- **Kind:** filing
- **Found during:** #153, implementation (checking CI after pushing to main)
- **Where:** CI run 31402210525, commit `813fa71`, `tests/benchmark/test_fixtures.py:85`
- **Severity:** should-fix
- **What's wrong:** Not a new defect — a live reproduction of the flake #234 and
  #129 describe, on `main`, today. `test_materialization_is_deterministic[07-declaration-mismatch]`
  failed with matching `base_sha` and differing `head_sha`
  (`143940c7…` vs `1f50fdb8…`); 932 passed. The run immediately before and after
  were green, on adjacent commits touching only `.claude/settings.json` and
  `CLAUDE.md` — so nothing in the tree explains it.
- **Why I didn't act:** it is the other lane's issue (#234), and fixing it here
  would collide with that branch.
- **Drafted fix:** comment on **#234** attaching this run:

  > Reproduced on `main` at `813fa71`, CI run
  > [31402210525](https://github.com/alipeles/acceptance-review/actions/runs/31402210525).
  >
  > ```
  > FAILED tests/benchmark/test_fixtures.py::test_materialization_is_deterministic[07-declaration-mismatch]
  > E       AssertionError: assert '1f50fdb860fd...e0774e0eab7eb' == '143940c7e9c9...5d73d697f4ade'
  > 1 failed, 932 passed in 40.21s
  > ```
  >
  > `base_sha` matched and `head_sha` did not, so whatever varies is confined to
  > the second commit. The runs on the commits either side were green, and all
  > three touched only `.claude/settings.json` and `CLAUDE.md` — nothing in the
  > tree accounts for it, which is consistent with #234's reading that the
  > variation is in materialization rather than in the fixtures.
- **Status:** open

### [2026-08-10] A requirement forbidding a test recommendation is typed `test_demand`
- **Kind:** filing
- **Found during:** #153, Gate 1
- **Where:** `src/acceptance/requirement/obligations.py` (type derivation); observed in `dogfood-logs/153-gate1-run1/output.log`, `constraint-03`
- **Severity:** should-fix
- **What's wrong:** The requirement *"No test is recommended for an obligation
  that admits code evidence only"* derives an obligation typed `test_demand`.
  Its demand is the **absence** of a test recommendation, not the presence of a
  test. Per DR-232 `test_demand` means the obligation's demand *is* the test, so
  a downstream stage seeking a test to satisfy it would be satisfied by exactly
  the evidence the requirement forbids. `functional` or `invariant` is right.
- **Why I didn't act:** assigning obligation types is a scope exclusion of #153
  (#205 owns it).
- **Drafted fix:** comment on **#205**, as evidence for assigning types in a
  separate pass:

  > Another case where the type is pulled by vocabulary rather than by the
  > demand. From #153's Gate 1 decompose (`dogfood-logs/153-gate1-run1/`):
  >
  > ```
  > [constraint-03] No test is recommended for an obligation that admits code
  >     evidence only.
  >     -> no-test-recommended-for-code-evidence-only  [test_demand/explicit]
  > ```
  >
  > This is #232's failure shape in the inverse case. #232 stopped derivation
  > inventing test framing on Constraints that demand no test; here the
  > requirement *forbids* a test recommendation and still types as
  > `test_demand`, because the word "test" is in the text. DR-232 defines
  > `test_demand` as "the obligation's demand is the test", so any downstream
  > stage looking for a test to satisfy this obligation is satisfied by
  > precisely the evidence the requirement rules out.
  >
  > #232's recorded corpus (`tests/prompts/test_decomposition_prompt.py`)
  > asserts on the type rather than on substrings, but has no case where the
  > requirement is a *prohibition* on tests. Worth a corpus case whichever way
  > #205 lands.
- **Status:** open
