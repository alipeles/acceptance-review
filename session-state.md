# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed to `main` at the gates, never to the branch under review (see
`CLAUDE.md` *Working conventions*) — but still a scratch record, not a plan.
**The GitHub issue stays authoritative** (#168). Clear it out when the task lands
rather than letting it accrete.

*Last updated: 2026-08-11*

---

## In flight: #259 — prefilter obligation pairs by cosine distance

Child of #181. `docs/DR-259-obligation-pair-prefilter.md` is the decided design.
Human authorised: **add an embedding path, Voyage dependency is fine, raw cosine
distance.** `VOYAGE_API_KEY` is in `.env` and verified working through LiteLLM
(`voyage/voyage-3.5-lite`, 1024-dim).

**TF-IDF is out of scope entirely.** Per the human it entered only as an analogy
for hub-effect correction and testing showed it made things worse; DR-259's
second "stdlib TF-IDF cosine — viable, not chosen" block should not have been
written. Queued as a doc correction. Do not resurrect it.

## Gate 1: PASSED at `0e1eae2`, confirmed by Claude with the human

`dogfood-logs/259-gate1-run1/`. 33 requirements, 32 with obligations, 1
deliberately none. **Zero open questions**, no unreconciled clusters. Every
requirement represented; nothing missing. No rewrite of `current-task.md` — the
wording is not the cause of the one defect seen.

## Threshold: 0.10 CONFIRMED — but for a different reason than DR-259 first gave

#259's Gate 1 run is a fifth task file, held out from DR-259's calibration. Same
method, labels from the model's own verdicts: 12 confirmed merges over 1,035
pairs. It carries a **genuine** merge at **0.2257** — `task-01`'s headline
obligation merging with its own constraint restatement — far outside the
0.094–0.115 band the DR calls a clean separator.

Raising the default to clear it was considered and **rejected**:

```
              calibration          held-out
threshold   genuine  spurious      genuine    asked
  0.10       20/20    0/10          11/12      2.1%   <- chosen
  0.15       20/20    2/10          11/12      3.4%
  0.25       20/20    9/10          12/12      8.1%
```

The nearest calibration *spurious* merge is at 0.116, below the held-out genuine
one at 0.2257. **They overlap — no threshold does both.** At 0.25 the filter
admits 9 of 10 spurious merges and stops being a quality filter at all.

So 0.10 stands, now as the deliberate **under-merge** side of a real trade rather
than a free separation: a missed merge leaves a visible redundant obligation, a
spurious merge destroys a requirement silently. Matches `linking.py`'s declared
bias. **Do not re-assert that the threshold separates cleanly — it does not.**
#211 is now load-bearing for settling the number properly.

Recorded in DR-259 (*Held-out check*). `current-task.md` and #259's Acceptance
already said 0.10, so nothing re-armed and no mandate changed.

## Do not rediscover

- **A prompt change invalidates only THAT STAGE's transcripts**, not the whole
  cache — `request_key` hashes each request individually.
- **`decompose --mode record` still wrote a 0-byte log through `tee`.** The trap
  is not fixed by `tee` alone. Rebuild by re-running `--mode replay` into the
  log; output is byte-identical and needs no live call. Check `wc -l`.
- **Transcript responses are JSON *strings*, not dicts** — `json.loads` the
  `response` field before reading `verdicts`. Cost one wrong analysis pass.
- **Transcripts live in `.acceptance/cache/transcripts/`**, not `cache/` directly.
- **`load_dotenv()` walks up from the calling *file*, not cwd.** A script in the
  scratchpad sees no project `.env`; pass the path explicitly.
- **`litellm.__version__` does not exist** — raises AttributeError.
- **`git branch -d` refuses every squash-merged branch.** Confirm via
  `gh pr view <n> --json state` then `-D`.
- **`git stash` mid-task reverts the working tree wholesale.** Use a second
  worktree or `git show` to inspect a baseline instead.
- **Compound constraints get over-split.** Write one statement per bullet in
  `current-task.md`.
- **A `PostToolUse` formatter hook reformats files after every edit.**
- **Obligation ids are minted per response, not stable across runs** (#231).
- **Python here is 3.10; CI runs 3.12**; repo is `alipeles/acceptance-review`.

## Queued — see `docs/DEFERRED.md`

Two open: the #223 composite-obligation filing (drafted, **not yet approved**),
and untracking `current-task.md` (still blocked on #258).

The 0.10 decision and the DR TF-IDF correction are resolved and their entries
deleted — both landed in DR-259.
