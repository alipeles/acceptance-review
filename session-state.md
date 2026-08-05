# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed, so it survives a context reset or a machine change — but still a
scratch record, not a plan. **The GitHub issue stays authoritative** (#168).
Clear it out when the task lands rather than letting it accrete.

*Last updated: 2026-08-05*

---

## Task in flight

**#195** — the decompose-stability corpus as a regression suite, #190's
counterpart and #193's scoreboard. Then #193, #191, #192. Branch: still `main`,
nothing coded.

**Gate 1 run 1 FAILED and is a hard stop, not a retry.** `current-task.md` written
from #195 and decomposed at `dbb342f`; run saved to `dogfood-logs/195-gate1-run1/`.
29 obligations, 3 open questions, nothing invented — the failure is entirely
absence:

- **Nine requirements produced no obligation.** Four Completion expectations,
  including all three degenerate-decomposer bullets that are #195's most
  load-bearing requirement; five of eight Scope exclusions. → #181/#193, #153.
- **All three open questions are the "wrong question" case** — each answered in
  the task file, two of them by a table written specifically to settle them.
  → #178, sixth audited recurrence. CLAUDE.md says stop and tell the human; done,
  awaiting direction.
- **Two prohibitions typed `human_review`** → #196, the run-7 corpus finding
  reproducing on the task file that encodes it as ground truth.
- **One compound bullet lost its second half** — *"No task text is copied into the
  case."* Mine to fix: split the bullet on the next iteration.

Full triage in that run's `judgement.md`. Do not re-run decompose expecting a
prettier breakdown — run 7 of the corpus warns against exactly that.

## What #190 left behind that the next task needs

- **`benchmark/corpus.py`** materializes a case from a real commit as a detached
  worktree. #195 can reuse it directly; the decompose corpus has the same shape.
- **`corpus/*` tags are load-bearing.** Every #190 head revision was
  squash-merged and is unreachable from `main`; the tags are the only thing
  keeping those objects alive. **CI must keep `fetch-depth: 0`.** If #195 pins
  revisions too, tag them at the same time — do not discover this from CI again.
- **Degenerate judges** (`tests/benchmark/degenerate_judges.py`) read allowed ids
  out of the request schema via #163's enum constraint rather than parsing prompt
  text. Reusable.

## Open against #190's residual — not defects in that change

- **#153** — scope exclusions demand test evidence that cannot exist. Writing
  tests moves them `unsupported` → `partially supported` and no further. This is
  why #190's Gate 2 never came back clean, and it will do the same to #195.
- **#191** — #190's Gate 2 round 3 fell 20 → 3 `strongly supported` on a diff
  that only added tests. Isolated to the per-defect verdict: mapping had *more*
  links (36→40), defect enumeration was identical (2.04/obligation),
  `would_be_caught` went 87% → 57%. Recorded there with the table.
- **#196** — decomposer typed automatable obligations `human_review`. Related to
  #193 but distinct: #193 is "unstable", #196 is "wrong".
- **#178** — the same open question recurred across five Gate 1 runs, and in
  Gate 2 went `[resolved]` → `[open]` with nothing relevant changed.

## Findings worth not re-deriving

- **Mapping quality must be measured filtered to the current task's obligation
  ids.** #189's Gate 2 read 76% unfiltered and **97% filtered**; DR-164's
  half-blind failure was ~17%.
- **Audit mapping before believing OR disbelieving a Gate 2.** #190's round 1
  looked like a tool failure and the audit (100% populated, zero foreign ids)
  proved the findings real.
- **A stable obligation count can conceal a re-split.** Compare aligned sets.
- **Two runs of silence is not evidence of resolution.**

## The inference to avoid (DR-180)

> *The diff was purely additive; added tests cannot weaken evidence; therefore a
> rating that fell did so for reasons outside the diff.*

Both premises true, conclusion false. In 7 of 8 unstable obligations the corpus
found the LOW rating was correct. **Instability is not a licence to dismiss a
finding** — check it on its merits first.

## Outstanding, small (carried, not started)

- **`docs/DR-180` §Open is stale** — lists two settled questions. Own small PR.
- **A DR for the content-vs-shape distinction is arguably owed.**
- **#193's body describes five runs; the corpus is seven.**
- **The instability harness has never been run live.**
- **`acceptance check --mode record` writes nothing to stdout when redirected**,
  though replay does. Worked around by recording once, then capturing in replay.
  Not filed — reproduce before believing it.

## Traps

- **`ModelClient` is a plain class, not pydantic.** Set defaults in `__init__`;
  the injected completion hook is `_completion_fn`, not `completion_fn`.
- **Python here is 3.10** — no `enum.StrEnum`. Use `(str, Enum)`.
- **The repo is `alipeles/acceptance-review`**, not the local dir name.
- **`tee FILE | head -N` writes an empty file** — redirect first, then read.
- **`gh api ... -f` sends strings**; sub-issue ids need `-F` for integers.
- **Adding a sub-issue returns the PARENT**, so `-q .number` echoes the umbrella.
- **Never assert a test file does not contain a string** — the assertion contains
  the string it searches for, so it can only be self-referential.
- **pytest may import a test module under a different name**, so
  `import tests.x.y as m; monkeypatch.setattr(m, ...)` can patch a *second*
  module object and silently do nothing. Patch `globals()` instead.
- **Project `Order` is a custom field**, not the `order` key in `item-list` JSON.

## What to ignore

- **`.acceptance/cache/`** — transcripts and cached reviews, regenerable.
