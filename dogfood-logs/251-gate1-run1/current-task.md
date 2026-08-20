# Task
Re-judge a criterion's test evidence only when something that criterion depends
on has changed, and make a changed rating justify itself. A criterion depends on
its requirement text, the set of tests mapped to it, and the contents of those
tests. When a review repeated over stored earlier state finds all three
unchanged, the stored rating stands and nothing is asked of the judge. When one
of them did change, the judge is told what the rating was and what changed, and a
rating it moves must rest on one of the changes it was given.

## Constraints
- A criterion whose requirement text, mapped test set and mapped test contents
  are all unchanged keeps the rating stored for it.
- Such a criterion costs no evidence-judgement model call.
- A criterion whose mapped test set gained or lost a member is judged again.
- A criterion the contents of whose mapped tests changed is judged again.
- A criterion is compared against the stored state by the contents of its mapped
  tests, not by whether a file containing one of them was touched.
- Adding a test that is not mapped to a criterion does not cause that criterion
  to be judged again.
- Editing a test mapped to one criterion does not change the rating of a
  criterion that test is not mapped to.
- A judgement asked for a criterion that changed is given the rating stored for
  that criterion.
- A judgement asked for a criterion that changed is given the changes to that
  criterion's dependencies.
- The stored rating and the dependency changes given to a judgement are part of
  the request that judgement is recorded under.
- A judgement that alters a rating names one of the changes it was given.
- A judgement that alters a rating while naming no change it was given is
  rejected by the code that reads the judgement, rather than by the instruction
  that asked for it.
- A rejected judgement leaves the stored rating in place.
- A rejected judgement is reported.
- A review with no stored earlier state judges every criterion without reference
  to any stored rating.
- A review repeated over the same stored state and the same inputs produces the
  same review state as the one before it.

## Scope exclusions
- Partitioning the evidence-judgement request so that one criterion's request
  carries no other criterion's tests.
- Making the set of tests mapped to a criterion stable across runs.
- Whether a rating is correct on its merits.
- Which defects the judge names for a criterion it does judge.
- Selecting which stored earlier state a repeated review continues, which is
  done over git ancestry.
- Which judgements other than the test-evidence rating are carried forward.

## Completion expectations
- Implementation
- A criterion whose requirement text, mapped test set and mapped test contents
  are unchanged keeps its stored rating and issues no evidence-judgement call.
- Adding a test to a file that already holds a mapped test leaves unchanged the
  rating of a criterion whose own mapped tests were not edited.
- Editing a test mapped to one criterion leaves every other criterion's rating
  unchanged.
- A judgement asked about a changed criterion receives the stored rating and the
  changes to that criterion's dependencies.
- A judgement that alters a rating while naming a change it was given is
  accepted.
- A judgement that alters a rating while naming no change it was given is
  rejected, and the stored rating stands.
- A review with no stored earlier state puts no stored rating in any
  evidence-judgement request.
- Two reviews over the same stored state and the same inputs produce
  byte-identical review state.
- The findings recorded as correct in `tests/fixtures/rating-stability/` are
  still found.
