# 409 Gate 1, run 1 — judgement

Run `e01fdf6cc0825d46`, `decompose`, 4 requirements → 8 obligations, 0 open
questions. **Not accepted**; task file reworded and re-run as run 2.

## Findings

1. **A description of the current defect became obligations — tool defect,
   and also wording I regret.** `task-01` was a problem statement: what the two
   tests do today. It yielded `call-network-blocking-pytest-configure-directly`,
   `network-block-installed-in-test-process` and, worst,
   `preserve-installed-network-block` `[invariant/explicit]` — "the network
   block … remains in place after the direct `pytest_configure` call", which is
   the opposite of the fix. A correct implementation would be marked as
   breaking it. A problem statement is an ordinary part of a bug ticket, so a
   client task file will carry one; the decomposer should not read present-tense
   description of a defect as a mandate, and must never emit an invariant that
   preserves it. Not covered by #342 (a prohibition turned into what it forbids)
   — no negation is involved here. Drafted as a new filing under #181 in
   `docs/DEFERRED.md`.

   Rewording: I removed the problem statement (run 2). Rewritten because I regret
   the wording; reported anyway because a client would write it the same way.

2. **Two obligations for one property — tool defect, already tracked as #277.**
   `task-02` yielded `skip-network-block-installation` `[regression]` and
   `skip-network-block-installation-2` `[functional]`, both "neither test
   installs the network block; each skips it". One sentence, one property. Same
   shape as #277 (one requirement yields two obligations stating the same
   property in different voice). A comment recording this occurrence on #277 is
   drafted in `docs/DEFERRED.md`.

3. `socket-module-restored-after-tests`, `regression-test-block-left-installed`,
   `no-network-block-implementation-change` — correct.
