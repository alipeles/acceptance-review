# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed, so it survives a context reset or a machine change — but still a
scratch record, not a plan. **The GitHub issue stays authoritative** (#168).
Clear it out when the task lands rather than letting it accrete.

*Last updated: 2026-08-10*

---

## In flight: #228 — a benchmark case yielding zero requirements must fail, not score

Branch `228-benchmark-empty-registry`, worktree
`~/acceptance-worktrees/228-benchmark-empty-registry`, branched from `0923f77`
(= `origin/main`). Child of **#186**.

**One of three parallel lanes** — #180 and #214 are running in their own
sessions. **This lane touches no model prompt**, so it forces no transcript
re-record and cannot collide with theirs on the request key.

## Gate 1: PASSED at `0923f77`

Two runs, both saved: `dogfood-logs/228-gate1-run1/` and `-run2/`.

- **Run 1** — 18 requirements, 17 obligations, 1 deliberately none, **no open
  questions**. Decomposition accurate. Two of my own bullets were weak:
  `constraint-05` overreached beyond what #228 asks, `completion-03` was
  ungrammatical. Both are authoring defects, not tool defects.
- **Run 2** — re-run after rewriting three bullets (`constraint-05`,
  `completion-03`, `completion-05`). Same shape, clean, no open questions.

Decomposition confirmed accurate by **Claude, awaiting human confirmation** —
presented at the gate, not yet signed off.

## The finding that shaped the plan

`constraint-05` originally said *"No case reaches a scoring hook without having
been checked."* That is not achievable and not what #228 asks. Benchmark scoring
hooks are also driven by synthetic cases built inline in tests whose task text
(`"## Deliverable\n...\n"`, `"..."`) has no `# Task` heading and therefore
**yields an empty registry too**. An unconditional guard at hook entry would
fail `test_runner.py`, `test_scoring.py`, `test_alignment.py`, `test_case.py`.

So the guard goes on the **corpus case builders**, which is exactly the scope
#228's Acceptance names. The synthetic-case problem is queued as a filing.

## Plan (presented at Gate 1, not yet approved)

- `benchmark/case.py` — `EmptyRequirementRegistryError` + a guard function.
  `case.py` is the home because `fixtures.py` and `corpus.py` both already
  import from it, and it has no cycle with `requirement/`.
- Call the guard from all three builders: `fixtures.py::build_benchmark_case`,
  `corpus.py::build_decompose_case`, `corpus.py::build_corpus_case`.
- New `tests/benchmark/test_empty_registry_guard.py`.
- `requirement/obligations.py:443-446` — the comment claiming all thirteen
  archetypes produce an empty registry is **stale** since `1c53592`. Fix it.

## Verified at `0923f77`, before any change

- Full suite **green: 972 passed** in 3m45s.
- **Every** task file in `archetypes/` (13), `decompose-regression/` (8) and
  `rating-stability/` (6) parses to a non-empty registry. The guard therefore
  changes no current outcome, and cannot be demonstrated by the corpus — which
  is why Acceptance item 3 demands a test-supplied unparseable file.

## Queue — `docs/DEFERRED.md`

**One open filing:** `run_case`'s own acceptance test cannot fail, because its
task file yields no requirements (`test_runner.py:46`, `:73`). Child of #186.
Drafted in full with evidence; needs approval before filing.

## Do not rediscover

- **`.acceptance/ignore` is committed** (#105) and holds `dogfood-logs/`.
- **`decompose|check --mode record` writes nothing to stdout when redirected** —
  pipe through `tee`, which works.
- **A `PostToolUse` formatter hook reformats files after every edit.** It strips
  imports added ahead of their first use — so some churn in a diff is not the
  author's.
- **Permission prompts are caused by command shape, not vocabulary.** One command
  per Bash call; patterns may wildcard mid-string; naming `.env` in any command
  prompts regardless. **Approvals are not recorded anywhere** — only denials are.
- **`pytest` must run from its own tree** — `addopts`/`pythonpath` are
  cwd-relative. Each parallel lane needs its own `.venv` (editable installs bake
  an absolute path).
- **`gh pr create` with "Closes #a, #b, #c" only closes the first.**
- **Obligation ids are minted per response, not stable across runs** (#231), and
  obligation *types* move too when the task text changes at all (#205).
- **Python here is 3.10; CI runs 3.12**; repo is `alipeles/acceptance-review`.

## Known open

**#210**, **#180**, **#193**, **#191**, **#196**, **#178**, **#214**, **#129**,
**#223**, **#224**, **#173**, **#225**, **#227**, **#228**, **#212**, **#231**,
**#236**, **#237**, **#239**.
