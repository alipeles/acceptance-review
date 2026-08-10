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
  `session-state.md`.

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
- **Changing a prompt, the model, or the seed invalidates recorded transcripts**
  — the request key hashes all three, deliberately: a determinism control changed,
  so recordings must be re-verified. It also makes benchmark accuracy figures
  non-comparable across the change, so sequence prompt work to pay that cost once.
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
- `session-state.md` — rolling state of the task in flight, carried across
  context resets. Committed, but still a scratch record: **the issue remains
  authoritative** (#168), and this file never becomes the plan.
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
  evidence that produced it*. This covers `gh issue create`, attaching a
  sub-issue, and any comment that asserts a new finding on an existing issue.
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

This does not conflict with the no-committed-transcripts rule. That rule is about
*transcripts*, which embed the full request as sent to the model; rendered reports
and task files are already committed under `tests/fixtures/rating-stability/`.

### Gate 1 — before writing any code

**1.** Write `current-task.md` for the issue (its Deliverable and Acceptance),
then decompose it:

```bash
.venv/bin/acceptance decompose --task current-task.md
```

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

**4. Record in `session-state.md`** that Gate 1 passed, at which SHA, and who
confirmed the decomposition. That confirmation is a human judgement — unwritten,
the next session either repeats it or assumes it.

### Gate 2 — after coding, before opening a PR

```bash
.venv/bin/acceptance check --task current-task.md --base <rev> [--head <rev>]
```

**Move forward only on a completely clean check.** Clean means all of:

- every obligation **addressed**;
- every obligation **strongly supported by test evidence** — supported is not
  enough;
- every open question **resolved**;
- **no** recommended tests;
- no other flag, caveat, or indication that something needs attention.

Anything short of that is a stop. It is not a judgement call and not a threshold
to negotiate down. Record the result in `session-state.md` — clean or not, and at
which SHA.

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

1. `session-state.md` — rolling state of the task in flight.
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

**Keep `session-state.md` current.** Rolling, fixed headings, rewritten wholesale
rather than appended to. Update it before you stop and any time losing the last
hour would hurt — not as an end-of-session ceremony, which is expensive enough to
get skipped. Keep it short; cheap to rewrite means it actually gets rewritten.

**Push exploration into subagents.** Searching the repo — "where is X handled",
"which tests cover Y" — produces far more output than answer. Delegate it and
keep the conclusion, not the transcript. This is the biggest lever on in-session
context.

## Sequencing

**Where the work currently stands is deliberately not recorded here** — a status
line goes stale within days and then misdirects. Live state is `session-state.md`
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
.venv/bin/pip install -e ".[dev]"   # first-time setup
.venv/bin/pytest -q                 # full suite — replay mode, no API key needed
.venv/bin/ruff check .              # lint, as CI runs it
.venv/bin/acceptance check --task current-task.md --base <rev> [--head <rev>]
gh issue view <n>                   # read a task
```

Other subcommands: `decompose`, `diff`, `classify`, `recommendation`.

**Habits that cost permission prompts and buy nothing.** Measured across 25
transcripts (3,324 unique Bash calls); together they outnumber every genuinely
missing allowlist rule. The allowlist is close to complete — **prompts are caused
by command *shape*, not by missing vocabulary.**

- **Don't `source .venv/bin/activate`** — 385 occurrences. The `.venv/bin/*` entry
  points above are allowlisted and `source` is not, so activating costs a prompt
  and then changes nothing.
- **Don't write files with `cat > f <<'EOF'`** — 107 occurrences. Use the `Write`
  tool; edits are already allowed. Heredocs also defeat segment matching, so the
  whole call prompts.
- **One command per call. Don't batch.** This is the big one: **63% of Bash calls
  would prompt**, and compound shapes account for 32 of the 34 recorded Bash
  denials. A compound command is only as permitted as its least-permitted
  segment, so batching `echo "=== label ===" && cmd` turns N allowed calls into
  one prompt. Round-trips are cheap; prompts are not. Independent calls issued in
  one message run in parallel anyway — that is the way to batch.
- **Need a different directory? Use a subshell: `(cd <dir> && <cmd>)`.** The
  matcher decomposes it and `cd` is auto-allowed, so `(cd <worktree> && .venv/bin/pytest -q)`
  matches the existing `.venv/bin/*` rules, and the `cd` cannot leak into the next
  call. `git -C <dir>` is fine for *read-only* subcommands (built-in git detection
  handles it); mutating ones need an explicit rule, because every plain `git *`
  rule assumes the subcommand comes first. `add` and `commit` have one —
  **patterns may wildcard mid-string**, as `Bash(git -C * add *)`, so any further
  gap of that shape is one line. Never write a bare `Bash(git -C *)`: it would
  swallow `push` and `merge`, which must keep prompting (*Working agreement* §3).
  Absolute tool paths miss too. `pytest` is worse than either: `addopts = "--ignore=tests/fixtures"`
  and `pythonpath = ["."]` are cwd-relative, so driving it by absolute path
  *silently collects the archetype fixtures as suite tests* and errors.
- **Never name `.env` in a command.** Secret-file protection overrides the
  allowlist, so `ls -la .env` prompts even though `Bash(ls *)` is allowed — and
  inside a batch it blocks every other segment with it. Use `test -f .env && echo
  present`.

---

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

---

Keep this file short. Add a line when an agent would otherwise rediscover
something expensive or get something wrong; delete a line when it stops being
true. Status belongs in `session-state.md` and git history, not here.
