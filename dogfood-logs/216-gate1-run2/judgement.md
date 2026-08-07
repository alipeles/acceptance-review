# Judgement — #216 Gate 1 run 2

At `efa2cab`, post-#217 and post-#218. **Gate 1 did not pass.**

`Requirements: 29   with obligations: 28   deliberately none: 1` — and no
unaccounted-for line at all.

## What run 1's finding did

Run 1 (at `95a3856`) failed with `UNACCOUNTED FOR: 8`: seven scope exclusions
and `completion-10` came back `yielded` with an empty `obligation_ids`, and
reconciliation discarded their reasons. #217 fixed the reconciliation half.

**That half is fixed and the count is now zero.** But the other half — #219, the
decomposer declining scope exclusions — did not fire either. Every exclusion
yielded an obligation this run. It yielded the *wrong* one, which is #210, not
#219. The two failure modes traded places between runs on the same corpus.

## Findings

All three verified against the recorded response
(`.acceptance/cache/transcripts/9c83cd8d…json`), not just the rendering. The CLI
output is faithful; the model produced these mappings itself.

### 1. Two cross-cutting constraints absorbed, their own obligations missing

```
constraint-11  Typed schemas are pydantic models  -> obligation-region-level-total-coverage-tests
constraint-12  Tests issue no live model calls    -> obligation-region-level-total-coverage-tests
```

That obligation reads *"A test asserts region-level total coverage over the
repository's committed task files and over the decompose-stability corpus."* It
states nothing about pydantic and nothing about live model calls. **No
obligation in the set of 13 does.** Both requirements' content is gone, and
`with obligations: 28` reports them as read.

This is worse than #210's shape. There, a mislinked exclusion at least landed on
an obligation about the same subject, and the exclusion's loss removed only a
negative statement. Here the requirement's content exists nowhere in the
obligation set, while the counter certifies it as accounted for. It is the same
failure #216 is about — content lost under a clean bill of health — one layer up
from the parse.

**Not attributable to task-file wording.** Both bullets are word-for-word from
#218's task file. In #218's Gate 1 they each yielded their own obligation; the
session-state record quotes `12. Represent typed schemas as pydantic models` as
a standalone obligation of that run. Same code, model and seed; different
surrounding task file.

*Caveat on my own authoring, separate from the defect:* `constraint-11` may be
inapplicable boilerplate here — #216 concerns spans and parse coverage, and may
introduce no new typed schema at all. That is a reason to reconsider the bullet,
not a reason the tool may absorb it. A vacuous constraint should surface as an
obligation nothing addresses.

### 2. All five scope exclusions over-merged — #210, at 5 of 5

| exclusion | what it excludes | linked to | whose content that is |
|---|---|---|---|
| `exclusion-01` | whether the model yields an obligation | `…parse-nested-content-as-own-or-unread` | task-01/02/05, constraint-01 |
| `exclusion-02` | the decomposition prompt's wording | `…decision-recorded-in-repository` | completion-07 |
| `exclusion-03` | disposition reconciliation (#217) | `…parse-nested-content-as-own-or-unread` | task-01/02/05, constraint-01 |
| `exclusion-04` | recovering prior runs' dropped requirements | `…unclaimed-covers-all-task-file-text` | task-03/04, constraint-04/10 |
| `exclusion-05` | nested content under unrecognised headings | `…unclaimed-covers-all-task-file-text` | task-03/04, constraint-04/10 |

Not one yielded its own obligation stating what is *not* done.

Two ways this strengthens #210. Its sample was 3 mislinked of 10; this is **5 of
5**. And its predictor — *an exclusion whose only obligation is shared with a
**completion expectation*** — catches only `exclusion-02` here. The other four
merge onto Task and Constraints requirements. The signal generalises to *shared
with any non-exclusion requirement*, which is the form the structural detector
in #210's Deliverable would need.

### 3. A redundant obligation, created alongside the specific ones it duplicates

`obligation-region-level-total-coverage-tests` (from completion-05/06) restates
what `…region-level-coverage-assertion` (constraint-06),
`…coverage-on-committed-task-files` (constraint-07) and
`…coverage-on-decompose-stability-corpus` (constraint-08) already say between
them. The merged duplicate is then what absorbs constraint-11 and constraint-12
in finding 1 — an obligation with no requirement of its own becomes the bucket.

Relevant to #144, inverted: the problem is not failing to merge duplicates, it
is minting one.

## Triage

**Tool defects, all three. No finding attributed to task-file wording.**

| finding | disposition |
|---|---|
| 1 — constraint absorbed, own obligation missing | **new child of #181** |
| 2 — five exclusions over-merged | **#210**, evidence added as a comment |
| 3 — redundant merged obligation | recorded on the new issue; touches #144, #193 |

## Open questions

**Zero raised**, for the second consecutive run on this task file. Gate 1 step 3
had nothing to triage.

Worth noting against #206: this task file states a design decision as
undecided — *"Decide whether nested content … is a requirement in its own right
or a continuation of its parent"* — and #216 itself calls both defensible. A
decomposer that asks nothing here is not reticent, it is silent on an
acknowledged fork.

## What the breakdown gets right

The substance of #216 is covered accurately. Both deliverable halves, the
region-coverage invariant, the two regression cases, the reproduction's
five-or-three assertion, and the design decision all have faithful obligations.
The defects are confined to two cross-cutting constraints, the five exclusions,
and one duplicate.
