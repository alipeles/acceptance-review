# Task
Make a changed test-evidence rating justify itself. When a review repeated over
stored earlier state judges a criterion again, the judge is told what the rating
was and what changed about that criterion's dependencies, and a rating it moves
must rest on one of the changes it was given.

## Constraints
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
- Narrowing which criteria are judged again.
- Partitioning the evidence-judgement request per criterion.
- Making the set of tests mapped to a criterion stable across runs.
- Whether a rating is correct on its merits.
- Which defects the judge names for a criterion it does judge.
- Selecting which stored earlier state a repeated review continues.
- Which judgements other than the test-evidence rating are carried forward.
- Where the rule deciding whether a stored result may be carried forward is
  defined.

## Completion expectations
- Implementation
- A judgement asked about a changed criterion receives the stored rating and the
  changes to that criterion's dependencies.
- The stored rating and the dependency changes are part of the request the
  judgement is recorded under.
- A judgement that alters a rating while naming a change it was given is
  accepted.
- A judgement that alters a rating while naming no change it was given is
  rejected, and the stored rating stands.
- The code that reads a judgement performs the rejection.
- A rejected judgement is reported.
- A review with no stored earlier state puts no stored rating in any
  evidence-judgement request.
- Two reviews over the same stored state and the same inputs produce
  byte-identical review state.
- The findings recorded as correct in `tests/fixtures/rating-stability/` are
  still found.
