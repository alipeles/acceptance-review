# Judgement — #314 Gate 1, run 1

First decomposition of #314's mandate. 29 requirements, 28 with obligations, one
deliberately none. No open questions raised.

## Real findings, acted on

**`constraint-08` produced no obligation of its own.** "Which pairs share a group
does not affect whether any one of them is reused" was attached to
`constraint-06`'s obligation, `verdict-reuse-when-way-and-test-source-unchanged`,
which states only that a verdict is reused while the way of failing and the test
source are unchanged. Acted on by rewording for run 2. Run 2 reproduced the same
merge, and on re-reading, the merge is **correct**: `constraint-06`'s "exactly
while" already entails that nothing else bears on reuse, so the bullet was
redundant wording of mine rather than a tool defect. Deleted at run 3.

**`constraint-09` under-split.** "reuses every verdict it is entitled to reuse,
and produces again only those it is not" yielded one obligation covering the
first half only, while `constraint-01`, `constraint-02` and `constraint-12` — all
two-demand sentences in the same mandate — were each split into two. Acted on by
splitting the bullet at run 3, which produced both demands.

## Attributed to a known tool defect

**Two obligation-type slips losing a `test_demand` distinction.**
`completion-06` is typed `functional` where its four siblings of identical form
are `test_demand`; `completion-07` gets no obligation of its own and merges into
`constraint-11`'s `functional` one, so the demand that a test exist is gone from
the obligation set. This is the fourth and fifth instance of the defect already
in the queue as *"Two obligation-type slips, one of which loses the `test_demand`
distinction DR-232 exists to carry"* (`docs/DEFERRED.md`), whose drafted filing
is a comment on #181, the decomposition-quality umbrella. Recorded there as
further evidence rather than filed again. Both slips reproduce unchanged in runs
2 and 3.

**No open questions raised, on any run.** Consistent with #303, the filed defect
that decomposition cannot raise an open question about a requirement that also
yields obligations and has raised none since #217. Nothing new to file. It means
Gate 1's open-question triage had nothing to triage, which is not evidence that
the mandate is unambiguous.
