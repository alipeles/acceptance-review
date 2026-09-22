# Task

When the review needs an edit that makes a named plausible defect true, it asks
for several candidate edits instead of one and uses the first candidate that
passes the checks the review already applies to an edit. How many candidates it
asks for is configurable. A candidate that fails a check is set aside and the
next is tried, and when no candidate passes, the defect is handled the way a
defect no edit could be built for is handled today.

The review also gains one further check on whether an edit changes anything at
all. The code is compiled before and after the edit and the two compiled forms
are compared, so an edit that leaves behaviour untouched is refused even when its
text differs from the text it replaced. A condition that is always true, a value
the caller ignores, and a reordering with no effect each read as a change to the
text and as no change to the compiled form, and each is refused here.

For each defect, the review records how many candidates it asked for, how many it
set aside and why, and which candidate it used. Its report says what building
edits cost and how long it took, since asking for several candidates multiplies
both.

## Constraints
- Two runs over the same input pick the same candidate.

## Scope exclusions
- Whether an edit that passes the checks really makes its named defect true.
- Which plausible defects are enumerated, and which region of the code an edit is
  allowed to fall in.
- Running the candidate tests, and anything decided from what they did.
