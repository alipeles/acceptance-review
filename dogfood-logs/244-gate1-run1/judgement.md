# Judgement — #244 Gate 1

**Gate 1 passed.** 22 requirements, 21 with obligations, 1 deliberately none. No
open questions, no unreconciled linking, and a repeat run over the unchanged file
was byte-identical.

## The breakdown is accurate

Nothing invented; nothing real missing. Every constraint, every scope exclusion
and every completion expectation yielded exactly one obligation. The single
"deliberately none" is the bare `Implementation` section marker — the correct
decline, and the case #214 requires not be penalised.

Two pairs were merged by the linking stage, both defensible:

- `constraint-02` + `constraint-06` — "a quotation is located within its
  requirement's span" and "a requirement keeps every obligation whose quotation
  lies within its span" are converses of one invariant.
- `completion-02` + `completion-06` — the two test demands over that same pair
  describe one test.

I wrote `constraint-06` as a deliberate guard against an over-aggressive fix that
rejects too much. The merge folds it into `constraint-02` rather than dropping
it, and `constraint-04` separately pins what happens to an unmatched quotation,
so the no-loss property is still represented. Worth re-checking at Gate 2 that
the implementation did not quietly trade recall for strictness.

## The contrast with #180's Gate 1 is the point

Same decomposer, same session, immediately after. On #180's task file, a
one-sentence Task requirement produced **seven** obligations — three paraphrases
of itself and three carrying other requirements' content. Here `task-01` produced
**one**, and no requirement's content appeared under another.

So #244's defect is real but not universal: this task file does not trigger it.
That is a useful boundary on the bug rather than a contradiction of it — and it
means this breakdown can be trusted as the basis for the fix even though the
stage being fixed produced it.

## Surfaced, per the gate's non-code-evidence rule

`exclusion-01` was typed **`human_review`**:

> How finely a single requirement is split into obligations, and how many
> obligations one requirement may yield, which is #117.

The gate requires surfacing anything marked as needing human review rather than
proceeding past it. My read is that this is a mistyping, not a genuine call for
human judgement: the requirement is an ordinary scope exclusion, indistinguishable
in kind from the five beside it, which were all typed `compatibility`. Obligation
typing is #205 and is explicitly excluded from this task's scope.

Two other types look off in the same way — `tests-no-live-model-calls` typed
`docs_config`, `byte-identical-review-state` typed `regression`. Same disposition:
#205's territory, noted not acted on.

Reported to the human at the gate rather than waved off.
