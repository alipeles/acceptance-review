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

**None.** #202 landed (`95a3856`, PR #215) and CI was green. `main` is clean.

`current-task.md` still holds #202's mandate — it refers back to a finished task,
which is expected.

## Next up

Board order is set. **#216 is first**, and the ordering deliberately puts
measurement ahead of the DR-202 siblings:

| order | issue | |
|---|---|---|
| 413.05 | **#216** | nested bullets dropped silently, guard reports zero |
| 413.10 | **#211** | rebuild #195's suite; link precision vs coverage |
| 413.15 | #210 | mapping over-merges onto adjacent requirements |
| 413.2–413.6 | #204, #205, #206, #144, #207 | the DR-202 siblings |
| 413.7–413.85 | #214, #213, #212, #209 | |

**Why this differs from DR-202's stated sequencing**, which put #144 immediately
after #202:

- **#144's premise was falsified.** DR-202 decision 2 reframed it on the claim
  that anchoring to identified requirements removes over-merging risk. #210
  showed the reframe *relocates* over-merging into requirement linking. #144
  needs a design revisit, not just a build. Commented on #144.
- **#144 changes the obligation set**, so without #211 it gets judged by eyeball —
  which is what `tests/fixtures/decompose-stability/` exists to prevent.
- **#204/#205/#206 all edit the decompose prompt.** Each edit forces a transcript
  re-record and makes accuracy non-comparable. Do them as one batch, not
  interleaved with #144.

**#214 probably wants a `decision` label and a short DR before building** — how
mandate coverage bounds the verdict is a design question. Instinct: it should
bound the verdict the way `Indeterminate` does rather than being averaged in.

## What #202 delivered

- requirement registry from the parse; ids `task-01` / `constraint-01` / … are
  **assigned by the code**. Interim — cross-version identity is #209.
- `Decomposition` and `Review` carry a many-to-many `RequirementMap`. Every
  requirement carries exactly one disposition, and the **code** marks
  `UNDISPOSED` anything the response failed to account for. That last part is
  load-bearing: without it a short disposition list is as well-formed as a
  complete one and the schema change buys nothing.
- `_user_prompt` passes typed identified fields, never `parsed.source`.
- the mapping renders requirement-major in the CLI and the §16 report.
- **a parse regression #202 itself introduced**: `parse_task_file` kept only the
  first `# Task` paragraph. Free while the model got `parsed.source`; silent data
  loss once the parse became authoritative. Fixed, plus `unread_source`.

**Accepted Gate 2 residue** (recorded on #202): one true-positive coverage gap —
`exclusion-01` claims *"the derivation is untouched"*, which is false — plus two
obligations attributed to #213. Note this was a **third disposition** CLAUDE.md
does not contemplate: accepting a true positive is neither "address it" nor
"attribute it to a tracked tool defect".

## Read this before trusting any Gate 2 number

**#214: `derive_verdict` never receives the requirement map**, so mandate
coverage cannot move the verdict. A decomposer that drops requirements therefore
scores *better* — dropped requirements cannot generate gaps.

Demonstrated live in #202's Gate 2 run 2: **every headline number improved while
mandate coverage fell 46/47 → 42/52**, because nine scope exclusions stopped
producing obligations and fewer obligations means fewer things that can lack
evidence. #190 and #195 both shipped on residues read under this blindness.

## Can the decomposer still drop a requirement? Yes — four ways

Asked and answered after #202 merged. What #202 closed is the *top-level silent*
drop only.

1. **#216 — nested bullets and second paragraphs inside a list item vanish**, and
   `unclaimed` is empty, so the guard prints `unaccounted for: 0`. Silence under
   a clean bill of health, which is worse than #202's original bug. Our task
   files happen not to nest bullets, which is why seven runs missed it.
2. **`no_obligation` with a plausible reason** — visible as a claim, but nothing
   is produced, and per #214 it does not touch the verdict.
3. **Compound clause inside one bullet** — one bullet is one requirement id; half
   a bullet can be lost with the disposition reading `yielded`.
4. **False link (#210)** — disposed `yielded` against an obligation that does not
   state it. Covered on paper, dropped in substance.

## Findings worth not re-deriving

- **A lossy parse is safe exactly until it is authoritative** (DR-202). Any stage
  that stops passing source and starts passing structure owes a report of what
  its structure does not cover.
- **Coverage is not quality.** #210's false links moved between runs while the
  count held flat.
- **Measure mapping from the persisted review, not `.acceptance/cache/`** — the
  cache pools every run ever made and read 45% where the review read 80%.
- **Mapping quality must be filtered to the current task's obligation ids.**
  #189's Gate 2 read 76% unfiltered, 97% filtered; DR-164's failure was ~17%.
- **A stable obligation count can conceal a re-split.** Compare aligned sets.
- **Single-run readings are unreliable — three were withdrawn in one session**
  (the `exclusion-04` "inversion"; "the reference rule fixed the declines"; "Gate
  2 run 2 is much better"). Each was internally coherent when written. This is
  the argument for #211 before any further decomposition work.

## The inference to avoid (DR-180)

> *The diff was purely additive; added tests cannot weaken evidence; therefore a
> rating that fell did so for reasons outside the diff.*

Both premises true, conclusion false. **Instability is not a licence to dismiss a
finding.**

## Known open, not the next task's problem

- **#153** — scope exclusions demanding evidence that cannot exist. Did **not**
  fire in #202's Gate 2 runs 2–3, because the exclusions produced no obligations
  to demand evidence for. The condition that suppressed it is worse than it.
- **#191**, **#196**, **#178**, **#193** — judgement and decomposition defects.
- **#129** — materialization flake in `materialize_archetype`, not a test flake.

## Outstanding, small (carried, not started)

- **`docs/DR-180` §Open is stale** — lists two settled questions. Own small PR.
- **The instability harness has never been run live.** DR-202 names its first
  live run: `decompose_case` over #195's cases with `RunConfig.model` varied.
- **Semantic open-question aligner** — #195 matches by id + observed aliases.

## Traps

- **`acceptance decompose|check --mode record` writes nothing to stdout when
  redirected**, though replay does. Record once, then re-run in replay to
  capture. Still not filed.
- **A `pgrep -f` pattern that matches your own waiter never exits.** Cost ~10 min.
- **`ModelClient` is a plain class, not pydantic.** Hook is `_completion_fn`.
- **Python here is 3.10** — no `enum.StrEnum`. Use `(str, Enum)`.
- **The repo is `alipeles/acceptance-review`**, not the local dir name.
- **`tee FILE | head -N` writes an empty file** — redirect first, then read.
- **`gh api ... -f` sends strings**; sub-issue ids need `-F` for integers.
- **Adding a sub-issue returns the PARENT**, so `-q .number` echoes the umbrella.
- **pytest may import a test module under a different name** — patch `globals()`.
- **Project `Order` IS readable** as the `order` key in `item-list --format json`;
  writing it needs `item-edit --field-id PVTF_lAHOAYe6HM4Bd8dTzhYaetU
  --project-id PVT_kwHOAYe6HM4Bd8dT --number <n>`.

## What to ignore

- **`.acceptance/cache/`** — transcripts and cached reviews, regenerable.
