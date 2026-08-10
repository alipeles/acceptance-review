# Judgement — #144 Gate 2, run 1

`check --base 9724df4 --head fc1bb99`. **NOT CLEAN. This is a stop.**

| | |
|---|---|
| verdict | INCOMPLETE |
| obligations | 18 (from 24 derived) |
| code evidence | 18 / 18 addressed |
| test evidence | 14 strongly supported, **4 unsupported** |
| open questions | 0 |
| recommended tests | 4 |
| unrequested changes | 15 |

## What worked — the feature demonstrably does its job on our own task file

Stage 1 produced **24** obligations, byte-for-byte the same set as Gate 1 run 3's
`decompose` over the identical task text. Stage 2 reduced it to **18**, with
**5 obligations named by more than one requirement**:

| survivor's requirements | what was merged |
|---|---|
| `constraint-06`, `completion-04` | the reason-clause rule and its acceptance criterion |
| `constraint-07`, `completion-05` | pre-link obligations persisted |
| `constraint-04`, `constraint-10`, `completion-06` | **three-way** |
| `constraint-09`, `completion-07` | byte-identical runs |
| `constraint-08`, `completion-08` | links stable unless derivation changes |

A 25% reduction on a real task file, and the two stages are separately readable
from the stored review — which is what `derived_obligation_map` was for.

**The three-way merge needs checking.** `constraint-04` is "the links are typed
fields"; `constraint-10` is "typed schemas are pydantic models". Those are not
obviously one requirement — one is about the link's representation, the other
about which library expresses schemas repo-wide. This may be the over-merge the
under-merging bias exists to prevent, on the first real task file the pass saw.

## Why it is not clean — 4 unsupported obligations, all from Task prose

| obligation | requirement |
|---|---|
| `duplication-per-requirement` | `task-01` |
| `later-stages-per-obligation` | `task-01` |
| `duplication-is-ordinary-restatement` | `task-02` |
| `duplication-not-input-fault` | `task-02` |

All four come from the two Task-section paragraphs that describe *the problem*,
and none from Constraints or Completion expectations. Read the recommendations
before judging them — they are the evidence:

> `duplication-per-requirement`: *"When the same requirement appears in two
> places in the task file, the derivation stage emits two obligations, one for
> each requirement occurrence."*

> `later-stages-per-obligation`: *"If derivation emits duplicate obligations,
> downstream stages process each obligation separately and the report grows
> accordingly."*

The first asks for a test of **#204's** behaviour, not this change's. The second
asks me to prove the tool is **inefficient** — to pin the very cost #144 exists
to remove. Both are obligations to preserve the status quo, derived from prose
that narrates the status quo.

## Disposition

**Attributed partly to my task-file wording, partly to a known tool defect.**

The Task section states current behaviour as fact — *"Obligation derivation reads
one requirement at a time… Every later stage runs once per obligation"* — and the
decomposer read a description of the problem as a requirement to keep it. That is
the sanctioned rewrite: describe the outcome wanted, not the mechanism being
replaced.

It is also **#212** (background becomes an obligation contradicting the mandate),
which is already filed and which this run reproduces cleanly — four instances,
all from the narrative section, none from a normative one. No new filing; a
comment on #212 with this evidence is queued.

Either correction re-arms the gate. Nothing proceeds to a PR on this run.

## Unrequested changes — 15, most of them the formatter

Seven (`#1`, `#3`, `#4`, `#5`, `#7`, `#8`, `#13`) are line-wrapping in files the
change touched, produced by the repo's own `format-changed.sh` PostToolUse hook,
not by me. They are correctly flagged and correctly `separable` / `in_service`.

Three are real and were called out before the run: the benchmark manifest
delegation (`#10`), the corpus-manifest extension (`#12`), and the new transcript
fixture (`#11`). Two are process files — `docs/DEFERRED.md` (`#14`) and
`session-state.md` (`#15`).

None is a surprise, and none is a defect. Recording them here so the next run's
list can be diffed against this one rather than re-triaged from scratch.
