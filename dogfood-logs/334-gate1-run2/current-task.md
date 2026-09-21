# Task

When the review builds an edit for a named plausible defect, it asks for several
candidate edits instead of one and uses the first that passes the checks the
review already applies to an edit. How many candidates it asks for is
configurable. When no candidate passes, the defect is handled the way a defect no
edit could be built for is handled today.

The review also gains one further check on whether an edit changes anything at
all. The code is compiled before and after the edit and the two compiled forms
are compared, so an edit whose text differs from the text it replaced — by adding
a condition that is always true, by changing a value the caller ignores, or by
reordering with no effect — is refused when the two compiled forms agree.

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
