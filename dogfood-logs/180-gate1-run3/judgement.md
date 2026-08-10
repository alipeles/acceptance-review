# Judgement — #180 Gate 1, runs 1–3

**Gate 1 failed.** The breakdown in run 3 is one I would not defend, so the gate
rule applies: do not proceed past it.

## What the three runs are

| run | task file | scope | result |
|---|---|---|---|
| 1 | per-criterion discrimination requests | superseded — design changed | 21 obligations, 0 open questions, no flags |
| 2 | carry-forward + repeated-judgement explanation | current design | 24 obligations, 0 open questions, **4 unreconciled** |
| 3 | run 2's file minus seven words in the Task sentence | current design | 24 obligations, 0 open questions, **8 unreconciled** |

A fourth run over run 3's unchanged file produced output **byte-identical** to
run 3. Replay determinism is intact; this is a stable defect, not noise.

## The finding — the decomposer over-generates from the Task sentence

Run 3's `task-01` is a single sentence:

> A repeated review changes a criterion's test-evidence rating only when
> something that criterion depends on has changed.

It yielded **seven obligations**. Three are paraphrases of each other and of the
sentence itself:

- `repeated-review-only-on-dependency-change` — "changes a rating only when that
  criterion's dependencies have changed"
- `dependency-change-is-the-only-trigger` — "changes a rating only when something
  that criterion depends on has changed"
- `dependency-change-gates-rejudgment` — the same rule stated as its converse

Three more are the content of *other* requirements, re-derived under `task-01`:

- `named-change-must-be-from-input-changes` — this is `constraint-07`
- `stored-review-input-and-determinism` — this is `constraint-08`
- `tests-no-live-model-calls` — `constraint-09`, correctly cross-linked

The first two of those then collide with the obligations `constraint-07` and
`constraint-08` produced in their own right — the same requirement twice, under
two ids. The linking stage detects the contradiction and **correctly refuses to
merge**, which is why the run ends with eight unreconciled obligations rather
than silently merging on an inconsistent answer. The guard works; what it is
guarding against is upstream.

## Why the rewrite between runs 2 and 3 counts as evidence

Run 2 → run 3 deleted seven words — the clause "and says what that change was" —
from one sentence. That clause was genuinely redundant with `constraint-06`, so
the rewrite was the sanctioned one and I would make it again.

Its effect was disproportionate: `task-01` went from **2 obligations to 7**, and
the unreconciled set from **4 to 8**. Removing a redundant clause roughly doubled
the redundancy. That is decomposition sensitivity to wording well beyond what the
edit changed in meaning.

## Disposition

**Attributed to a tool defect**, drafted as a filing against **#181**
(decomposition umbrella) and queued in `docs/DEFERRED.md`. Not addressed by
further rewriting: one rewrite already made it worse, and a second attempt would
be tuning the input until the tool agrees rather than fixing the tool.

## Why this matters to #180 specifically

Redundant obligations are rated independently. Three obligations that say the
same thing can receive three different test-evidence ratings, and the report
shows the same requirement as strongly supported and partially supported at once.
**That presents as rating instability even when the judge is perfectly
consistent.** So an unknown share of the instability #180 was opened to fix may
originate upstream of the judge, in decomposition redundancy.

This is the concrete case for `CLAUDE.md`'s sequencing rule — decomposition
quality (#181) before evidence judgement (#183) — appearing inside #180's own
Gate 1.
