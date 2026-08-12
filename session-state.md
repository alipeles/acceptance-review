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

## The finding that matters — 0.10 is lossy on held-out data

#259's own Gate 1 run is a fourth task file, held out from DR-259's calibration.
Same method, labels from the model's own verdicts: 12 confirmed merges over
1,035 pairs.

```
0.10  ask 2.1%   keep 11/12      <- the mandated default
0.23  ask 6.7%   keep 12/12
0.25  ask 8.1%   keep 12/12
```

The lost merge is at **0.2257** and is genuine — `task-01`'s headline obligation
merging with its own constraint restatement. DR-259 put the farthest genuine
merge at 0.0938, so **the separating band does not generalise**. Cause: those two
paraphrase each other across levels of abstraction (requirement vs mechanism),
a much wider gap than the near-verbatim restatements the calibration sample was
dominated by.

**Decision queued, not taken** — the issue's Acceptance mandates 0.10, so
implement 0.10 and let the human choose. Recommendation is 0.25.

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

Four open: the 0.10 decision, the DR TF-IDF correction, the #223 composite-
obligation filing, and untracking `current-task.md` (still blocked on #258).
