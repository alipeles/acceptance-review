# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed, so it survives a context reset or a machine change — but still a
scratch record, not a plan. **The GitHub issue stays authoritative** (#168).
Clear it out when the task lands rather than letting it accrete.

*Last updated: 2026-08-09*

---

## Task in flight — #232 + #219 + #230, at Gate 2

Branch `232-decomposition-prompt-shaping`, off `eb182de`. Nothing pushed, no PR.
**Gate 2 presented and not clean** — see below. Awaiting the human's call.

## What shipped

- **`ObligationType.TEST_DEMAND`** — a demand for a test is its own type, and
  spec §7.3 gains it. `docs/DR-232-test-demand-obligation-type.md`.
- **Derivation prompt** picks the type from the requirement's own text, never
  because another bullet asks for a test of the same behaviour.
- **Scope exclusions decline uniformly**, with the reason barred from stating
  anything the change must hold. The positive-restatement rule explicitly does
  not apply to them — it inverts, because an exclusion names *work* and work has
  no positive form.
- **Linking skips a mixed pair** rather than asking (`_can_state_one_requirement`).
  A question with one admissible answer is not a question, and a wrong `true`
  lands in a transitive component where the clique rule suppresses every other
  merge in it.
- **`tests/prompts/test_decomposition_prompt.py`** — new recorded corpus, 18
  tests, asserting on the type rather than on substrings.

Measured on this repo's own task file: exclusions inverted 4/6 → **0/6**;
Completion expectations keeping their demand 0/5 → **5/5 typed**; invented
framing on Constraints 3/8 → **0/8**; behaviour↔test merges 3 → **0**.

## Gate 2 — not clean, and not because of unmet requirements

15 obligations, all *addressed*, no open questions, **6 rated below strongly
supported**. Full analysis in `dogfood-logs/232-gate2-run2/judgement.md`.

The blocker is that the gate **does not converge**. Between run 1 and run 2 the
only change was two added tests, which fixed run 1's one finding — and five
untouched obligations degraded. `tests-no-live-model-calls` went strongly →
partially while its mapped set **grew** from 6 tests to 8. That is #180
(judgement stability) plus #182 (mapping churn).

**Do not try to close this by adding tests.** That is what produced the
regression.

## Do not rediscover

- **`acceptance check ... > dogfood-logs/<run>/output.log` cannot be replayed.**
  `check` reads the working tree as head, the shell creates the redirect target
  first, so the log joins the diff under review and the coverage request key
  moves between record and replay. It fails with `no recorded transcript`, under
  a message blaming a prompt edit. **Capture outside the repo and copy in.**
  Queued as a filing.
- **Two prompt attempts failed before typing worked.** Told to keep the test
  framing, derivation began *inventing* it on Constraints that demand no test.
  The prompt cannot carry this distinction; the type can. DR-232.
- **The linking prompt's own criteria point the wrong way here** — the test that
  asserts X is also the evidence for X, so "the same test would demonstrate
  both" reads true. That is why it is enforced in code.
- **Gate 1 could not be clean for this task by construction** — every Completion
  expectation in this repo's convention used the framing #232 dropped.
- **#153 looks stale** — open as "decompose never learns the exclusion section
  exists", but #219's body says #202 fixed exactly that. Candidate to close.
- **Obligation ids are minted per response, not stable across runs** (#231).
- **`decompose|check --mode record` writes nothing to stdout when redirected.**
- **Python here is 3.10**; repo is `alipeles/acceptance-review`.

## Queue — `docs/DEFERRED.md`

Two open, both filings, both from Gate 2:

1. `acceptance check` reviews its own output file — needs your call on the parent
   umbrella (#185, or a new change-stage one).
2. Adding two tests moved five unrelated obligations — comment on #180,
   cross-referencing #182.

Filed earlier this session: **#234** (child of #184), comments on **#230** and
**#212**.

## Known open

**#210**, **#180**, **#193**, **#153**, **#191**, **#196**, **#178**, **#214**,
**#129**, **#223**, **#224**, **#173**, **#225**, **#227**, **#228**, **#212**,
**#230**, **#231**, **#232**, **#219**, **#234**.
