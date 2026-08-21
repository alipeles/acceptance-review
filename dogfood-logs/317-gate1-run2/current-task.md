# Task
An answer that accounts for the same requirement more than once no longer costs
the review every requirement it read. What the review does with such an answer
turns on whether those accounts agree with one another.

## Constraints
- Several accounts of one requirement that agree on that requirement's outcome
  are combined into a single account of it.
- The combined account states every obligation the separate accounts stated, in
  the order the answer returned them, and drops none of them.
- Where combining would leave two obligations carrying the same identifier, they
  are made distinct, as obligations whose identifiers collide for any other
  reason already are.
- The review records that it combined several accounts of a requirement, and
  which requirement, rather than combining them silently.
- Several accounts of one requirement that disagree about that requirement's
  outcome stop the review.
- Several accounts that agree on the outcome but state one shared obligation
  differently stop the review.
- A requirement accounted for exactly once is unaffected.

## Scope exclusions
- How much of a review an answer the review cannot read at all stops.
- What the review asks in order to obtain an answer, and the shape of answer it
  asks for.
- How the review finds requirements in the mandate, and how many it finds.
- Which obligations an account states, and whether they are the right ones for
  the requirement.
- Combining obligations that one single account states more than once.

## Completion expectations
- Implementation.
- A test fails when several accounts of one requirement that agree on its
  outcome stop the review.
- A test fails when an obligation stated by one of several agreeing accounts is
  missing from the combined account.
- A test fails when combining leaves two obligations carrying the same
  identifier.
- A test fails when accounts are combined and the review does not record it.
- A test fails when accounts disagreeing about a requirement's outcome are
  combined instead of stopping the review.
- A test fails when accounts agreeing on the outcome but stating one shared
  obligation differently are combined instead of stopping the review.
- A test exercises the whole path from the answer through to the obligations
  produced, not the combining step alone.
- Two recorded runs over the same input produce byte-identical review state and
  byte-identical report output.
