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

**#202** — M1.2.r1, decomposition returns a requirement → obligation mapping.
Branch `202-requirement-obligation-mapping`, 12 commits off `4ec4470`. Suite
green at 761. **Both gates closed. Not yet pushed; no PR open.**

## Gate status

**Gate 1: passed under attribution.** Run 1 did not pass; every loss traced to
#202 itself, which predates the run. Runs 2–4 verified the fix.

**Gate 2: closed with an accepted residue** — 1 coverage gap, 2 recommendations.
Recorded on #202, and **note it is a third disposition** CLAUDE.md does not
contemplate: accepting a true positive is neither "address it" nor "attribute it
to a tracked tool defect". Human decision, recorded so it stays visible.

- **The gap:** `exclusion-01` claims *"the derivation is untouched"*, which is
  false — this change adds two sections to the decomposition prompt. **The tool
  is right.** Not fixed, because that would be a third consecutive edit to
  `current-task.md` made after seeing the checker's output.
- **The 2 recommendations:** #213 — the evidence is #195's green suite, which
  the tool cannot read. Deliberately not satisfied with duplicate tests.

## The thing to carry forward

**#214 changes how every Gate 2 number in this repo should be read.**
`derive_verdict` never receives the requirement map, so mandate coverage cannot
move the verdict. A decomposer that drops requirements therefore scores
*better* — dropped requirements cannot generate gaps. Gate 2 run 2 demonstrated
it live: every headline improved while mandate coverage fell 46/47 → 42/52.

#190 and #195 both shipped on Gate 2 residues read under this blindness. Not a
claim their conclusions were wrong — nobody has looked — but the instrument had
the flaw then too.

## Filed this session

| | |
|---|---|
| #209 | semantic requirement alignment across task-file versions |
| #210 | mapping over-merges onto lexically adjacent requirements |
| #211 | rebuild #195's suite; score link precision separately from coverage |
| #212 | task files cannot distinguish context from requirements |
| #213 | a green regression suite is unreadable as evidence for preservation |
| #214 | the verdict cannot see mandate coverage |

**#211 blocks #210.** #212's motivating example was corrected on the issue — it
turned out to be the parse bug, not context bleed.

## Three conclusions withdrawn today, all single-run readings

1. The `exclusion-04` "inversion" — *"does not need to"* is a permission, not a
   prohibition. My error, not a tool defect.
2. *"The reference rule fixed the scope-exclusion declines"* — held two runs,
   then fell to 1 of 10 on six added bullets.
3. *"Gate 2 run 2 is much better"* — it was worse; the numbers improved because
   the mandate shrank.

Each was internally coherent when written. That is a pattern about judgement
under this workflow, not three unrelated slips, and it is the strongest argument
for sequencing **#211 before any further decomposition work**.

## What #202 delivered

- requirement registry from the parse; ids `task-01` / `constraint-01` / … are
  assigned by the code. Interim — cross-version identity is #209.
- `Decomposition` and `Review` carry a many-to-many `RequirementMap`. Every
  requirement carries exactly one disposition, and the **code** marks
  `UNDISPOSED` anything the response failed to account for.
- `_user_prompt` passes typed identified fields, never `parsed.source`.
- the mapping renders requirement-major in the CLI and in the §16 report.
- **the parse regression this change introduced**: `parse_task_file` kept only
  the first `# Task` paragraph. Free while the model got `parsed.source`; silent
  data loss once the parse became authoritative. Fixed, plus `unread_source`.

## Findings worth not re-deriving

- **A lossy parse is safe exactly until it is authoritative** (DR-202). Any stage
  that stops passing source and starts passing structure owes a report of what
  its structure does not cover.
- **Coverage is not quality.** "43 of 44" says nothing about whether the links
  are right; #210's false links moved between runs while the count held flat.
- **Measure mapping from the persisted review, not `.acceptance/cache/`** — the
  cache pools every run this repo has ever made and read 45% where the review
  read 80%.
- **Mapping quality must be filtered to the current task's obligation ids.**
  #189's Gate 2 read 76% unfiltered and 97% filtered; DR-164's failure was ~17%.
- **A stable obligation count can conceal a re-split.** Compare aligned sets.

## The inference to avoid (DR-180)

> *The diff was purely additive; added tests cannot weaken evidence; therefore a
> rating that fell did so for reasons outside the diff.*

Both premises true, conclusion false. **Instability is not a licence to dismiss a
finding.**

## Known open, not #202's problem

- **#153** — scope exclusions demanding evidence that cannot exist. Did **not**
  fire in Gate 2 runs 2–3, because the exclusions produced no obligations to
  demand evidence for. The condition that suppressed it is worse than it.
- **#191** — per-defect verdict instability.
- **#196**, **#178**, **#193** — decomposition defects; #205 owns the typing fix.
- **#129** — materialization flake in `materialize_archetype`, not a test flake.

## Outstanding, small (carried, not started)

- **`docs/DR-180` §Open is stale** — lists two settled questions. Own small PR.
- **The instability harness has never been run live.** DR-202 names its first
  live run: `decompose_case` over #195's cases with `RunConfig.model` varied.
- **Semantic open-question aligner** — #195 matches by id + observed aliases.

## Traps

- **`acceptance decompose|check --mode record` writes nothing to stdout when
  redirected**, though replay does. Record once, then re-run in replay. Not filed.
- **A `pgrep -f` pattern that matches your own waiter never exits.** Cost ~10 min.
- **`ModelClient` is a plain class, not pydantic.** Hook is `_completion_fn`.
- **Python here is 3.10** — no `enum.StrEnum`. Use `(str, Enum)`.
- **The repo is `alipeles/acceptance-review`**, not the local dir name.
- **`tee FILE | head -N` writes an empty file** — redirect first, then read.
- **`gh api ... -f` sends strings**; sub-issue ids need `-F` for integers.
- **Adding a sub-issue returns the PARENT**, so `-q .number` echoes the umbrella.
- **pytest may import a test module under a different name** — patch `globals()`.

## What to ignore

- **`.acceptance/cache/`** — transcripts and cached reviews, regenerable.
