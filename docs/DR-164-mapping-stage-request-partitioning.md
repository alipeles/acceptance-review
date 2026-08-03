# Decision Record 164 — Request partitioning for the mapping stage

*Relates to issue #164 (reframing merged in `08d0862`; implementation still
open) and issue #163. Status: measurement accepted, partitioning accepted,
implementation pending. Track: checker. Stage: 1, with one item explicitly
deferred.*

---

## Context — the reviewer's own failure is reported as the user's defect

The M4 mapping stage asks one model call to assign obligations to every
candidate test. On a review of this repo it returns a **well-formed entry per
test with an empty `obligation_ids` list**. The response is schema-valid, so
nothing downstream notices. `apply_test_mapping` then joins on an empty
mapping, every obligation renders `unsupported (no mapped test)`, and
`derive_verdict` reads those findings and returns INCOMPLETE.

The review therefore tells the reader **"your change has no tests"** when the
truth is **"the reviewer could not map them."**

Measured across four dogfood runs as the diff grew, empty entries out of ~95:

| run | empty `obligation_ids` |
|-----|------------------------|
| 1   | 29 |
| 2   | 51 |
| 3   | 50 |
| 4   | **80** |

At the worst point **zero of the run's 17 obligations were mapped**. This is the
most severe failure mode found in the tool so far, because its output is
indistinguishable from the true finding the tool exists to produce: a genuine
untested change and a total mapping failure render identically.

**Consequence: any dogfood verdict on a repo this size is currently
unreliable, in both directions.** The M7.5 (#36) iteration-3 run reported
NO-MATERIAL-GAPS and was cited as meaningful; its mapping call had ~50 of 95
entries empty. It was half-blind and should not be cited. M7.5 is complete and
verified on its branch but is not merged pending this work.

## Size is not the binding constraint

The obvious reading — "the prompt is too big" — is wrong, and acting on it would
have meant raising a limit that never binds. Measured on a full review of this
repo:

- Largest prompt: **26,283 input tokens** against a **1,050,000** context window
  — **2.5% utilisation**.
- No truncation observed, and no explicit context cap anywhere in `src/`.

What degrades is **judgments per call**. The mapping stage asks for
tests × obligations decisions — 1,632 in this run — and past roughly a thousand
it sheds work silently.

This is why §3.2's open decision was reframed from *"code-context retrieval
budget"* (a size question) to *"request partitioning (decisions per request)"*.

## A second, independent failure in the same call

Where the model *did* assign ids, they were `show-fields`, `line-total`,
`money-format`, `returns-in-parens` — obligations belonging to the
**archetype-1 fixture**, whose text appears inside
`tests/benchmark/test_coverage.py`, one of the candidate test files pasted into
the prompt. The model answered a question about the wrong document.

`evidence/mapping.py` filters ids that aren't in `valid_obligation_ids` with a
bare `continue`. That filter is correct — it must not admit foreign ids — but
because it is silent it converts a **visible** malfunction into an **invisible**
one.

## Decisions

**1. Partition the mapping request by obligation (#164).** Fewer decisions per
call, so the model stops shedding work.

**2. Do not generalise partitioning to the other stages.** Partitioning is cheap
only where the repeated context is small relative to the axis being split.
Measured prompt composition:

| stage | dominant content | partition cost |
|-------|-----------------|----------------|
| mapping | 96% candidate tests (the axis being split); obligations only 4% | cheap |
| coverage, unrequested-change detection, recommendations | ~96% **diff** (shared context) | ~3.8× tokens, on stages with no observed failure |

Splitting the **diff** instead breaks correctness outright: unrequested-change
detection needs the whole diff by definition, and coverage would emit a false
`not_addressed` for work done in a file outside the batch.

**3. Constrain id-bearing response fields to an enum of the ids actually
supplied, per call (#163).** A foreign id becomes *unrepresentable* rather than
detected after the fact.

Rejected on the way here, recorded so they are not re-derived:

- *"Report unmapped obligations as `indeterminate`"* — **wrong grain**. Whether
  obligation B got mapped says nothing about whether A was considered, so any
  run-level signal is a proxy for the thing we care about.
- *"Detect the response whose ids are all foreign"* — **band-aid**. It guards one
  flavour of gross error; a model that can fail that way can fail others.

**4. Do not attempt to distinguish "considered and found nothing" from "judged
wrongly."** If the model knew it had erred, it would not have erred. This is
closed; do not reopen it.

**5. Sequence #164 before #163.** Both touch the same prompt and schema, and
each forces a transcript re-record that makes benchmark accuracy figures
non-comparable across it. Sequencing them pays that cost once. They were kept as
separate issues rather than merged.

## Open

- **Should the silent id filter in `evidence/mapping.py` record what it
  dropped?** Decision 3 makes foreign ids unrepresentable at the schema level,
  which may make this moot — or may leave the tool blind to the next variant of
  the same failure. Undecided.
- **`source_quote` validation.** Same family as #163 — a claim about supplied
  input that we could check rather than trust — but a different check: the quote
  must appear in the task text. Noted as out of scope in #163, undecided.

## Related

- `docs/DR-081-unrequested-change-scoring.md` — the two-axis framing (obligation
  → code, code → obligation) that this stage sits on.
- Commit `08d0862` — the §3.2 reframe, which does not close #164.
