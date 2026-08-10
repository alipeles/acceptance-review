# Judgement — #244 Gate 1, re-armed

The mandate changed during implementation (see below), which re-arms the gate.
This is the decompose over the revised `current-task.md`, run against the fix
itself — the CLI is an editable install, so the attribution check is live here.

29 requirements, 28 with obligations, 1 deliberately none. No open questions.

## Not clean: one requirement yielded the identical obligation twice

`constraint-10` produced `keep-within-span-obligations-with-their-requirement`
and `keep-within-span-obligations-with-their-requirement-2` with **byte-identical
descriptions** — the same sentence twice, told apart only by `_unique` appending
a suffix.

That pair joins a transitive link cluster with the near-identical obligations
from `task-01`, `constraint-02` and `constraint-03`; one pair inside the cluster
is denied; the run ends with five unreconciled obligations.

**#244's fix correctly does nothing here.** Both duplicates quote `constraint-10`
and are attributed to `constraint-10`, so attribution is right and the check
passes them through. This is a different defect — exact duplication within one
requirement — and #244's Scope exclusions assign "how many obligations one
requirement may yield" to #117.

Disposition: attributed to a tool defect, drafted as a filing against #181 and
queued in `docs/DEFERRED.md`. Distinguished from #117 in the draft: this is not a
granularity judgement but exact duplication, detectable without asking the model.

## The mandate changed, and that needs saying plainly

Two constraints in the Gate 1 mandate no longer described what was built:

> An obligation whose quotation matches no requirement's span is recorded as an
> answer that could not be used, **and no requirement is left claiming it.**

The implementation keeps it. Dropping an obligation because its quotation could
not be placed risks losing a requirement — the failure #202 and #214 exist to
prevent — and a decomposer that quotes badly is not evidence that the obligation
it derived is unreal.

A second, sharper reason surfaced only in code: `_requirement_map` raises when a
requirement disposed `yielded` carries no obligation. So moving or dropping a
requirement's *last* obligation converts a mild quoting slip into a failed
review. A completion expectation quoting the constraint it demands a test for is
the DR-204 shape and is common, so that slip is not rare.

The mandate was rewritten to match, and three constraints were added that the
original did not anticipate: line-break-insensitive matching, never emptying a
requirement, and a re-attributed obligation taking its new section's admissible
evidence.

**This is a design change disclosed as one, not a wording fix.** `CLAUDE.md`
sanctions rewriting weak wording and forbids editing the task file to change what
the review says. Rewriting a mandate to match what was built sits close enough to
the forbidden move that it should be reviewed as such rather than waved through.
