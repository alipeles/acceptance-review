# Judgement — #292 Gate 2, run 1

**Not clean.** `Task completion: INCOMPLETE`, with two obligations whose test
evidence is `unsupported` — meaning no mapped test at all — and a recommended
test for each. Run `13b24dfa89b21bcf`, continuing Gate 1's
`1ee26beb851d7843`. Base `763b1d6`, head `9319051`, record mode, $0.1487.

Everything else is clean: 26 of 28 requirements have obligations that are
addressed and strongly supported (or are scope exclusions correctly settled by
the source diff), **zero open questions**, and no unrequested change dispositioned
as anything worse than `in_service` apart from the Decision Record, which is
`separable` and expected.

Mapping was not half-blind (`DR-164`'s check): 12 mapping calls, and almost every
obligation came back with named tests.

## Finding 1 — a duplicate obligation split the evidence, and only one twin got the test

Obligation 3, `changed-criterion-gets-stored-rating` (constraint-01), has **no
mapped test**. Its recommendation asks for a test proving the stored rating
reaches the judge's request.

That test exists:
`tests/evidence/test_anchoring.py::test_a_changed_criterion_is_given_its_stored_rating_and_its_dependency_changes`
asserts the prompt contains `rating recorded by the earlier review:
strongly_supported`. The mapper mapped it to obligations **20** (completion-02)
and **21** (completion-03) — both strongly supported — and not to obligation 3.

Obligations 3, 20 and 21 are the **unreconciled linking triangle from Gate 1**,
filed as a comment on #242. Gate 1 predicted the cost: a duplicate obligation is
a criterion mapping must find tests for. This is that cost arriving.

**Disposition: address it.** Not attributed to the tool and left there — the
finding is fair on its own terms. My one test asserts two things at once, so the
mapper had to choose which obligation it evidenced. Splitting it into a test about
the stored rating and a test about the dependency changes gives each obligation
its own target, and is a better test either way.

## Finding 2 — `rating-stability-fixtures-still-found` is genuinely under-evidenced

Obligation 27 (completion-10), *"The findings recorded as correct in
`tests/fixtures/rating-stability/` are still found"*, has no mapped test.

The scoreboard it should rest on exists and passes:
`tests/benchmark/test_rating_regression.py` scores the corpus and fails in **both**
directions — `test_a_judge_that_always_issues_strongly_supported_fails_the_suite`
and `test_a_judge_that_never_issues_strongly_supported_fails_the_suite`. The whole
suite is green at 1423 passed.

But those cases are **first reviews**, so they never take the anchored path. They
prove this change did not break the unanchored pipeline. They do not prove the
anchoring mechanism cannot blunt the judge, because anchoring never runs in them.

**The finding is correct, and it points at a real defect. See below.**

## The defect behind finding 2, which is the important part of this run

**The rejection is symmetric, and `DR-180` says the two directions are not.**

`DR-180`'s central result: in 7 of the 8 unstable obligations, the LOW rating was
the correct one. Every case where a rating fell turned out to be the judge finally
noticing a hole that had been there all along. The tool errs toward "looks fine",
and `strongly supported` issued when unearned is the dangerous failure — far more
dangerous than churn.

As implemented, a rating that moves without naming a supplied change is held
**whichever way it moved**. So: a criterion whose test file changed is re-judged
and anchored; the judge correctly downgrades it, because it has finally noticed a
pre-existing hole that has nothing to do with the change it was shown; it names
no change, because none of them is the reason. My code holds the unearned
`strongly_supported`. That is `DR-180`'s exact defect, re-created by the fix for a
different one.

Two things bound how bad this is, and neither removes it:

- A criterion with no nameable change is not anchored at all, so the pure
  `DR-180` scenario — same inputs, judge looks harder — never reaches this code.
  Existing carry-forward already suppresses it, which is a separate problem.
- The prompt and the schema enum both push toward naming a change, so the judge
  has to actively omit it.

**The alternative worth considering: enforce asymmetrically — require a
justification to RAISE a rating, and let a fall through unjustified.** The
argument against is #269's 37→4 collapse, which was a mass *fall* and was wrong.
The argument for is that #269's collapse was caused by re-judging criteria that
should never have been re-judged at all, and **that is #293's fix, not this one**
— using #292's justification rule to suppress downgrades is making one issue pay
for another's gap, in the direction `DR-180` says is dangerous.

I did not decide this. It is queued as an open design decision with that
recommendation, because it changes what the delivered behaviour is and the
evidence points both ways.

## What I did not do

I did not re-run the gate after forming these conclusions. Finding 1's fix is
unambiguous, but finding 2's disposition changes the implementation, and
re-running before that is settled would burn a record-mode run on code that is
about to change.
