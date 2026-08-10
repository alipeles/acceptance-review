# Task
An obligation is attributed to the requirement its quoted text comes from.

## Constraints
- An obligation carries a quotation of the task text it derives from.
- An obligation's quotation is located within the span of the requirement the
  obligation is attributed to, not merely somewhere in the task file.
- A quotation is located without regard to where lines are broken, so the same
  sentence is found whether the text wraps or not.
- An obligation whose quotation falls outside the span of the requirement it was
  attributed to is re-attributed to the requirement whose span contains the
  quotation, when that requirement also yielded obligations.
- Re-attribution never leaves a requirement that yielded obligations holding
  none.
- An obligation is never discarded for a quotation that cannot be placed; it
  stays where it was attributed.
- Every disagreement between an obligation's quotation and the requirement it
  was attributed to is recorded, whether or not it was acted on.
- Re-attributing an obligation leaves the obligation's own content unchanged.
- A re-attributed obligation admits the evidence its new requirement's section
  admits.
- A requirement keeps every obligation whose quotation lies within its span.
- Two runs over byte-identical task text produce byte-identical review state.
- Tests issue no live model calls.

## Scope exclusions
- How finely a single requirement is split into obligations, and how many
  obligations one requirement may yield, which is #117.
- Whether two obligations on the same requirement are merged, which the linking
  stage decides.
- Assigning obligation types, which is #205.
- Which open questions are raised, and what they cite, which is #206.
- Whether requirement identifiers survive an edit to the task file, which is
  #209.
- Measuring how accurate decomposition is, which is #211.

## Completion expectations
- Implementation
- A test asserts that an obligation quoting text inside its own requirement's
  span keeps that requirement.
- A test asserts that an obligation quoting text belonging to a different
  requirement is re-attributed to that requirement.
- A test asserts that an obligation whose quotation matches no requirement's
  span stays where it was attributed, and that the disagreement is recorded.
- A test asserts that a requirement that yielded obligations is not left holding
  none by re-attribution.
- A test asserts that a quotation is located whether or not the text it comes
  from is broken across lines.
- A test asserts that re-attribution leaves the obligation's content unchanged.
- A test asserts that a re-attributed obligation admits the evidence its new
  requirement's section admits.
- A test asserts that no requirement loses an obligation whose quotation lies
  within its span.
- A test asserts that two runs over byte-identical task text produce
  byte-identical review state.
