# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed, so it survives a context reset or a machine change — but still a
scratch record, not a plan. **The GitHub issue stays authoritative** (#168).
Clear it out when the task lands rather than letting it accrete.

*Last updated: 2026-08-08*

---

## Next task — #144, and it starts immediately

**#144 (merge semantically duplicate obligations) is the next task and must not
wait.** Between #204 landing and #144 landing, the obligation set is unmerged:
#204's own Gate 2 derived **71 obligations from 34 requirements**. Every
downstream stage is per-obligation, so cost and report length stay roughly
doubled until #144 lands, and **no Gate 2 on this repo can come back clean in
the meantime** — the same gap gets counted several times.

Two constraints are already recorded as comments on #144; read them before
planning:

1. **Links are structured output, not prose.** A link written into an
   obligation's description cannot be validated, cannot be scored by #211, and
   cannot be told apart from the model narrating what it did.
2. **The pre-merge obligation set must be persisted**, even though no user sees
   it. Obligation determination is now two stages, and determinism is enforced
   at each: per-requirement obligations change only if that requirement's
   relevant inputs change; the de-duplication and its links stay identical
   unless the per-requirement obligations they were computed from change.
   Without stage 1's output stored, a movement in the final set cannot be
   attributed to the stage that caused it. Expect `rerun.py` to gain a second
   staleness question.

## Previous task — #204, merged (or in flight; check the PR)

Branch `204-partition-obligation-derivation`, **PR #229**. Gate 1 passed at
`40383bc` (human-confirmed); three Gate 2 runs in `dogfood-logs/204-gate2-run*/`.
Suite green at 860.

**Gate 2 was honest but not clean, and could not be** — see the next-task note
above. Closed on that basis, not by attribution.

### What #204 changed, in one place

- Derivation is partitioned by requirement batch through `partition.py`, at
  `DEFAULT_DECOMPOSE_BATCH_SIZE = 8`. **Every call still reads the whole task
  file**; the batch scopes only what a call must answer for.
- `--decompose-batch-size`, hashed via `Batch.request_partition()` — only
  `size`, never index or count.
- **Derivation performs no linking, as a SHAPE.** `_Yielded` carries
  `obligation` + `more_obligations` — the obligations themselves — instead of
  ids pointing into a flat list. DR-204's mechanism section is amended.
- `request_partition_sizes` is per stage; the stage label is recorded outside
  the hashed request so no mapping transcript is re-keyed.

## The lesson from #204 worth carrying

**A rule the schema invites cannot be enforced by asking harder.**

DR-204 first enforced no-linking with a post-response validator. It rejected the
response, dropped both claimants, left the mandate unaccounted for, and aborted
the review — deterministically, at temperature 0.

The model was not ignoring an instruction it understood. Obligations sat in a
flat list and dispositions pointed into it by unconstrained string, so writing
the same id twice was the *obvious* encoding for "these two requirements state
the same thing", while the prompt forbade it in prose.

**Measured, not assumed:** a control task file about invoice formatting — nothing
to do with decomposition — linked identically. So it was neither dogfood
contamination nor an edge case. When a prompt rule keeps losing, check whether
the response shape is offering the thing you are forbidding.

## Do not rediscover

- **The archetype corpus was unreadable until this branch.** All 13 task files
  yielded an EMPTY registry (`# Task: <title>` is not the `task` heading), so
  since #202 made the prompt registry-only the model saw a header and an empty
  list. **`decomposition_accuracy` figures from before this branch are
  meaningless.** Corpus fixed; the missing guard is **#228**.
- **An obligation can no longer be an orphan.** It arrives inside the
  disposition that owns it. The CLI still renders orphans because #144 rewrites
  the map, but derivation cannot produce one.
- **Test doubles use the flat shape and are translated** by
  `tests/support.py::_nest_obligations`, which REFUSES to express linking, so no
  fixture can smuggle back what the schema drops. It consumes obligations
  positionally — a fixture may legitimately mint the same id twice.
- **Verbatim response repetition is real**, new since responses grew: the model
  emitted its whole disposition list twice, byte for byte. Exact repeats are
  dropped; differing duplicates stay a rejection. If it recurs at larger sizes,
  batch size is the lever.
- **The task file must never mention dogfooding, gates, or our verification
  process** — now a CLAUDE.md rule. The issue says how we verify; the task file
  says what the software must do.
- **`request_key` hashes the response schema** (`llm.py`), so a shape change
  re-records everything. #204 paid this twice over.
- **`tests/` is a namespace package** — import shared helpers as
  `tests.requirement.region_coverage`, never relatively.
- **Python here is 3.10**; the repo is `alipeles/acceptance-review`.

## Traps

- **`decompose|check --mode record` writes nothing to stdout when redirected.**
  Record once, then re-run in replay to capture.
- **A commit subject starting with `#` is deleted during `rebase --continue`.**
  Put the issue ref at the end.
- **`gh api ... -f` sends strings**; sub-issue ids need `-F`, and the id is the
  REST `.id`, not the issue number. Adding a sub-issue returns the PARENT.
- **Do the work on a branch.** #204's commits started on `main` and had to be
  moved.
- **`cd` inside a Bash call persists to the next call.** Use absolute paths.

## Filed this session

- **#227** (`decision`, → #181) — accept the task file the user actually wrote;
  give feedback instead of silently reading nothing. Revisit after #208.
- **#228** (→ #186) — a benchmark case yielding zero requirements must fail, not
  score.
- **#225** (→ #183) — a rating falls as its evidence improves, and the
  recommendation names a test in the strength call's own mapped set.
- Comments: **#223** (absorption is task-file dependent, narrowing an earlier
  claim), **#173**, **#180**, **#212** (background became an obligation
  *contradicting* the mandate — the sharpest instance yet), **#144** ×2.

## Known open, not the next task's problem

**#210**, **#180**, **#193**, **#153**, **#191**, **#196**, **#178**, **#214**,
**#129**, **#223**, **#224**, **#173**, **#225**, **#227**, **#228**, **#212**.

## What to ignore

- **`.acceptance/cache/`** — transcripts and cached reviews, regenerable.
