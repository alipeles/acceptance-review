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
`0923f77`. **Gate 1 passed at run 2** (`078d216`); no code written yet.

Three lanes in parallel: **#180** (evidence-rating stability), **#228**
(benchmark guard), **#214** (this one).

## The design — settled with the human, two rulings

**Ruling 1: coverage keys off the requirement's disposition, not its text.**
Disposition is already structured and *enforced*, in two layers: the model-facing
discriminated union `_Yielded` / `_NoObligation` / `_RaisedOpenQuestion`
(`obligations.py:300-340`, `Literal` tags, and `_Yielded` splits its first
obligation into its own required field so "at least one" is unrepresentable
otherwise), and the persisted `RequirementDisposition` whose validator rejects
`yielded` with no obligations and `no_obligation` with no reason.

So there is a hard rule with no judgement call in it, and the four cases are:

| disposition | can a requirement vanish? |
|---|---|
| `yielded` | No — validator makes obligation-free `yielded` unrepresentable |
| `no_obligation` | No — **trusted**, exempt by rule |
| `open_question`, unresolved | No — already forces `needs_clarification` |
| `open_question`, **resolved by the diff** | **Yes — this is the hole** |

A bare section marker is exempt because it is `no_obligation`, not because it is
short. **My earlier ≤3-words heuristic is dead** — do not resurrect it.

The accepted price: ten declines with identical boilerplate now return clean.
Defensible because #153 made scope exclusions yield obligations at source, and
re-judging whether a decline was *correct* is #193/#211's job, not the verdict's.

**Ruling 2: derived obligations from resolved open questions are in scope.** An
implementation choice that settles an ambiguity cannot ship untested.

## How the derived obligation is built

One field added to the open-question resolution schema: when `resolved=true`, the
model also returns the behaviour the diff commits to, as one requirement-shaped
sentence. **Everything else is fixed in code, not inferred:**

- `explicit=False` — the field already means "inferred, not stated in the mandate"
- `type=functional`, `importance=normal` — constants
- `coverage_status="addressed"`, `coverage_refs` = the `diff_refs` the resolution
  already cited. **So a derived obligation can never be a coverage gap** — it
  rides the test-evidence axis only, and reaches the verdict through the existing
  weak-evidence path. Untested choice -> `incomplete`.
- **`id` computed deterministically from the question id, never model-minted.**
  Required by this task's own byte-identical-rerun constraint, and by #180's
  carry-forward design (see below).
- Only questions that are resolved **and** cite at least one hunk qualify.

Why not synthesize from the existing `rationale` instead, avoiding the prompt
change: `rationale` is written to explain *what the diff shows*, not to state
required behaviour. Templating it produces obligations phrased as commentary,
which mapping and discrimination then run on — a false red the builder cannot fix
by changing anything of theirs.

## Coordination with #180 — asked and answered

Asked whether the `open_questions.py` prompt/schema change collides. Answer: **no
overlap, and no request-key change in its lane.** A determinism-component child
(provisionally #180.3) *would* touch the key, but is unfiled and out of its
session's scope; re-ask if it is picked up.

**Correction from #180, verified in `llm.py:81-108` rather than taken on trust:**
`request_key` hashes each *individual* request dict and `TranscriptStore` files
per key, so editing one stage's prompt orphans **only that stage's** recordings.
CLAUDE.md's "changing a prompt invalidates recorded transcripts" reads broader
than it is. Global invalidation needs a change to `request_key` itself or to
something folded into every request (model id, seed).

**#180's warning, acted on:** its design is heading toward re-judging an
obligation only when that obligation's own inputs changed, so ratings carry
forward across runs. A derived obligation whose id moved between runs would look
like one vanishing and a new one appearing — never carrying forward, and silently
re-judging while looking stable. Hence the deterministic id above.

Expect textual merge conflicts with #180 in `review_state.py` (both adding
fields) and `pipeline.py` (different regions). **Rebase early.**

## Gate 2 — NOT CLEAN, runs 1 and 2

Implementation is complete and committed (`bb1f1ef`); **993 tests pass, ruff
clean**. Gate 2 is INCOMPLETE, and this is a human call, not mine.

**Run 1's four findings were all real and all are fixed.** Two coverage gaps
(byte-identical review state had no test at all — it was in my mandate and I did
not write it) and two weak ratings (a declined-requirement test that could not
fail, and a coverage figure asserted on the result but never in the report).
Run 2 confirms: both gaps closed, both weak ratings moved to strongly supported.
Determinism test verified by injection — `uuid4()` in `derived_obligation_id`
fails it.

**Run 2's four findings are attributed to #180/#182.** The heads differ by three
added tests and no source change, yet 7 of 21 obligations moved rating and four
fell. `constraint-11` went `strongly supported` (two mapped tests) →
`unsupported` **with no mapped test at all**, both tests still present and
untouched. I read every recommendation first: three describe tests that already
exist — one of them cited by the same run as evidence for the obligation it says
lacks it — and the fourth asks for a test of something `derive_verdict`'s
signature already guarantees.

Same call as #153 and #235, same cause. Evidence in
`dogfood-logs/214-gate2-run1/` and `-run2/`.

## Gate 1 — passed, run 2

`dogfood-logs/214-gate1-run2/`. 29 requirements, 28 yielded, 1 deliberately
declined, **0 open questions**. Run 1 (`dogfood-logs/214-gate1-run1/`, 25
requirements) is superseded — it predates ruling 1.

`completion-01` = `- Implementation`, declined both runs on identical text as a
standalone section marker. That is #214's Acceptance item 4 live in this task's
own file, and under ruling 1 it is exempt for the right reason.

**One flag, attributed to the tool and queued:** `constraint-05` and
`completion-06` produced byte-identically-described obligations that failed to
merge, because an unrelated obligation was linked into their cluster and
`_confirmed_clusters` (`linking.py:382`) merges nothing in a cluster containing a
denied pair. Six other constraint/completion pairs merged correctly, so it is not
a wording problem. Everything stayed attached to its correct requirement, so the
set is sound to build against — but **if those two ids wobble at Gate 2, read it
as this defect, not as new evidence.**

## #214's Acceptance is partly stale — issue needs updating

- **Item 2** ("a review in which requirements produced no obligation cannot
  return `no_material_gaps`") is stale, per the human: it predates the
  realisation that some requirements legitimately yield none. Under ruling 1 it
  is wrong as written.
- **Item 4** (bare section marker not penalised) is now satisfied structurally
  rather than by a rule aimed at it.
- The `undisposed` bullet is already corrected on the issue
  (`issuecomment-5244447965`); implemented against `unread_source`.

**Not yet done: updating #214's Acceptance to match rulings 1 and 2.** Needs the
human's approval as a backlog write.

## Queue — `docs/DEFERRED.md`

One entry: **filing (blocker)** — a drafted comment on #180 carrying the
`constraint-11` evidence (a mapped set collapsing from two tests to zero across
an additive diff), which is a cleaner reproduction than the corpus holds.

Already filed this session: **#242** (linking merges nothing when one spurious
link joins a cluster), child of #181. The exemption-rule decision entry is
resolved and deleted — ruling 1 settled it.

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
