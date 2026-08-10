# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed, so it survives a context reset or a machine change — but still a
scratch record, not a plan. **The GitHub issue stays authoritative** (#168).
Clear it out when the task lands rather than letting it accrete.

*Last updated: 2026-08-10*

---

## Task in flight: #214

**The completion verdict cannot see mandate coverage.** Child of #185. Branch
`214-verdict-mandate-coverage`, worktree `~/acceptance-worktrees/`, branched at
`0923f77`. **Gate 1 passed** at `0923f77`; decomposition confirmed accurate by
Claude, awaiting human confirmation at the gate presentation.

Three lanes in parallel: **#180** (determinism/judgement — owns `llm.py` and the
request key), **#228** (benchmark guard), **#214** (this one). #214 stays inside
`verdict.py` / `report.py` and touches **no model prompt and no request key**, so
it cannot collide with #180's transcript re-record.

## Gate 1 — passed, run 1

`dogfood-logs/214-gate1-run1/`. 25 requirements, 24 yielded, 1 deliberately
declined, **0 open questions**, **0 unread source**. Nothing invented, nothing
missing, so no rewrite of `current-task.md` was warranted.

The single decline is `completion-01` = the bullet `- Implementation`, declined
as *"A standalone section marker with no requirement under it."* That is #214's
Acceptance item 4 arriving live in this task's own file — the item-4 fixture is
observed behaviour, not an invention for the test.

## The design (settled against the code, not yet built)

**Mechanism — a bound, not a branch.** Derive the verdict exactly as today, then
apply a coverage bound afterwards: a shortfall may only *cap* the verdict below
`no_material_gaps`, never move it. If the verdict was already `incomplete`, it
stays `incomplete`. This is what makes Acceptance item 3 (a dropping decomposer
never scores better) hold monotonically, and it adds no enum value and re-ranks
no existing precedence.

**Where a shortfall lands:** `unable_to_determine`. The existing
`if not obligations: -> UNABLE_TO_DETERMINE` is this same rule at its limit
(zero coverage), so generalising from "no coverage" to "partial coverage" keeps
one meaning, and matches the "uncertainty is first-class" invariant — an
uncovered requirement is uncertainty, not a pass.

**Item 1 (identical evidence, different coverage → different verdict)** is
satisfied on the `CompletionResult` *object*: the coverage figure is a new
first-class field and the rationale names the shortfall, so two such reviews
differ always, and differ in the enum whenever it would otherwise be positive.

**Schema:** `CompletionResult` gains a coverage field. Additive with a default;
no later work depends on it yet.

## Two things the issue assumes that the code has already settled

1. **`undisposed` does not exist.** M1.2.r2 removed it — a response that fails to
   account for a requirement does not parse. The Deliverable's second bullet is
   literally unimplementable. **Resolved:** corrected on #214 itself
   (`issuecomment-5244447965`); the bullet is implemented against `unread_source`,
   which carries the same meaning — unambiguous loss, still invisible to the
   verdict.
2. **Scope exclusions yield obligations again** since #153 (`0923f77`), in
   `CODE_ONLY` absence form. The #202 evidence in the issue body ("nine of ten
   scope exclusions stopped producing obligations") predates that, so the
   headline failure mode is partly closed at source. The verdict blindness this
   issue is about is not, and is independent of it.

## Queue — `docs/DEFERRED.md`

One entry, open, awaiting the human's call:

- **decision (blocker):** what exempts a declined requirement from the coverage
  bound — #214's Acceptance items 2 and 4 are in tension. Recommended structural
  exemption (≤3 words, no terminal punctuation); rejected uniformity-of-reason.

The `undisposed` entry is resolved and deleted — it was a correction to #214, not
a new filing, and it is posted.

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
  cwd-relative.
- **Each worktree needs its own `.venv`** — an editable install bakes an absolute
  path. This one's is correct (verified importing from this tree).
- **`gh pr create` with "Closes #a, #b, #c" only closes the first.**
- **Obligation ids are minted per response, not stable across runs** (#231).
- **Python here is 3.10; CI runs 3.12**; repo is `alipeles/acceptance-review`.

## Known open

**#210**, **#180**, **#193**, **#191**, **#196**, **#178**, **#214**, **#129**,
**#223**, **#224**, **#173**, **#225**, **#227**, **#228**, **#212**, **#231**,
**#236**, **#237**, **#239**.
