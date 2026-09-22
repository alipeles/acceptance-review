# Task

When the review builds an edit for a named plausible defect, it asks for several
candidate edits instead of one and uses the first that passes the checks the
review already applies to an edit. How many candidates it asks for is
configurable. When no candidate passes, the review says that none of the
candidates it asked for could be used, rather than that the defect cannot be
turned into an edit, and otherwise handles the defect the way it handles one no
edit could be built for today.

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
- Which tests are candidates, how the project's tests are run, and how the result
  of a run is read.
