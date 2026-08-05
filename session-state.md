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
Branch `202-requirement-obligation-mapping`, off `4ec4470`. Implemented; three
commits; suite green at 750.

Design is `docs/DR-202-decomposition-requirement-mapping.md` (accepted, not
built). #202 is scoped to the **representational** change only — DR decisions
1–4 and 8. Siblings under #181, all deliberately out of scope: #204 (partition by
requirement batch), #205 (typing pass), #206 (open-question citations), #207
(resolver reads base revision), #208 (`decision`: decomposer code context), #144
(de-dup, sequenced immediately after).

**#193 is no longer the next task.** The model question it was blocked on is
answered: DR-202 concludes the fix is structural, not a model upgrade, and
rejects the upgrade explicitly (deficit is recall only). #193 is now the symptom
issue that #202 and its siblings address. Note the board has not caught up — #193
still holds Order 414 and **#202 is not on the project board at all**.

## Where #202 stands

**Implemented and committed (`a772982`). Full suite green. Gate 2 NOT yet run.**

Gate 1 run 1 did not pass, and the human authorised proceeding under attribution
(every loss traced to #202 itself, which predates the run), asking for a second
decompose after the change as a test of it. Both runs are in `dogfood-logs/`.

| | run 1 (flat list) | run 2 (mapping) |
|---|---|---|
| requirements identified | — | 44 |
| yielding an obligation | 30 of 42 | 35 of 44 |
| yielding nothing | **12, invisible** | **9, each with a reason** |
| `undisposed` | n/a | **0** |
| obligations serving >1 requirement | not representable | 10 |

**The deliverable works.** Run 1's losses were silence; run 2's are claims a
human can reject. The never-duplicate property (DR-202 decision 2), lost in both
its statements in run 1, is mapped in run 2.

**Run 3 added the requirement-major renderer and a prompt rule for unresolvable
references.** The second was the human's diagnosis and it was right: run 2's
declines said *"a scope note pointing to #204"*, which is what not knowing what
#204 is looks like. Coverage went 35 → **43 of 44**; all ten scope exclusions now
yield. The one decline is `completion-01: Implementation`, correctly.

This **refutes DR-202's positive-invariant hypothesis as the primary cause** —
that rule was already in force for run 2 and recovered only 2 of 10.

**Open defects:**

1. **#210** (filed, child of #181) — three exclusions linked to a neighbouring
   requirement's obligation instead of their own. Predictive signal is exact on
   this sample: the only three exclusions sharing an obligation with a Completion
   expectation are the only three mislinked. **DR-202 decision 2's reframe
   relocates over-merging rather than removing it** — read before building #144.
2. **#211** (filed, supersedes #195, child of #186) — rebuild that suite against
   the mapping and score **link precision separately from coverage**. Blocks #210:
   43-of-44 would otherwise score as ~0.98 accuracy.
3. **Unfiled** — the Task section's *problem statement* becomes an obligation to
   preserve the flat list, alongside the obligation to replace it. Stable across
   all three runs. #181 family.

**Withdrawn:** the `exclusion-04` "inversion" finding from runs 2 and 3 was my
error, not a tool defect — *"does not need to"* is a permission, not a
prohibition, and the obligation takes the same form as its correctly-handled
siblings. Both judgements corrected in place, both readings preserved. The lesson
is DR-180's in mirror: I reused a judgement across three runs instead of
re-deriving it, and its stability was not evidence for it.

**Next: Gate 2** (`acceptance check --task current-task.md --base 4ec4470`).
Expect #153 to cap the scope exclusions below `strongly supported`, as it did for
#190 and #195.

## Decisions already taken on #202

- **Requirement id stability is settled as an interim scheme**: `section +
  ordinal`, code-assigned in parse order, zero-padded — `constraint-01`,
  `exclusion-03`, `completion-07`, and `task` for the behavior paragraph. Full
  rationale in the #202 comment; the short form is that positional ids satisfy
  the acceptance criterion as written (within-version determinism) and their
  failure mode is inspectable, whereas a content hash would present a reworded
  bullet as *requirement vanished, new requirement appeared* — indistinguishable
  from the recall defect being fixed.
- **True cross-version requirement identity is semantic and is deferred to
  #209** (filed, child of #181). It is the `align_obligations` problem one level
  up. DR-202's §Open first bullet is to be updated to record this — that update
  is a Completion expectation of the current task file.

## What #195 left that #202 needs

- `benchmark/scoring.py::score_case` and `benchmark/case.py::GroundTruthLabels`
  are the scoring path; #195's decompose-stability suite is the **control** for
  #202 — it must run unchanged and no case may flip. A flip means something
  behavioral changed, and #202 is representational.
- Rebuilding that suite to bind labels to the mapping is a **superseding issue**,
  not part of #202 (DR-202 §Sequencing).
- `benchmark/corpus.py` materializes a case from a real commit as a detached
  worktree.
- **`corpus/*` tags are load-bearing** and CI must keep `fetch-depth: 0`.

## Known open, not #202's problem

- **#153** — scope exclusions demand test evidence that cannot exist; caps them
  at `partially supported`. Will hit #202's Gate 2, as it hit #190 and #195.
- **#191** — per-defect verdict instability; 20 → 3 `strongly supported` on a
  tests-only diff.
- **#196** — decomposer types automatable obligations `human_review`. #205 owns
  the fix.
- **#178** — questions raised that the task file answers. Did **not** recur in
  this run.
- **#129** — materialization flake in `materialize_archetype`, not a test flake.
  Cost #195 one red CI that passed on re-run of the identical commit. Unchecked:
  CI is 3.12, local is 3.10; `ignore_patterns` misses `.pytest_cache`.

## Findings worth not re-deriving

- **Mapping quality must be measured filtered to the current task's obligation
  ids.** #189's Gate 2 read 76% unfiltered and **97% filtered**; DR-164's
  half-blind failure was ~17%.
- **Audit mapping before believing OR disbelieving a Gate 2.**
- **A stable obligation count can conceal a re-split.** Compare aligned sets.
- **Two runs of silence is not evidence of resolution.**
- **Single-clause bullets do not rescue recall.** #202's task file was written
  after DR-202, deliberately avoiding compound clauses, and still lost 12 of 42.
  Second independent argument that the fix must be structural.

## The inference to avoid (DR-180)

> *The diff was purely additive; added tests cannot weaken evidence; therefore a
> rating that fell did so for reasons outside the diff.*

Both premises true, conclusion false. In 7 of 8 unstable obligations the corpus
found the LOW rating was correct. **Instability is not a licence to dismiss a
finding.**

## Outstanding, small (carried, not started)

- **`docs/DR-180` §Open is stale** — lists two settled questions. Own small PR.
- **A DR for the content-vs-shape distinction is arguably owed.**
- **#193's body describes five runs; the corpus is seven.**
- **The instability harness has never been run live.** DR-202 names its first
  live run: `decompose_case` over #195's cases with `RunConfig.model` varied.
- **Semantic open-question aligner** — #195 matches by id + observed aliases, so
  a decomposer inventing a new slug defeats it. Not filed.

## Traps

- **`acceptance decompose --mode record` writes nothing to stdout when
  redirected**, though replay does. Confirmed again on this run. Record once,
  then re-run in replay to capture. Still not filed.
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
