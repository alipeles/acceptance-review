# Run 2 — judgement

*After the de-duplicating rewrite. 18 obligations (from 24), 3 open questions
(from 5).*

## Verdict at the time

**Still not a Gate 1 pass**, for one reason: an obligation came back typed
`human_review`, which is a mandatory pause under CLAUDE.md's rule that anything
requiring non-code evidence or human review is a stop.

## What improved, and whether it was earned

Both improvements are attributable to the task-file rewrite, not to sampling:

- **Duplicates collapsed, 24 → 18.** The pairs listed in run 1's judgement are
  gone. Correct, and caused by the edit.
- **Two fair questions resolved.** `fixed-input-unspecified` and
  `variance-path-interface-unspecified` disappeared after I said who supplies the
  input and named `benchmark/scoring.py::disclose_variance`. Both were directly
  addressed by the edit, so both are earned.

## The finding — `defaults-are-cheap-to-run` typed `human_review`

> `[human_review/explicit] defaults-are-cheap-to-run: The defaults together are
> cheap enough to run without first deciding a budget.`

**The tool is right, and this is a good catch.** "Cheap enough to run without
first deciding a budget" is not checkable by any static or test evidence — it is a
judgement about money, and the type system correctly routed it to a human.

**Disposition: rewrote the task file.** This is the sanctioned rewrite of a weak
obligation, not a way around the flag. The distinction matters and is worth
stating precisely, because the two look identical from the outside:

- Suppressing would be: deleting the requirement, or rewording it so the tool
  stops noticing while the requirement stays vague.
- What I did: replaced an untestable requirement with a testable one — *the
  default model set is a single model and the default run count is a small
  number*. The underlying intent (a default run must not cost real money) is
  preserved and is now checkable. The human judgement it was asking for had in
  any case already been given: the budget decision was made explicitly in
  conversation before Gate 1.

Anyone auditing this should check `task-diffs.txt` and confirm the requirement
survived the rewrite rather than being dropped.

## Remaining open questions — triage

| question | case | disposition |
|---|---|---|
| `oq-default-values` — what should the defaults be? | implementation detail | Answered by the run 2 → 3 edit as a side effect, since the edit states the defaults. |
| `oq-perturbation-definition` — what perturbations, and how specified? | implementation detail | **No action.** The task file now says the caller supplies the perturbation; the mechanism is mine to design. Note this is *narrower* than run 1's version of the same question, which also asked whether the set was fixed — that half was genuinely answered by the rewrite. |
| `oq-output-format` — what format, emitted where? | implementation detail | **No action.** Same question as run 1's, unchanged. |

## What I expected of run 3

That `oq-default-values` would resolve and the other two would persist, since
nothing in the edit touches them. **This expectation was wrong** — see run 3.

**Honesty note on this section:** the expectation is genuine but was *not*
written down before run 3 was executed; it is reconstructed from the reasoning
that produced the edit. A prediction recorded in advance would be worth more, and
future rounds of this corpus should write the expected outcome into the judgement
file *before* running. Treat this particular one as weaker evidence accordingly.
