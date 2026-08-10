# Judgement — #248 Gate 1, run 1

Command: `.venv/bin/acceptance decompose --task current-task.md --mode record`
Run at `4619e78` (main, clean tree).

## Decomposition accuracy — confirmed

24 requirements identified, matching the task file exactly: 1 task line, 10
constraints, 6 scope exclusions, 7 completion expectations. 23 yielded an
obligation; `completion-01` ("Implementation") deliberately yielded none, with
the reason that a bare section marker imposes nothing checkable.

No invented obligations. No requirement of the file went missing. Each
constraint's obligation restates its constraint verbatim; each exclusion was
reframed as a preservation invariant ("the change does not alter …") and carries
code-only admissible evidence, which is #153's intended behaviour.

## Open questions — none raised

Nothing to triage under the Gate 1 three-case table.

## Negative findings

### 1. Unreconciled linking cluster (attributed to a tool defect — #242)

```
Unreconciled linking answers: answers contradict each other: these obligations
are linked transitively but at least one pair among them was denied, so none of
them were merged
  affected: dedupe-identical-obligations, exact-description-identity,
            record-duplicate-drop, dedupe-identical-obligations-2
```

Real, and this run is fresh evidence for **#242** rather than a new defect. The
cluster mixes one genuine near-duplicate pair with two obligations that state
plainly different things:

| obligation | from | states |
|---|---|---|
| `dedupe-identical-obligations-2` | `task-01` | a requirement does not yield the same obligation twice |
| `dedupe-identical-obligations` | `constraint-01` | identical descriptions → keep one |
| `exact-description-identity` | `constraint-03` | identity is exact, character for character |
| `record-duplicate-drop` | `constraint-04` | the drop is recorded, not silent |

The first pair is the ordinary headline-restated-as-constraint shape and is a
fair merge candidate. `exact-description-identity` and `record-duplicate-drop`
are not duplicates of anything in the cluster — they are the spurious links
#242 describes, and because one pair inside the cluster was denied, nothing
merged at all. Queued as a comment on #242.

Not a Gate 1 stop: the gate stops on an inaccurate breakdown or a wrong open
question, and this is neither.

### 2. `task-01` and `constraint-01` mint the same slug

`task-01`'s obligation carries the id `dedupe-identical-obligations-2`, the
suffix minted because `constraint-01` had already claimed the base slug. Two
different requirements independently producing the same slug is the case
`decompose` already anticipates in code, and the descriptions genuinely differ,
so this is **not** the exact-duplication defect #248 targets — #248 is scoped to
two identical descriptions under **one** requirement. Recorded here only so a
later reader does not mistake the `-2` for the defect under repair.

## Task-file wording

Left as written. The `task-01` / `constraint-01` overlap is the headline and its
precise statement, which is how every task file in this repo is shaped; the
merge failure over it is the linking stage's, not the wording's.

## Verdict

Gate 1 passed. Decomposition accurate, no open questions, one negative finding
attributed to an existing tracked defect with a comment queued.
