# #334 Gate 1, run 3 — judgement

Run `a7f05ec002634926`, continuing `a1c00b42b03c0fb7`. **Zero decompose calls,
$0.0000** — 6 requirements carried unchanged, none derived, none revised. The one
call was an embedding for obligation linking. Worktree
`334-sample-candidate-edits` at `0b751b4`.

**Accepted.** 12 obligations over 6 requirements. Verified two ways: the printed
breakdown and the decomposition ledger agree at 12, which runs 1 and 2 did not
(see below).

## What changed

The compiled-form requirement was removed from the task file, on the human's
decision, after the measurement in `docs/experiments/334-bytecode-equivalence/`
showed that comparing compiled forms catches none of the three cases #334 names,
and that the class it does catch — comment- and formatting-only edits — is
already refused without a model call by the verifier #335 merged that morning.

The run reported the removal explicitly:

```
REMOVED task-02: The review also gains one further check … (3 obligation(s) dropped)
```

That count is correct, and tracing why it was correct is what turned up the
display defect below. Only 2 of those 3 obligations had ever been printed.

## The obligation set

Ask for several candidates; use the first that passes the checks the review
already applies; make the count configurable; fall back to today's handling when
none passes. Record per defect how many were asked for, how many set aside and
why, and which was used; report what building edits cost and how long it took.
Two runs over the same input pick the same candidate. Three Scope exclusions,
one obligation each.

Every behaviour in the mandate appears exactly once. Nothing invented, nothing
missing, zero open questions.

## What "3 obligation(s) dropped" meant, and a false alarm I raised over it

The count is right and the breakdown is right. I initially read them as
contradicting each other and reported a defect that does not exist. Recorded
here because the same trap is one command away for the next person.

The two figures count different things:

| run | `derivations[].obligations` | printed | merges recorded |
|---|---|---|---|
| 1 | 25 | 24 | 1 |
| 2 | 15 | 14 | 1 |
| 3 | 12 | 12 | 0 |

`derivations[].obligations` in the ledger is what each requirement **derived**,
before linking. The breakdown renders what **survived**. A merged pair therefore
shows as two in the ledger and one on screen, and the gap is the merge count.

Verified for run 2 rather than assumed: its ledger holds one `merge_decisions`
entry with `same_requirement: true`, and recomputing that entry's two
fingerprints — sha256 over id, description and observable behaviour, per
`ledger.py::obligation_fingerprint` — matches `compiled-form-change-check` and
`compiled-before-after-compare-compiled-forms`. The near-duplicate was
recognised and merged. That is the decomposer doing the thing #277, "one
requirement yields two obligations stating the same property", says it fails to
do.

**The error, plainly.** I compared two counts, hypothesised that the renderer
suppressed one of a near-identical pair, and filed it as a blocker while
labelling the hypothesis unverified. A minute in `cli.py::_requirement_block`
would have ruled the renderer out — it iterates the requirement map's
dispositions, not the obligation set, so it cannot suppress anything. The human
withdrew a Gate 1 confirmation on the strength of it.

**What survives.** Run 1's `failed-candidate-set-aside` and `next-is-tried` still
did not merge, and run 1 records only that one merge decision, so #277's
underlying problem is real. The compiled-form pair is simply not an example of it.

## Method note

`.acceptance/ledger/<run>.json` is per-run local state and is not committed, so
the figures above are the record. To compare like with like, count
`derivations[].obligations` **minus** `merge_decisions` entries whose
`same_requirement` is true, against `grep -c '^    -> ' output.log`.
