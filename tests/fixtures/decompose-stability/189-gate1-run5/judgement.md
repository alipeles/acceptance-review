# Run 5 — judgement

*After splitting the compound decomposition-variance bullet into two. 24
obligations, 2 open questions.*

## Verdict at the time

**Gate 1 passed.** Breakdown accurate, nothing invented, nothing missing, both
open questions triaged to no-action.

## Run 4's finding is fixed

Both halves of the split requirement are now extracted:

- `report-obligations-present-in-some-runs-only`
- `report-open-questions-present-in-some-runs-only`

Splitting the compound bullet was sufficient. The open-questions half is no longer
swallowed.

## The confirming observation — open-question membership oscillates

This is the entry that settles what runs 3 and 4 could not.

| question | run 1 | run 2 | run 3 | run 4 | run 5 |
|---|---|---|---|---|---|
| output format | **present** | **present** | absent | absent | **present** |
| perturbation shape/definition | **present** | **present** | absent | absent | **present** |

**The task file has never said anything about output format**, in any of the five
versions. The text that would answer the question is absent throughout, and the
question's presence oscillates anyway.

This settles the reading recorded in run 3 and hedged in run 4:

- Run 3's judgement called the disappearance *unexplained instability*.
- Run 4 scored prediction 3 as *inconclusive, leaning toward the questions having
  been genuinely resolved* — two consecutive zero-question runs being more
  consistent with resolution than with noise.
- **Run 4's lean was wrong.** Resolution is not a state a question can return
  from. A question that comes back was never resolved; it was dropped.

An open question is a first-class output — "uncertainty is first-class" is a
standing invariant. Dropping one is the tool silently converting *I don't know*
into *nothing to see*, which is the precise failure mode this product exists to
detect in others. It is worse than an unstable evidence rating, because a rating
at least renders something a reader can dispute.

**Two runs of silence is not evidence of resolution.** Generalising: a clean Gate
1 that is clean because questions vanished is not the same as one that is clean
because they were answered, and only the history distinguishes them.

## Open-question triage

| question | case | disposition |
|---|---|---|
| `perturbation-input-shape` — what form does the caller-supplied perturbation take, and how is it applied? | implementation detail | **No action.** The task file says the caller supplies it; the shape is mine to design. Correct observation about a decision that is mine. |
| `report-format` — what output format, written or returned where? | implementation detail | **No action**, and not silenced. Fifth observation of this exact question across the project's audited runs. |

Neither is answerable from the task file plus the repo, so neither is the
"wrong question — stop and tell the human" case.

## Secondary finding — obligation *type* is unstable too

`record-run-provenance` on byte-identical source text:

| run | type |
|---|---|
| 3 | `invariant` |
| 4 | `invariant` |
| 5 | `docs_config` |

Worth flagging because #162 Part 2 proposes that human escalation key on
`ObligationType`, with `DOCS_CONFIG` among the escalating types. If the type axis
is itself unstable, moving escalation onto it moves the instability rather than
removing it. **This is a live input to #162's design, not a curiosity** — recorded
against #181, and #162 should read it before Part 2 is built.

## Duplicates, still

`reuse-existing-obligation-alignment` and `compare-by-obligation-content` are the
two clauses of one constraint. #144 again, same intra-sentence shape as run 3's
pair. Left in place; the wording is defensible and flattening it would be shaping
the input to flatter the tool.
