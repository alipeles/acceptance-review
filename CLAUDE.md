# CLAUDE.md — project context for coding sessions

Read this first. It captures the decisions and conventions for this repo so an
agent can work productively without re-deriving them. The source of truth for
scope and detail is `docs/AI-Assisted-Software-Development-Review-Spec.md` (the
spec); section refs (§) point at it. **GitHub is authoritative for anything with
a lifecycle** — tasks, open decisions, milestone sequencing. Files are
authoritative only for things with no lifecycle: the spec, resolved decisions
(`docs/DR-*.md`), and the standing invariants below. If a file and an issue
disagree about what the work is, the issue wins (#168).

## What this is

An independent **acceptance review** for software written by AI coding agents.
Given a change mandate and a proposed implementation, it decides whether the
tests actually demonstrate that the requested behavior was delivered, and
prescribes the evidence still needed. Personal project; goals: sharpen AI-domain
credibility, grow agentic skills, and build something individually useful without
enterprise setup.

## How to write to me

I have not seen what you have seen. I read your summary, not the transcript,
and I do not remember what the issue numbers mean. These rules apply to every
message, and a hook repeats them before every turn so they do not fade.

1. Plain English. Short sentences, ordinary words, no cleverness.
2. The first sentence answers the question that was asked. No heading, table,
   or preamble before it. If the news is bad, that sentence is the bad news.
3. Prose by default. A table only when comparing three or more things on three
   or more dimensions, and never as the opener.
4. Use only terms the spec or the code defines. A term you coined in this
   session is replaced with a plain description every time, or not used.
5. Every issue number, DR, or section reference carries a clause saying what
   it is, every time: not `#242`, but "#242, where one wrong link stops a group
   of duplicate obligations from merging".
6. Match length to the question. A one-line question gets a few sentences.
   Evidence goes after the answer, under a heading I can skip.
7. Name the thing, not its place in your context: the file, the test name, the
   obligation id, never "the test I mentioned" or "the second finding".
8. Say "I verified" or "I believe", and mean it. They are different sentences.

If a reply still reads as cryptic, `/plain` asks for it again with no
formatting. The rules are repeated in *Working agreement* §6.

## Stage 1 scope (what we're building now)

A **Local Completion Checker** plus the **validation benchmark** that measures
whether the checker works. GitHub Acceptance Review is Stage 2 — out of scope.

## Invariants — do not violate these

- **The checker stays local/GitHub-independent.** Its only inputs are a task
  file, Git revisions, source, tests, and an optional builder declaration. No
  GitHub App, hosted service, or CI access in the Stage-1 checker (§3.1, DoD #1).
  (Managing *our own* backlog on GitHub is separate from the product's inputs.)
- **Evidence-tier discipline is a data-model invariant, not a display choice.**
  Tiers: builder-claim < static < coverage-confirmed < defect-killed < CI-confirmed.
  A component may only raise a finding to a tier it's authorized to produce; a
  static analyzer can never emit `defect-killed` (§8.1, M0.3).
- **Every finding is typed and linked.** It carries a tier and links to exact
  requirement text / code lines / test locations. No free-text conclusions (§13.6).
- **Uncertainty is first-class.** `Indeterminate` and open-question outputs are
  valid, expected results — don't force a confident verdict (§9.3, §7.3).
- **Structured, persisted review-state**, not an unstructured model transcript
  (§12, §15). Build this store first (M0) so later components write into it.
- **Markdown is an input format and a rendering format — never an interchange
  format.** Anything the code has already parsed reaches the model as typed,
  identified fields, never re-pasted as raw source for it to re-derive.
  Responses are schema-constrained everywhere already; the gap is on the way
  *in*. `requirement/obligations.py::_user_prompt` handing the model
  `parsed.source` after `parse_task_file` has computed the structure is the
  shape to avoid — the parse is discarded and the model is asked to redo it.
- **Replay-first + determinism.** Model calls are schema-constrained and recorded
  for replay; capability tests run off recorded transcripts, no live calls
  (M0.4, M0.5). Two recorded runs over the same input must be byte-identical.
- **Positive results are bounded.** "No material gaps at the achievable tier,"
  never "proven correct" (§3.7).
- **`current-task.md` is an input to the checker — never a work log, and never
  edited to change what the review says.** Suppressing a finding or open question
  destroys the only signal that the tool is wrong; adding progress notes or
  decisions changes the decomposition. The one sanctioned edit is rewriting a
  *weak obligation* — requirement text that is genuinely badly worded — which is
  encouraged. **Fix the wording, never the output.** Session state belongs in
  `session-state/<issue>.md`.

## Tech

- Tool language: Python — it must parse Python ASTs and drive pytest.
- Code under review: Python; tests pytest; VCS Git; requirements as Markdown.
- Any execution (M8) runs sandboxed: no network, no secrets, targeted test
  subsets, short time budget, skipped when a hermetic-feasibility probe fails.

## How the tool runs — read before your first command

- **Replay is the default mode.** `RunConfig.mode` defaults to `Mode.REPLAY`, so
  the CLI, the test suite and CI never issue a live model call and need no API
  key. Opt into `RECORD` explicitly to call a provider.
- **Transcripts and cached reviews live in `.acceptance/cache/`** (gitignored).
  Record-if-missing, then replay.
- **Changing the model or the seed invalidates every recorded transcript;
  changing a prompt or a response schema invalidates that stage's.** The request
  key hashes each request individually, so a stage's recordings orphan when its
  own request changes, while every other stage keeps replaying — one lane's
  prompt edit does not force another lane to re-record. Either way a determinism
  control moved, so the recordings must be re-verified, and benchmark figures
  spanning that stage stop being comparable. Sequence prompt work to pay that
  cost once.

  **The per-lane part stops holding as soon as anything shared builds the
  request.** A change to common request-assembly moves every stage's key at the
  same time, so the whole corpus orphans in one go rather than one lane's — and
  "pay it once" becomes a repo-wide constraint rather than a per-lane one. Check
  whether what you are editing is a stage's own prompt or something every stage
  goes through before estimating the cost.
- Interpreter is `.venv/`. Provider keys, needed only when recording, come from
  `.env` (gitignored).

## Repo layout

- `docs/` — the spec (source of truth for the product), plus Decision Records
  (`DR-<issue>-<slug>.md`). No task list lives here; tasks are GitHub Issues.
- `.github/workflows/` — `ci.yml` (lint + tests) and `benchmark.yml` (accuracy
  report stub for M-B*.report).
- `tests/` — unit tests, plus `tests/fixtures/archetypes/` — the labelled cases
  the benchmark scores against.
- `current-task.md` — the task being worked right now, in the tool's own input
  format.
- `session-state/<issue>.md` — rolling state of one task in flight, carried
  across context resets. **One file per task, owned by that task's session**;
  delete it when the task lands, so the directory is the list of what is
  actually in flight. Committed, but still a scratch record: **the issue remains
  authoritative** (#168), and these files never become the plan.
- `dogfood-logs/` — one directory per dogfood run, holding its inputs, output
  and judgement. Committed; see *Dogfooding* below for the layout and why.
- `.acceptance/` — local run artifacts. Gitignored, never committed.

### `src/acceptance/` — the review pipeline

`pipeline.py::run_review` is the spine, and both consumers call it: the CLI
(`acceptance check`) and the benchmark (`benchmark/coverage.py::classify_case`).
A test pins that they share it — they had drifted before, leaving the CLI on an
M3-era chain. Stage order follows §10.1:

- `requirement/` — parse the task file, decompose into obligations, ingest the
  builder declaration (§7).
- `change/` — resolve revisions and build the diff under review.
- `evidence/` — discover candidate tests, **map** them to obligations, then
  extract evidence, judge discrimination, and classify strength.
- `coverage/` — classify implementation coverage per obligation, detect
  unrequested changes and their dispositions, resolve open questions, recommend
  tests, compare the declaration.
- `verdict.py` / `report.py` — derive the completion verdict from findings and
  render the §16 report.

Supporting: `review_state.py` + `review_store.py` (the persisted structured
review), `llm.py` + `config.py` (schema-constrained calls, determinism controls,
transcript record/replay), `serialization.py` (canonical form — byte-identical
reruns depend on it), `evidence_tier.py`, `source_ref.py`.

`benchmark/` is the measurement harness; it is not part of a review run.

## How work is tracked

GitHub **Milestones** (M0 … M9) group tasks; **Issues** are the individual tasks
(Inputs / Deliverable / Acceptance); labels `track:checker` / `track:benchmark`,
`human-gate` (needs human sign-off), `decision` (open design decision). The
Project board has an **Order** number field giving the strict sequence.

**The backlog is the plan.** There is no separate planning document — milestone
descriptions carry sequencing and dependencies, issue bodies carry task detail.
Write task detail into the issue, never into a file. A task revised *after* it
was delivered gets a **superseding issue** (`M7.3.r1` supersedes `M7.3`), not an
edit in place: the original acceptance check genuinely passed, and that record is
worth keeping. See #34 → #167.

**Tool defects found by dogfooding hang off a subsystem umbrella**, one per area
of `src/acceptance/`, labelled `umbrella` and holding its children as GitHub
sub-issues. Dogfooding generates defects faster than they can be fixed, and they
cluster: several children of one umbrella touch the same file, share one prompt,
and force the same transcript re-record, so they are sequenced together rather
than independently.

| umbrella | area |
|---|---|
| #181 | decomposition — `requirement/` |
| #182 | test discovery & mapping — `evidence/discovery.py`, `mapping.py` |
| #183 | evidence judgement — `evidence/discrimination.py`, `strength.py` |
| #184 | determinism & reproducibility — `llm.py`, `serialization.py`, `partition.py` |
| #185 | findings model, verdict & presentation — `coverage/`, `verdict.py`, `report.py` |
| #186 | benchmark — `benchmark/` |

File a new defect **as a child of its umbrella**, not standalone. Mapping and
evidence judgement are deliberately separate umbrellas: #167's Gate 2 showed they
fail independently — a byte-identical mapped set with a flipped judgement over it.

Which milestone proves which §13.5 demonstration scenario:

| # | Scenario | Proven by |
|---|---|---|
| 1 | Missed obligation | M1 + M3 |
| 2 | Qualifier missed | M3 |
| 3 | Superficial test (asserts existence) | M5 |
| 4 | Non-discriminating input | M5 (+ M8 to confirm) |
| 5 | Circular expected result | M5 |
| 6 | Critical behavior mocked out | M5 |
| 7 | Declaration mismatch | M6 |
| 8 | Unrequested change | M3 + M3.5 + M7 (M7.6 advisory presentation) |
| 9 | Local revision cycle (rerun) | M7 (incremental re-run over M0 state) |
| 14 | Execution-confirmed weak test | M8 |

Scenarios 10–13 depend on GitHub/CI and are Stage 2.

## Working conventions

- **One issue per branch and PR.** Keep diffs small and reviewable — that's how
  the human builds understanding without reading every line.
- **Process artifacts are committed to `main`, never to the branch under
  review.** `session-state/` and `docs/DEFERRED.md` are working records that
  no mandate ever asks for, so on a branch they are pure noise in two places at
  once: `check` reports them as `separable` on every run, and they crowd the PR
  diff — #257 changed 14 files of which 2 were the delivery. Commit
  `docs/DEFERRED.md` to `main` as it changes; commit your task's
  `session-state/<issue>.md` to `main` **at the gates**, leaving mid-task edits
  uncommitted in the working tree. **Touch only your own file** — sessions run
  concurrently and the sharding exists so that two gates landing at once do not
  collide. Both paths are also in `.acceptance/ignore`, as a backstop for when
  one reaches a branch anyway.
- **Never check out `main` to commit to it. Push a throwaway branch instead.**
  Uncommitted changes survive a branch switch, so the old advice was checkout /
  add / commit / push / checkout back. Do not do that. Git allows `main` to be
  checked out in only **one** worktree, so with several sessions running, every
  gate contends for it, and a session that finds `main` already taken — or that
  reaches into a worktree it does not own — commits onto someone else's branch.
  That happened: a `docs/DEFERRED.md` commit landed on `261-format-and-lint-gates`
  and reverted three of that session's queue edits, and undoing it took a reset
  of a branch belonging to another session.

  ```bash
  git fetch origin
  git branch --no-track tmp origin/main   # temp branch at main's tip; --no-track
                                          # so it runs sandboxed (see below)
  git switch tmp                      # your own worktree; edits survive the switch
  git add docs/DEFERRED.md session-state/<issue>.md   # explicit paths, never -A
  git commit -F <message-file>
  git push origin tmp:main            # updates origin/main directly
  git switch -                        # back to your branch
  git branch -D tmp
  ```

  Two rules carry the safety, and both are load-bearing: **branch from
  `origin/main`, not from `HEAD`** — branching from your own branch would push
  your feature commits to `main` — and **run git only in the worktree you own**.
  Never `git stash`, which reverts the working tree wholesale.
- **Push a `main` commit immediately.** An unpushed `main` commit reaches origin
  only inside the next branch's squash, attributed to the wrong PR.
- **A commit subject starting with `#` is silently destroyed on the editor
  path.** Git strips lines beginning with `core.commentChar`, which defaults to
  `#`, so `#261 Gate 2 — not clean` loses its subject and the second paragraph
  of the body silently becomes the subject. No warning, exit 0; you find out by
  reading `git log` afterwards. This repo's convention produces such subjects
  constantly.

  ```bash
  git -c core.commentChar=';' -c core.editor=true rebase --continue
  ```

  **It fires only when an editor is involved** — a *conflicted* rebase's
  `--continue`, a `reword`, or `--amend`. A clean rebase reuses the commit
  object and never opens one, which is why branches carrying these subjects
  survive rebase after rebase and then lose a message the first time a conflict
  appears. Verify with `printf '#x subject\n\nbody\n' | git stripspace
  --strip-comments`, which prints only `body`.
- **Before coding**, read the issue body and its Acceptance check, and state the
  plan before editing.
- **Dogfooding is a hard gate on shipping.** See *Dogfooding — the review gates*
  below, and follow it literally.
- **Test the wiring, not just the function.** Defect injection has repeatedly
  found the same shape of hole: a helper with a good unit test that the pipeline
  never actually calls. When you add a helper, test that the pipeline invokes it.
- **Measure as you build:** each capability milestone ends with a scoring hook
  into the benchmark harness (M-B0) — don't defer measurement to the end.
- **Surface open decisions, don't silently resolve them.** Open design decisions
  are tracked as `decision`-labeled issues, each owned by a milestone — that
  label *is* the list. Raise a new one rather than picking quietly; raising it
  means queueing it (*Working agreement* §4), not stopping the work.
- **The backlog's _content_ needs human review; its _commands_ do not.** Draft the
  item — title, body, labels, parent umbrella — and show it *alongside the
  evidence that produced it*. This covers `issue_write`, attaching a sub-issue
  with `sub_issue_write`, and any `add_issue_comment` that asserts a new finding
  on an existing issue.
  Editing your own draft after feedback is not a second approval; re-show it.
  The backlog is the plan (see *How work is tracked*), so filing is a change to
  the plan, and an agent that files as it goes writes the plan unsupervised.
  **The review is batched, not skipped.** Draft the item as part of the
  judgement, put it in the queue (*Working agreement* §4), and keep working;
  the queue is presented for approval at the next gate. Approval is what
  authorises the filing — the wait is until the gate, not until each item.
  Once the gate approves it, **file it without asking again**: the issue-writing
  commands are allowlisted, so nothing mechanically prevents an unreviewed
  filing. The rail is this rule now, not a permission prompt. Opening a PR,
  merging and pushing are a different category and still stop for approval
  (*Working agreement* §3).
- **Write a Decision Record when one is resolved**, or when a non-obvious finding
  changes the design: `docs/DR-<issue>-<slug>.md`, referenced from the issue. A
  decision that lives only in a commit message or a chat session is lost. See
  `DR-081` and `DR-164`.

## Dogfooding — the review gates

We run the tool against our own work in progress. It is the only place the tool's
own failures become visible, so it is a hard constraint on shipping. Two gates,
both mandatory, neither skippable because the change looks small.

**The tool must never be aware that it is being dogfooded.** The whole premise is
that we use it exactly as a client would, so `current-task.md` is an ordinary
mandate and nothing more. It never mentions dogfooding, gates, runs, or this
repo's own verification process, and it never makes one of them a requirement —
*"a dogfood run over a large task file loses no requirement"* is a thing **we
do**, not a thing the **software does**, and putting it in the input asks the
tool to derive an obligation the code can never satisfy. Acceptance items of that
kind are real and belong on the GitHub issue, which is our plan; they do not
cross into the tool's input. The issue says how we verify; the task file says
what the software must do.

Always save each dogfood run as a self-contained, committed directory under
`dogfood-logs/`, in the shape `tests/fixtures/rating-stability/` already uses —
so any run can later become a benchmark case:

```
dogfood-logs/<issue>-gate<n>-run<m>/
  current-task.md   the exact task file the run was given
  output.log        the full command output
  revisions.txt     base and head SHAs — `check` runs only
  judgement.md      which findings were real vs tool defects, and the triage
```

Two parts are easy to skip and both are load-bearing. **The revisions**: a task
file without its SHAs is not a reconstructable input, and `revisions.txt` is the
only reason #190's cases could use real inputs instead of invented ones. **The
judgement**: it cannot be reconstructed from the output later, and without it the
pair is a recording rather than a labelled fixture.

**Check `output.log` is non-empty after writing it** — `wc -c` is enough. Twice
during #265's Gate 1, `acceptance decompose … > output.log` exited 0 and left a
**zero-byte** file, and re-running the identical command after `rm -f` produced
the full 6.9 KB both times. It is not caused by the run making live calls; that
hypothesis was tested against a probe task file that forced one, and the probe
wrote its log fine. Cause unknown, so there is no defect to fix and no reliable
way to avoid it — but a silently empty log destroys the run's only durable record
while reporting success, and the loss is discovered long afterwards.

This does not conflict with the no-committed-transcripts rule. That rule is about
*transcripts*, which embed the full request as sent to the model; rendered reports
and task files are already committed under `tests/fixtures/rating-stability/`.

### Gate 1 — before writing any code

**1.** Write `current-task.md` for the issue (its Deliverable and Acceptance),
then decompose it:

```bash
.venv/bin/acceptance decompose --task current-task.md
```

**On a re-run, pass `--continue <run id>`.** Every run prints
`continue this run with: --continue <id>`; give the previous run's id when you
decompose again after reworking `current-task.md`. Without it **nothing is
carried forward** — that is #269's rule, *"No obligation is carried forward when
no continued run is named"* — so the obligation set is free to move for reasons
unrelated to your rewording. Measured at #251's Gate 1: rewording one Scope
exclusion bullet inverted whether four *untouched* requirement pairs merged,
and the same task file run with `--continue` reproduced the previous run's
merges exactly, on one model call instead of five
(`dogfood-logs/251-gate1-run{2,3,4}/`). A gate's second and third runs are
exactly where stability matters, because they only exist because the first run
found something.

**2. Read the obligation breakdown and confirm it is accurate** — no invented
obligations, none of the real ones missing. An inaccurate decomposition
invalidates every downstream stage, so do not proceed past a breakdown you would
not defend.

**3. Triage every open question it raises.** Each falls into exactly one of three
cases:

| Case | Action |
|------|--------|
| **Fair question** — `current-task.md` was genuinely inadequate or ambiguous | **Fix `current-task.md`.** This is the sanctioned rewrite of weak wording (see invariants). |
| **Implementation detail** deliberately left to the coding agent | **No action.** It is a correct observation about a decision that is yours to make; silencing it would be dishonest. |
| **Wrong question** — answerable from the task file plus the repo | **Stop and tell the human. Do not proceed.** State why it is answerable, and whether you believe the cause is already accounted for in the backlog (e.g. a known decomposition or mapping defect). Never fix it silently, never work around it. |

**Tie-break on rewriting:** rewrite when the tool's response makes you regret
your wording; otherwise leave it. This is independent of whether to escalate — a
question can be both worth rewording and worth reporting. Report it either way;
the rewrite is not the report.

**4. Record in `session-state/<issue>.md`** that Gate 1 passed, at which SHA, and who
confirmed the decomposition. That confirmation is a human judgement — unwritten,
the next session either repeats it or assumes it.

### Gate 2 — after coding, before opening a PR

```bash
.venv/bin/acceptance check --task current-task.md --base <rev> [--head <rev>]
```

`check` takes `--continue <run id>` as well, and the same rule applies: on a
second or later round, name the previous round's run so decomposition is carried
rather than re-derived. Note this is **not** the same mechanism as the prior
*review* `rerun.py::find_prior_review` selects over git ancestry — that one
carries judgements and needs no flag; `--continue` carries the obligation set.

**Move forward only on a completely clean check.** Clean means all of:

- every obligation **addressed**;
- every obligation **strongly supported by test evidence** — supported is not
  enough;
- every open question **resolved**;
- **no** recommended tests;
- no other flag, caveat, or indication that something needs attention.

Anything short of that is a stop. It is not a judgement call and not a threshold
to negotiate down. Record the result in `session-state/<issue>.md` — clean or not, and at
which SHA.

#### Suspended while the defect-first evidence work is in flight

**From 2026-08-21, until #312's sub-issues have landed — #313, #314, #315 and
#316 — the "clean or stop" rule above does not apply.** Gate 2's machinery is
the very thing that work is replacing: the mapping question is unanswerable as
posed, a mapping miss is unrecoverable downstream, and the strength denominator
is self-serving (`docs/DR-312-defect-first-evidence.md`, Context). Iterating a
task to a clean check against an instrument we already know to be broken spends
real effort on a reading that is about to change. For tasks in this stretch:

- **Run `check` once.** Do not re-run it to chase a clean result. This also
  suspends, for Gate 2 only, the re-arm rule below — a correction made in
  response to a finding does not oblige another run.
- **Fix what the run genuinely identifies** — a real defect in the work under
  review, or genuinely weak wording in `current-task.md`.
- **File what is genuinely new**, as a drafted queue item reviewed at the gate
  (*Working agreement* §4).
- **A finding that is only evidence of an already-known defect needs nothing.**
  Do not re-file it, do not re-record it against its issue, do not work around
  it. Note it in a line and move on.
- **Then move forward.** A less-than-clean check is not a stop here.

What does not change: **Gate 1 is untouched** and still needs a decomposition
you would defend. The check is still *run*, and its result still recorded in
`session-state/<issue>.md` with the SHA, clean or not. A finding attributed to a
tool defect still may not be silently dropped — this stops the *iterating*, not
the *looking*. Anything flagged as needing non-code evidence or human review is
still a pause.

**Delete this block when #316 lands.**

### Rules that apply at both gates

- **Read the test recommendations before forming an opinion.** When an obligation
  is less than strongly supported, the recommendations state exactly what evidence
  is missing. Read them *first* — do not pronounce on whether the finding is
  meaningful, correct, or worth acting on until you have.
- **Anything marked as requiring non-code evidence or human review is a pause.**
  Surface it and wait; that flag exists because the tool cannot settle the
  question alone.
- **Any correction made in response to a dogfood finding re-arms the gate.**
  Re-run the stage that raised it — `decompose` for Gate 1, `check` for Gate 2 —
  and get a clean result before moving on. A fix is finished when the re-run comes
  back clean, not when it was written.
- **Every negative finding has exactly two permitted dispositions:** (1) **address
  it** with a code or documentation change, or (2) **attribute it to a defect in
  the tool**, in which case **a drafted backlog item must be in the queue before
  you move forward** (*Working agreement* §4) and the finding is recorded against
  it. There is no third option. The draft is what makes it tracked work; it is
  filed when the queue is approved at the gate. An attribution with nothing
  queued is indistinguishable from suppressing the finding, and is treated as such.
- **A clean verdict is only as trustworthy as the mapping step behind it.** A
  review whose M4 mapping call returned mostly empty `obligation_ids` is
  half-blind, not clean. Check the mapping transcript before believing a clean
  Gate 2 — see `docs/DR-164-mapping-stage-request-partitioning.md`.

## Working in small sessions

Sessions are kept short and context reset often, deliberately: a long session
accumulates dead ends and superseded versions that compete for attention, and
compaction keeps the shape of that history while dropping the specifics. The cost
of resetting is paid in whatever was never written down, so: **externalise state
continuously, reset at the cheap moments.**

**Start of session — do this and nothing more:**

1. `session-state/` — list it, then read the entry for the task in flight. More
   than one file means more than one session is running; read only yours, and
   check the others for collisions rather than assuming there are none.
2. `current-task.md` — the task itself.
3. `git log --oneline -10` and `git status`.

Do **not** read `.acceptance/next-instruction.md` at startup. It is a single
fixed path overwritten by whichever `check` run last found gaps, keyed to no task
and no SHA, and never cleaned up — so it routinely describes a different task on
a different branch. #167 (M7.3.r1) replaces it with on-demand retrieval.

Then start work. Do **not** "get oriented" by reading the source tree; the
`src/acceptance/` map above exists so you don't have to.

**Reset at the gates.** Gate 1 passing and Gate 2 coming back clean are the
natural reset points: all the state is external and re-derivable, so resetting
costs almost nothing. Mid-implementation is where real work is lost. It follows
that a task should fit one session, gate to gate — if it can't reach Gate 2
without a reset, split the issue rather than run a longer session.

**Keep your `session-state/<issue>.md` current.** Rolling, fixed headings, rewritten wholesale
rather than appended to. Update it before you stop and any time losing the last
hour would hurt — not as an end-of-session ceremony, which is expensive enough to
get skipped. Keep it short; cheap to rewrite means it actually gets rewritten.

**Push exploration into subagents.** Searching the repo — "where is X handled",
"which tests cover Y" — produces far more output than answer. Delegate it and
keep the conclusion, not the transcript. This is the biggest lever on in-session
context.

## Sequencing

**Where the work currently stands is deliberately not recorded here** — a status
line goes stale within days and then misdirects. Live state is `session-state/`
and `current-task.md`.

What is durable is the load-bearing order: the review-state store, evidence-tier
primitives and LLM harness (M0) and the benchmark harness (M-B0) come before
capabilities, so nothing ships unmeasured. The execution tier (M8) comes after the
static pipeline (M7) — it only confirms what static analysis already maps.

**Decomposition quality comes before evidence quality.** Obligations must be
accurate, stable, non-redundant and clean before work on judging evidence about
them is worth doing — every downstream stage is judging the obligation set, so a
wrong or unstable set invalidates mapping, discrimination and the verdict alike,
and any measurement taken over it is measuring the wrong thing. In practice that
puts the `#181` decomposition defects ahead of the `#183` evidence-judgement and
`#185` presentation ones. Within reason: a defect that makes the tool actively
*misleading* — one that turns a gate green rather than red — can jump the queue,
because everything after it is judged against a broken gate.

## Commands

```bash
.venv/bin/pip install -e ".[dev]"   # first-time setup; needs the sandbox off (TLS)
.venv/bin/pytest -q                 # full suite. Replay mode, no API key needed
.venv/bin/ruff check .              # lint as CI runs it. Only valid if .venv/bin/ruff --version prints 0.16.2
.venv/bin/acceptance check --task current-task.md --base <rev> [--head <rev>] --mode record
```

Other subcommands: `decompose`, `diff`, `classify`, `recommendation`.

`check` defaults to replay, so a task file it has never seen aborts on the first
stage; `--mode record` is required at Gate 2. The error names the prompt tests,
which is the wrong fix. `decompose` already defaults to record.

**GitHub goes through the `mcp__github__*` tools, not `gh`.** They run
in-process, so they avoid the sandbox, the keyring and TLS verification, and
they have no local git side-effects. `gh` is kept for one job only: a background
CI watch through `Monitor`, which needs `dangerouslyDisableSandbox`. Say so when
you use it rather than escaping silently.

| want | use |
|---|---|
| read a task | `issue_read` (`method: "get"`) |
| comment on an issue | `add_issue_comment` |
| file an issue / attach a sub-issue | `issue_write`, `sub_issue_write` |
| read a PR, its diff, its comments | `pull_request_read` |
| is CI green? | `pull_request_read`, `method: "get_check_runs"` |
| open a PR | `create_pull_request` |
| merge | `merge_pull_request` (then delete the branch separately) |

The approval boundaries do not move: `issue_write`, `sub_issue_write` and
`add_issue_comment` file without a prompt, so *Working agreement* §4's
review-then-file rule is the only rail; `create_pull_request` and
`merge_pull_request` still stop for a human (§3). A comment body is a
parameter, not a file: no `-F <file>`, no heredoc.

**Sessions start sandboxed, and a sandboxed Bash call runs without a prompt.**
The rules below are what keep calls inside the sandbox; break one and the call
stops for a human. The reasons, the measurements and the recovery steps for
each are in `docs/agent-notes/environment.md`. Read that file when a command
fails with "Operation not permitted", prompts unexpectedly, or leaves git in a
strange state; do not read it at session start.

- Do not reach for `dangerouslyDisableSandbox` unless a command demonstrably
  failed because of a sandbox restriction.
- One command per call. No `&&` batching, no `echo "=== label ===" && cmd`.
  Independent calls issued in one message run in parallel anyway.
- No heredocs (`<<`) in Bash, including `python - <<'PY'`. Use the `Write` tool
  and run scripts by path. The one exception is `git commit -F -`.
- Do not `source .venv/bin/activate`; call `.venv/bin/<tool>` directly.
- Never name `.env` in a command; use `test -f .env && echo present`.
- Need another directory? `(cd <dir> && <cmd>)`. Never a bare `git -C <dir>`
  for a mutating subcommand, and never drive `pytest` by absolute path (it
  collects the archetype fixtures as tests).
- Creating branches: always `--no-track` (`git branch --no-track`,
  `git switch --no-track -c`, `git worktree add --no-track`). Without it the
  command tries to write `.git/config`, which the sandbox protects, and
  `git switch -C` fails half-way and leaves the index wrong. Do not try to allow
  writes to `.git/config`; the protection is deliberate.
- `git branch -m` prints `fatal:` and has still succeeded; check
  `git branch --show-current`.
- A branch operation that touches `.claude/settings.json` fails half-way
  inside the sandbox. Recover with `git checkout -- .`, then rerun with the
  sandbox off.
- Do not re-add `Read(.env)` deny rules to `.claude/settings.json`; they make
  `pytest` fail to collect anything.


# Working agreement

How much autonomy an agent has between the gates. The gates themselves are
defined in *Dogfooding — the review gates* above; this section does not add any.

## 1. Default posture: keep going

Work autonomously between the gates. Do not ask permission to read, edit, create
files, run tests, lint, create branches, or commit. Do not narrate intent or ask
"shall I proceed?" — proceed. The permission rules in `.claude/settings.json`
define what is allowed; if a rule allows it, it is approved.

Silence between the gates is the goal. The cost of a needless interruption is
higher than the cost of a wrong turn caught at the next gate. **An iteration is
one issue, Gate 1 to Gate 2** — that is the unit the queue in §4 batches over.

## 2. The gates are the dogfood gates

There is one set of gates in this repo: **Gate 1**, decomposing `current-task.md`
before any code, and **Gate 2**, a clean `acceptance check` before a PR. Their
procedure and their pass/fail rules live in *Dogfooding — the review gates*, and
are neither restated nor relaxed here. This section says only what to **present**
on arrival, because each gate is also the scheduled alert.

At **Gate 1**:

- the obligation breakdown, and your confirmation it is accurate — no invented
  obligations, none of the real ones missing;
- the triage of every open question, by the three cases in the gate's table;
- the plan: files and modules you will change, and any schema or interface other
  work will depend on, written out concretely;
- anything in the issue you think is wrong or underspecified;
- the bundled queue (§4).

At **Gate 2**:

- whether the check is clean by the gate's definition, stated plainly at the top
  — if it is not clean, lead with that rather than burying it;
- each Acceptance item from the issue and how it is demonstrated — name the test,
  not the intent;
- a diff summary, calling out anything touched outside the task's own area;
- decisions and assumptions the Gate 1 plan did not cover;
- the bundled queue (§4).

Present and stop. Do not push, merge, or open a PR. Between the gates, stop for
nothing except §3.

## 3. Always interrupt — regardless of gate

Interrupt immediately, via `AskUserQuestion` with concrete options (never an open
question), when any of these happen:

- An **invariant** above would have to change — local-only inputs, evidence-tier
  discipline, typed-and-linked findings, markdown-never-as-interchange, replay
  determinism — or the review-state schema would, after later work depends on it.
- The **spec** would have to change for the issue's Acceptance to be reachable.
- **Licensing, secrets, money, or dataset redistribution** is implicated.
- You have **failed the same way twice** and the third attempt would be a
  different approach rather than a fix. Say what you tried, what you observed,
  and what you would try next.
- **Benchmark ground-truth labels look wrong.** Never "fix" a label to make a
  metric move.
- An action is **irreversible or outward-facing**: pushing, merging, opening a
  PR, closing an issue, rewriting history.

The gates add two stops of their own and they stand unchanged: a Gate 1 open
question that is a **wrong question**, and any tool output marked as needing
**non-code evidence or human review**.

Do **not** interrupt for: style choices, library selection within the dependency
stance, test naming, refactors inside the task's own area, a decision to raise, a
defect to file, or anything reversible in one commit. Those go in the queue.

## 4. The bundled queue

Three kinds of thing used to stop the work one at a time. All three now go into
`docs/DEFERRED.md` and are reviewed **together at the next gate**:

1. **Defects found mid-flight**, outside the current task's scope — a bug, a
   smell, a missing test, a spec inconsistency, a dependency problem. Do not fix
   it and do not ask about it.
2. **Backlog filings** — an issue, a sub-issue, or a comment asserting a new
   finding. *Never write to the backlog without human review* holds in full; what
   changes is **when** that review happens. Draft the item — title, body, labels,
   parent umbrella — with the evidence that produced it, and queue it. Nothing
   reaches GitHub until it is approved at a gate.
3. **Open design decisions** you would otherwise raise. Surfacing them stays
   mandatory and resolving one quietly stays forbidden; queue it with your
   recommendation and the alternative you rejected.

```markdown
### [YYYY-MM-DD] <one-line title>
- **Kind:** defect | filing | decision
- **Found during:** #144, Gate 1
- **Where:** src/acceptance/requirement/obligations.py:118
- **Severity:** blocker | should-fix | nice-to-have
- **What's wrong:** one or two sentences, concrete.
- **Why I didn't act:** out of scope for #144 / would change the review-state schema.
- **Drafted fix:** for a defect, what you would do — specific enough to approve or
  reject without a follow-up, with the diff sketch if it is small. For a filing, the
  issue body as it would be filed, and its parent umbrella.
- **Status:** open
```

**A dogfood finding attributed to a tool defect is a filing**, and the
attribution rule in *Rules that apply at both gates* is satisfied by the queued
draft rather than by an already-filed issue — the finding is recorded before you
move forward, and filed at the gate. An attribution with nothing in the queue is
still indistinguishable from suppressing the finding, and is still treated as one.

Exception — fix it now, silently, and note it at the gate: the problem makes the
*current* issue's Acceptance unachievable, and the fix is inside the task's own
area.

At each gate, present the queue grouped by kind and severity with a recommended
disposition for each (fix now / fix next issue / won't fix / file as drafted /
needs my call). I approve in a batch; `/triage` then executes the approved ones,
filings included.

## 5. Evidence discipline applies to your own work too

This project's whole thesis is that a claim without discriminating evidence is
worthless. Hold your own reports to it:

- "The check passes" means you ran it and saw it pass — paste the output.
- Never report an issue complete on the strength of code that looks right.
- Before claiming a test demonstrates a behavior, ask whether it would fail if the
  behavior were absent. If it wouldn't, the test is not evidence. Say so.
- `Indeterminate` and "I could not verify this" are acceptable answers at a gate.
  A false green is not.

## 6. Write for someone who was not in the session

The rules are in *How to write to me* at the top of this file; they apply to
gate reports, queue entries and answers alike. Two of them are broken most
often in gate reports, so they bear repeating here.

**Bad news first, in the first sentence.** A gate that is not clean, a check
that failed, a claim you had to withdraw: those lead. Burying them under what
went well is the one habit that makes a report untrustworthy.

**Do not compress a process into a coined phrase.** "Queued as a blocker draft"
was four words standing in for "I wrote the issue text into `docs/DEFERRED.md`
and left it unfiled, because you approve backlog items before they reach
GitHub". The short version is unreadable to anyone who was not in the session,
which is everyone. If a sentence feels satisfying to write, treat that as a
warning sign.

This is not a request for more words. A short report I can act on beats a long
one I have to reverse-engineer.

---

Keep this file short. Add a line when an agent would otherwise rediscover
something expensive or get something wrong; delete a line when it stops being
true. Status belongs in `session-state/` and git history, not here.
