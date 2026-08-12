# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed to `main` at the gates, never to the branch under review (see
`CLAUDE.md` *Working conventions*) — but still a scratch record, not a plan.
**The GitHub issue stays authoritative** (#168). Clear it out when the task lands
rather than letting it accrete.

*Last updated: 2026-08-12*

---

## Task in flight: #191 — partition discrimination, split enumeration from verdict

**Gate 1 passed at `4e6c9af`, agent-confirmed, awaiting human confirmation.**
Log: `dogfood-logs/191-gate1-run1/`. 29 requirements → 28 obligations, 1:1, no
composites, no spurious links, **no open questions**, no unreconciled cluster —
the cleanest Gate 1 in the logs. One drift (`constraint-11`: "does not reduce"
derived as "preserves the number") and one type inconsistency, both queued.

**Zero open questions is not confirmed, only observed.** #193 says membership
oscillates; a second `--mode record` run would replay by construction and prove
nothing. Distinguishing needs #189's harness with determinism off. Recorded as
unresolved.

## Three sessions running in parallel

Checked for collisions, not assumed. `discrimination.py` and `strength.py` are
format-clean and lint-clean, so #191 does not collide with the reformat.

| session | issue | collision risk |
|---|---|---|
| this one | **#191** | `partition.py` is format-dirty — if #191 edits it, use the checkout+script workaround |
| — | **#258** | none; both its test files are already format-clean |
| — | **#261 + #239** | repo-wide; adds `ruff format --check` to CI, so later merges must be clean |

`session-state.md` is owned by this session. Agreed general fix if it recurs:
shard to `session-state/<issue>.md`, one per task in flight.

## Where #191 sits

Step **5 of 6** in the judgement-stability program: #189 harness (closed) → #190
rating-regression suite (closed) → #195 decompose-regression (closed) → #193
decompose instability (open, order 414) → **#191** → #192 (open, order 416).

Taken **before** #193 despite the board order, deliberately: #191's scoreboard is
the checked-in `tests/fixtures/rating-regression/` corpus, not live decompose
output, so decompose instability cannot contaminate its measurement. Human call.

## Baselines — one taken, one still owed

- **#190 regression suite: 34 passed** at `4e6c9af`, pre-change. This is the
  "real findings still found / unearned STRONGs not issued" direction.
- **#189 harness baseline NOT yet taken.** #191's Costs section requires it
  *before* starting, and implementing first invalidates the discrimination
  transcripts that would produce it. Recoverable only by checking out old code
  and re-recording. **Do this first when coding starts.**
  Harness: `src/acceptance/benchmark/instability.py`.

## The mechanism #191 fixes

`judge_discrimination` (`evidence/discrimination.py:133`) makes **one**
`client.complete` carrying every obligation's every defect verdict, and passes
neither a partition nor a `stage=` — so it is invisible to
`partition_sizes_in_force`. Two changes in one PR (do not split; the transcript
re-record is paid once):

- **(a)** partition by obligation via `partition(obligations, size, key=...)`,
  mirroring `mapping.py:126`.
- **(b)** separate enumeration from verdict, keyed differently. **The enumeration
  request carries no test evidence at all** — that is what makes "adding a test
  leaves the defect set unchanged" true *by construction*: same request bytes →
  cache hit → replay. Testable with no model call.

## Do not rediscover

- **A prompt change invalidates only THAT STAGE's transcripts** — `request_key`
  hashes each request individually.
- **52 of 117 files fail `ruff format --check`** and the `PostToolUse` hook
  reflows any file it touches — 457 changed lines for a 5-line edit. Filed as
  **#261**. **Workaround:** `git checkout <base> -- <path>`, then re-apply the
  real edit **by script**, never with the Edit tool.
- **The formatter strips an import you add before you add its usage.** Add the
  usage first; it silently reverted two edits, surfacing only as a later
  `NameError`.
- **`decompose --mode record` writes a 0-byte log through `tee`.** Rebuild with
  `--mode replay` into the log — byte-identical, no live call. Check `wc -l`.
- **Transcript responses are JSON *strings*** — `json.loads` the `response`
  field before reading `verdicts`.
- **Transcripts live in `.acceptance/cache/transcripts/`** (1,205 of them), not
  `cache/`. **The cache is not an archive** — DR-259 lost two runs mid-analysis.
- **`load_dotenv()` walks up from the calling *file*, not cwd.** A scratchpad
  script sees no project `.env`; pass the path explicitly.
- **`litellm.__version__` does not exist.**
- **`Review` requires `mode`** — `Review(mode="local", reviewed_revision=...)`.
- **A `check` or `decompose` over a new task file needs `--mode record`** and
  makes live calls.
- **`git branch -d` refuses every squash-merged branch.** `gh pr view <n> --json
  state`, then `-D`.
- **Python here is 3.10; CI runs 3.12**; repo is `alipeles/acceptance-review`.

## Carried forward from #259

- **DR-259's "0.10 is a clean separator" claim is withdrawn.** The held-out task
  file carries a genuine merge at **0.2257**; the nearest spurious sits at
  **0.116**, so the bands overlap and no threshold does both jobs. 0.10 ships as
  the deliberate under-merging side of a real trade. **#211** settles it properly.
- **Two consecutive issues merged on non-clean gates** (#248, #259). That is the
  reason this session is on judgement stability rather than more capability work.

## Queued — see `docs/DEFERRED.md`

**Three open.** Two new from this gate (the `constraint-11` quantifier drift as a
child of #181; the exclusion-typing inconsistency as a comment on #205), plus
untracking `current-task.md`, still **blocked on #258**.
