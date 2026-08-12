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

## No task in flight

**#259 landed** — `c3ebc42` (PR #260), CI green. Obligation pairs are prefiltered
by cosine distance before the linking call, with an embedding path recorded and
replayed through the same transcript store as every other model call.

`current-task.md` still holds #259's mandate, which has shipped. Ignore it; the
next task writes its own at Gate 1.

## What #259 settled about the threshold

Carry this forward — the number is right but the *reasoning* in the original DR
was not, and re-deriving it from the DR alone would resurrect the wrong claim.

DR-259 justified 0.10 as a clean separator. **It is not.** #259's own Gate 1 run
was a fifth task file, held out from the calibration, and carries a **genuine**
merge at **0.2257** — far outside the 0.094–0.115 band. The nearest calibration
*spurious* merge sits at **0.116**, below it, so the two overlap:

```
              calibration          held-out
threshold   genuine  spurious      genuine    asked
  0.10       20/20    0/10          11/12      2.1%   <- chosen
  0.15       20/20    2/10          11/12      3.4%
  0.25       20/20    9/10          12/12      8.1%
```

At 0.25 the filter admits 9 of 10 spurious merges and stops being a quality
filter at all. **No threshold does both.** 0.10 ships as the deliberate
under-merging side of a real trade, matching `linking.py`'s declared bias.
Recorded in DR-259's *Held-out check*; the clean-separation claim is withdrawn.
**#211 is now load-bearing** for settling the number properly.

## Gate 2 was NOT clean, and #259 merged anyway — deliberately

29 of 30 obligations strongly supported. The single blocker was `completion-10`
reported as having no mapped test while **the same report cited that exact test
twice elsewhere** — on its Constraint twin and on an unrelated obligation. That
is #245; no code change answers it. Merged on the strength of **seven defect
injections**, with the human's explicit call.

**This is the second consecutive issue merged on a non-clean gate** (#248 was the
first). `CLAUDE.md`'s sequencing rule says a gate that moves under unchanged
evidence cannot validate anything downstream — so #225/#180 deserve weighing
against more capability work before the next task.

## The #225 evidence is now two-directional

Newly filed on #225, and it changes what the defect *is*:

- run 1 → 2: an obligation fell strongly → partially on **byte-identical**
  evidence; non-discriminating went 3 → 13 while only *adding* tests.
- run 2 → 3: **two** boundary tests moved **twelve** obligations *up* to
  strongly supported, most untouched by them.

Every prior instance showed ratings falling, readable as a conservative judge.
Twelve unearned promotions rules that out — it is instability, not bias, so
"write more tests until the gate is clean" is not a convergent strategy.

## Do not rediscover

- **A prompt change invalidates only THAT STAGE's transcripts** — `request_key`
  hashes each request individually.
- **52 of 116 files fail `ruff format --check`** and the `PostToolUse` hook
  reflows any file it touches — 457 changed lines for a 5-line edit on
  `tests/test_cli.py`. Filed as **#261**. **Workaround:** `git checkout <base> --
  <path>`, then re-apply the real edit **by script**, never with the Edit tool.
- **The formatter strips an import you add before you add its usage.** Add the
  usage first; it silently reverted two edits, surfacing only as a later
  `NameError`.
- **`decompose --mode record` writes a 0-byte log through `tee`.** Rebuild with
  `--mode replay` into the log — byte-identical, no live call. Check `wc -l`.
- **Transcript responses are JSON *strings*** — `json.loads` the `response`
  field before reading `verdicts`. Cost one wrong analysis pass.
- **Transcripts live in `.acceptance/cache/transcripts/`**, not `cache/`.
- **`load_dotenv()` walks up from the calling *file*, not cwd.** A scratchpad
  script sees no project `.env`; pass the path explicitly.
- **`litellm.__version__` does not exist.**
- **`Review` requires `mode`** — `Review(mode="local", reviewed_revision=...)`.
- **A `check` over a new task file needs `--mode record`** and makes live calls.
- **`git branch -d` refuses every squash-merged branch.** `gh pr view <n> --json
  state`, then `-D`.
- **Python here is 3.10; CI runs 3.12**; repo is `alipeles/acceptance-review`.

## Queued — see `docs/DEFERRED.md`

**One open**, unchanged: untracking `current-task.md`, still **blocked on #258**
(two tests read the live file). Do #258 first, then untrack.

Four filed this session: #245 comment, #225 comment, **#261** (formatter churn,
new), #223 comment.
