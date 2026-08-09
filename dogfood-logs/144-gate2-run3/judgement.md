# Judgement — #144 Gate 2, run 3

`check --base 9724df4 --head 74e02ba`, with the pairwise sweep and clique rule.
**Still NOT CLEAN**, and on the headline numbers it is worse than run 2.

| | run 1 | run 2 | run 3 |
|---|---|---|---|
| derived → linked | 24 → 18 | 24 → 17 | 24 → **21** |
| merges | 5 | 7 | **3** |
| weak / unsupported | 4 | 5 | **8** |
| contradictions detected | — | — | **1** |

## What the sweep found, and it is the whole story

One `unusable_answer` finding, naming a component of **nine or more**
obligations — `linked-obligation-for-two-sections`,
`distinct-requirements-not-merged-by-vocabulary`,
`reason-clause-counts-as-same-requirement`, `post-derivation-linking-pass`,
`duplicate-recognition-links-existing-obligation`,
`linked-obligation-preserves-union-of-provenance`, and more.

The model confirmed enough pairs among these to chain them all into one
connected component, while denying at least one pair inside it. The clique rule
then discarded the entire component, which is why merges fell to 3 and weak
obligations rose to 8. The good merges inside that component — the reason-clause
rule and its acceptance criterion, plainly one requirement — went with it.

## Reading it honestly

**The sweep did not remove the false positives; it made them visible.**
`distinct-requirements-not-merged-by-vocabulary` chained together with
`post-derivation-linking-pass` means pairs were confirmed that should not have
been. Under the single-call shape those would have merged silently and shown up
as a smaller, cleaner-looking obligation set. Runs 1 and 2 *looked* better on
every metric while doing something worse.

So on correctness this run is ahead: no observed over-merge, and the
contradiction is on the record instead of laundered into the result. On the
Gate 2 metric it is behind, because under-merging leaves obligations that each
need their own evidence.

**The clique rule is too blunt at this scale.** The DR predicted the cost — "one
contradicted pair discards the good merges in its component" — and this run
measures it: at N=24 with many partial confirmations, nearly everything chains
into a single component, so one denied edge discards almost every merge in the
run. That is a scale property, not a one-off.

## The obvious next lever, not taken here

Extract maximal cliques *within* a contradicted component rather than discarding
it wholesale — greedy, in derivation order, so it stays deterministic. That
keeps the pairs the model actually confirmed together while still refusing to
invent the ones it denied. It is a real design change on top of a design change
already made twice this session, so it goes to the human rather than into a
third unilateral attempt.

## The four Task-prose obligations are unchanged

`duplication-per-requirement`, `later-stages-per-obligation`,
`duplication-is-ordinary-restatement`, `duplication-not-input-fault` remain
unsupported, exactly as in runs 1 and 2, and remain attributed to **#212**.
Nothing in this change touches them.
