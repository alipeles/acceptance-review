# #372 — executed kill/survive labels from BugsInPy mutants

Labelled cases for the judgement "would this test fail if this defect were
present?", where every label comes from running the test, not from a model.
#371 (the experiment on whether TypeSafe's Jev can take over fixed-label
judgements) scores judges against them. The numbers are in `FINDINGS.md` and
`findings.json`.

## Method

The code is `src/acceptance/benchmark/mutants/`. The bug list is pinned in
`pinned_bugs.json`.

1. **Choose bugs.** 87 BugsInPy bugs from PySnooper, thefuck, tqdm and
   youtube-dl, with the dataset pinned at commit `11c5f1e`. These projects have
   light dependencies and offline tests. tornado, httpie and sanic were left
   out because their tests start local servers, which the sandbox's network
   block refuses.
2. **Edit the code.** Each edit is one mechanical change from a fixed operator:
   flip a comparison, change a constant, negate a condition, return `None`,
   swap `+`/`-` or `and`/`or`, or drop a `not`. Edits are placed only on the
   lines the bug's fix changed. The defect description is written from the edit
   itself, so it cannot claim more than was injected.
3. **Choose tests.** First the tests BugsInPy names for the bug, then tests from
   the same file whose source names the edited function, up to 4 per bug.
   Random extra tests were tried first and dropped: see Traps.
4. **Run the control.** The chosen tests run on the untouched code with
   `mutation/baseline.py`. A test that is already red is set aside, and its
   error is recorded.
5. **Run the edits.** Each usable test runs against each edit (up to 4 per
   bug), in a copy, through `execution/sandbox.py`. A case is one (edit, test)
   pair whose run completed. The requirement text is the fix commit's message.

## Rebuilding

Nothing derived from BugsInPy is committed. BugsInPy declares no license and
this repo is public (DR-168, the benchmark dataset choice). Everything is
rebuilt under the gitignored `.acceptance/mutant-labels/`:

```
.venv/bin/python -m acceptance.benchmark.mutants prepare   # network: run by hand
.venv/bin/python -m acceptance.benchmark.mutants build     # offline, about 20 min
.venv/bin/python -m acceptance.benchmark.mutants sample    # survivor spot-check
.venv/bin/python -m acceptance.benchmark.mutants report    # counts only
```

Two builds from the same pins gave byte-identical files (SHA-256 `3349d30d…`).

## Traps

- **Never run tests in the prepared checkout.** It sits inside this repo, so
  for a project with no pytest config of its own, pytest climbs to *our*
  `pyproject.toml`. Every test id then gets a `.acceptance/…` prefix and
  matches nothing. The first build lost 86 of 87 bugs this way. The build now
  works in a copy outside the repo.
- **Random extra tests make the survivors trivial.** They were killed 17 times
  in 419 (4%), because most never run the edited code. That held the killed
  share at 22%. Choosing extra tests that name the edited function raised it
  to 58%, and the survivors became tests that run near the edit and still miss
  it.
- **Some old tests do not run on the environment's versions.** Two clashes
  account for 25 of the 26 tests set aside by the control run. 12 are thefuck
  tests whose setup calls `item.get_marker`, which was removed in pytest 4; the
  sandbox needs pytest 6 or later, so pytest cannot go back. 13 are tqdm tests
  calling `sys.setcheckinterval`, which was removed in Python 3.9, the oldest
  Python available here. Together they lose 10 bugs. Each set-aside test
  records its real error.
- **`prepare` needs a CA bundle.** A python.org macOS interpreter has no root
  certificates by default, so every download failed until downloads were
  pointed at `certifi`.
