# Judgement — #216 Gate 1 run 1

At `95a3856`. **Gate 1 did not pass**; the run was abandoned and #216 deferred.

`Requirements: 31   with obligations: 22   deliberately none: 1   UNACCOUNTED FOR: 8`

## The finding

Seven scope exclusions and `completion-10` came back `disposition: "yielded"`
with `obligation_ids: []`. The transcript shows **no invented ids** — `_resolve`
dropped nothing — and every one of the eight carried a substantive reason:

    exclusion-05  'This is a scope exclusion pointing to a separate issue (#144)
                   and does not add a checkable requirement for this change.'

The model wrote a textbook `no_obligation` reason under a `yielded` label.
`_requirement_map` required the label to match, fell to `else`, discarded the
reason and substituted `"disposition 'yielded' named no usable output"`.

## Triage

**Tool defect, two of them, both filed.**

1. Reconciliation discarding a supplied reason and recording the requirement as
   unaccounted-for — **#217 (M1.2.r2)**, fixed in this session.
2. The decomposer declining to yield obligations for scope exclusions at all,
   against the instruction already at `obligations.py:150`. Still open; belongs
   in the #204/#205/#206 prompt batch, where the re-record is paid once.

**Not attributable to task-file wording.** Three of the empty exclusions and
`completion-10` are word-for-word what #202's task file used, and in #202's
Gate 1 run 4 all four yielded obligations — same code, model and seed.

Zero open questions were raised, so Gate 1 step 3 had nothing to triage.
