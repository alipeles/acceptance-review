# Judgement — #266 Gate 2, run 3

`check --task current-task.md --base 265bfac --head 95efe1e`.

## NOT CLEAN, and iterating further will not make it clean

Verdict `INCOMPLETE`, 5 of 34 obligations short of strongly supported. The two
corrections made after run 2 both worked — and seven *other* obligations fell in
the same run, four of them ones this commit added tests for and three of them
scope exclusions it did not touch at all.

## First: the run aborted before it rendered, on a guard I had just added

The first attempt at run 3 produced no report:

```
acceptance: model error: obligation
'test-review-produces-report-when-all-weak-criteria-have-statements'
was both recommended for and declined as unevidenceable
```

A real response put one obligation in both lists, and the contradiction guard
added in run 2's fixes raised — **reconstructing, one level down, the exact
abort this issue exists to remove.** I had written that guard's docstring
arguing a contradiction must not be resolved by precedence, and was right about
that and wrong about the consequence: not picking a side does not require
destroying the review.

Fixed in `95efe1e`: a contradiction and a reason-less refusal both become
`UnusableAnswer`s, leaving the obligation `indeterminate` with a major finding
naming it, and every other obligation reported. Omission still raises — the
issue's settled decision, and silence really is indistinguishable from
truncation.

Worth recording as the sharpest lesson in this task: **the fix for a
fail-closed defect is itself the most likely place to reintroduce one.**

## The tool's own delta section is the finding

Run 3 rendered a comparison against run 2's head, one commit earlier:

```
closed:
  A statement that no test can evidence a criterion carries a reason.
      test evidence: nominally supported -> strongly supported
moved:
  ...two runs produce the same statements    strongly supported -> partially supported
  ...a test bearing on several criteria      strongly supported -> partially supported
  ...every weak criterion answered           strongly supported -> UNSUPPORTED
  ...two runs, same statements (constraint)  strongly supported -> partially supported
  ...code-alone exclusion unchanged          strongly supported -> UNSUPPORTED
  ...request size unchanged                  strongly supported -> partially supported
  ...non-test evidence not recommended       strongly supported -> partially supported
```

The `closed` line is the empty-reason fix landing, confirmed by the tool.

The `moved` lines are the problem. Three of them are **scope exclusions** —
"the change does not alter X" — and nothing about them changed between the two
commits. One of them, *"A review in which every weak criterion is answered with
a statement that no test can evidence it produces a report"*, fell from strongly
supported to **unsupported in the very commit that added a dedicated test for
it** (`test_every_weak_obligation_declined_still_returns_a_result`).

Ratings are not tracking evidence. This is #225 — rating instability under
unchanged evidence — measured about as cleanly as it can be: two runs one commit
apart, the delta computed by the tool itself rather than reconstructed by hand,
and the direction of movement anti-correlated with the direction of the work.

## Why I stopped rather than running a fourth time

Three runs: 9 short, then 2, then 5. Each round produced one real finding and a
new set of movements. A fourth run would produce a fourth set, and the working
agreement's rule about failing the same way twice applies — the next attempt
would need to be a different approach, not another turn of the same handle.

The mapping fix is separately well-evidenced and should not be lost in this:
**7 of run 1's 9 findings went green with no test added and no test changed**,
only the instruction to the mapper. That result stands on its own.

## Disposition

- The mapping-prompt fix: **worked**, evidenced by run 1 → run 2.
- The empty-reason and all-declined fixes: **worked**, evidenced by run 2 → run 3's
  `closed` line.
- The abort-on-contradiction defect I introduced: **fixed**, with a wiring test.
- The residual 5 and the 7 movements: **attributed to #225**, comment queued.
  Not fixable inside #266, and not fixable by iterating.

**Gate 2 has not been passed.** Whether #266 ships without one is a human call,
not one this session can make.
