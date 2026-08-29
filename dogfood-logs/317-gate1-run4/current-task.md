# Task
Every requirement of a mandate is accounted for on its own, and an obligation
quotes the requirement it came from. The mandate's opening summary is accounted
for last, against the obligations the rest of the mandate already produced, so
that a property the rest of the mandate states does not become a second
obligation and a property only the summary states is not lost.

## Constraints
- A requirement other than the opening summary is accounted for by a step asked
  about that requirement alone, and that step returns exactly one account of it.
- The quotation an obligation carries is chosen from the text of the requirement
  its step was asked about, so a quotation belonging to a different requirement
  cannot be given.
- No step that accounts for a requirement other than the opening summary is
  asked to account for the opening summary.
- The opening summary is accounted for by a step that first divides it into
  stretches of its own words and then decides, for each stretch, whether the
  obligations already derived from the rest of the mandate require the same
  thing.
- Every stretch is a substring of the opening summary, and every stretch is
  decided exactly once.
- A stretch the already-derived obligations require yields no obligation.
- A stretch they do not require yields obligations, derived by a step asked
  about that stretch alone.
- The step that decides whether a stretch is already required yields no
  obligations itself.
- An obligation derived from a stretch carries that stretch as its quotation,
  taken from the mandate rather than from the answer that named it.
- A step may name the model it runs on; a step that names none uses the run's
  own model.
- A completed run says which model each step used.
- Where a step tells the answering party what order its request presents its
  parts in, that statement is true of the request as sent.

## Scope exclusions
- Which text in the mandate counts as a requirement, and how many requirements
  are found.
- Whether the obligations derived for a requirement are the right ones for it.
- What the review does with an answer it cannot read at all.
- Combining obligations that state the same thing as one another.
- Which model is the right one for any step, and what any step costs.
- Comparing figures recorded before this change with figures recorded after it.

## Completion expectations
- Implementation.
- A test fails when a step accounting for a requirement other than the opening
  summary is asked about more than that one requirement.
- A test fails when an obligation carries a quotation belonging to a requirement
  its step was not asked about.
- A test fails when a step that accounts for a requirement other than the
  opening summary is asked to account for the opening summary.
- A test fails when a stretch of the opening summary is decided more than once,
  or is left undecided, or is not a substring of the opening summary.
- A test fails when a stretch the already-derived obligations require yields an
  obligation.
- A test fails when a stretch they do not require yields none.
- A test fails when an obligation derived from a stretch carries a quotation
  other than that stretch.
- A test fails when a step naming its own model is run on the run's model
  instead.
- A test exercises the whole path from the mandate through to the obligations
  produced, not any one step alone.
- Two recorded runs over the same input produce byte-identical review state and
  byte-identical report output.
