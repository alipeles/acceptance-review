# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed, so it survives a context reset or a machine change — but still a
scratch record, not a plan. **The GitHub issue stays authoritative** (#168).
Clear it out when the task lands rather than letting it accrete.

*Last updated: 2026-08-10*

---

## No task in flight

**#232 + #219 + #230 landed** as `14b2549` (PR #235, squash merge). `main` is
synced. `current-task.md` still holds that bundle's mandate — stale, and the next
task overwrites it at Gate 1.

## Next task — #153, and why it is next

**#153: scope exclusions carry no meaning downstream.** #235 made this *more*
true, deliberately and with the tradeoff recorded: exclusions now decline
uniformly, so nothing checks that one was respected. The agreed design is in
[#153's comment](https://github.com/alipeles/acceptance-review/issues/153#issuecomment-5241310422):

- Exclusions **yield obligations again**, marked as admitting **code evidence
  only**, with no test-support score at Gate 2.
- That marking is a **third axis** on `Obligation`, not an obligation type.
  `type` is what the obligation is; `coverage_status` is whether the code
  responds; `evidence_class` is whether the tests discriminate; this is which
  kinds of evidence apply at all. `review_state.py` already documents keeping
  those axes separate.
- **Open design point, to settle when implementing:** evidence for an exclusion
  is an *absence*, so it has no location to link to. Non-violation should
  probably be a completeness claim over the examined change set — "every change
  was checked against this exclusion and none breaches it" — rather than a
  listing of every file as supporting evidence. That needs an answer for the
  typed-and-linked invariant (link to the scope examined) and for evidence-tier
  discipline (a partial scan must not claim completeness).

Overlaps #148 (code-evident obligations); likely wants that mechanism.

## What #232/#219/#230 shipped

- **`ObligationType.TEST_DEMAND`**, and spec §7.3 gains it.
  `docs/DR-232-test-demand-obligation-type.md`.
- Derivation picks the type from the requirement's own text, never because
  another bullet asks for a test of the same behaviour.
- Scope exclusions decline uniformly; the reason may not state anything the
  change must hold.
- **Linking skips a mixed pair** rather than asking
  (`_can_state_one_requirement`).
- `tests/prompts/test_decomposition_prompt.py` — new recorded corpus, 18 tests,
  asserting on the type rather than on substrings.

Measured on this repo's task file: exclusions inverted 4/6 → **0/6**; Completion
expectations keeping their demand 0/5 → **5/5 typed**; invented framing on
Constraints 3/8 → **0/8**; behaviour↔test merges 3 → **0**.

## Gate 2 was not clean, and #235 merged anyway

On an explicit human call. 15 obligations, all addressed, no open questions, **6
rated below strongly supported** — none an unmet requirement. The gate does not
converge: between Gate 2 runs 1 and 2 the only change was two added tests, and
five untouched obligations degraded. Filed on **#180** with the evidence.
Analysis in `dogfood-logs/232-gate2-run2/judgement.md`.

## Do not rediscover

- **`.acceptance/ignore` is committed** (#105) and holds `dogfood-logs/`. Without
  it, `check` reads the working tree as head and a run's own redirected
  `output.log` joins the diff it is reviewing, so the run cannot be replayed.
  `.gitignore` names `.acceptance/cache/` and `.acceptance/reviews/`
  individually — the directory holds input as well as output.
- **`gh pr create` with "Closes #a, #b, #c" only closes the first.** #219 and
  #230 had to be closed by hand after #235 merged.
- **Two prompt attempts failed before typing worked.** Told to keep the test
  framing, derivation began *inventing* it on Constraints that demand no test.
  DR-232.
- **The linking prompt's criteria point the wrong way on a behaviour/test pair**
  — the test that asserts X is also the evidence for X, so "the same test would
  demonstrate both" reads true. Hence enforcement in code.
- **Obligation ids are minted per response, not stable across runs** (#231).
- **`decompose|check --mode record` writes nothing to stdout when redirected.**
- **Python here is 3.10**; repo is `alipeles/acceptance-review`.

## Queue — `docs/DEFERRED.md`

One open: the missing-transcript error blames an edited prompt, which was wrong
at Gate 2 and cost a diagnostic cycle. Needs a parent — #184 is the closest fit.

Filed this session: **#234** (child of #184), comments on **#230**, **#212**,
**#180** and **#153**.

## Known open

**#210**, **#180**, **#193**, **#153**, **#191**, **#196**, **#178**, **#214**,
**#129**, **#223**, **#224**, **#173**, **#225**, **#227**, **#228**, **#212**,
**#231**, **#234**.
