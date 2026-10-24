# Task

The review report states, for every enumerated defect the pair-judgement stage
was asked about, how many of that defect's pairs the run settled, how many were
put to the judge, how many were dropped as not worth asking, and how many were
skipped once the defect was covered. This holds for a defect the injection stage
did not attempt, whose injection outcome is `not_mutable` or `not_attempted`, as
much as for one it did.

The counts for such a defect are correct, not merely present. No edit was built
for it, so none of its pairs was settled by the run and none was dropped or
skipped on the strength of an edit: every one of its pairs is counted as put to
the judge, including a pair the judge was offered and did not answer. The count
of pairs put to the judge agrees wherever the report states it for the same
defect.

A regression test is part of the deliverable: it renders a review holding a
`not_mutable` defect and a `not_attempted` defect, each with pairs that went to
the judge, and pins the exact counts the report states for each.

## Scope exclusions

- How pairs are routed between the run and the judge is unchanged; only what the
  report says about them is in scope.
