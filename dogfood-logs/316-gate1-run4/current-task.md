# Task
The rating a criterion gets for its test evidence is derived from the judgements
the review has already recorded about the ways a change could fail that criterion
and about whether each candidate test would fail on each of them. The tests the
review prescribes are derived from those same judgements. So is the conclusion
the review reaches. The older judgement of which tests bear on which criterion,
and of whether a test discriminates, is removed.

## Constraints
- A recorded way of failing is covered when some candidate test would fail if the
  delivered code failed that way. A criterion all of whose recorded ways of
  failing are covered is strongly supported; one where some are covered is
  partially supported; one where none are, while candidate tests exist, is
  nominally supported. Where no candidate test exists, or the judgement could not
  be reached, the outcomes the review already has for those cases stand.
- Every rating the report shows names how many of that criterion's recorded ways
  of failing are covered, and how many were recorded.
- A criterion for which the review recorded no plausible way of failing, and said
  why, gets an outcome of its own, neither strongly supported nor unsupported,
  and the report says test evidence cannot be obtained for it.
- Every test the review recommends names one recorded way of failing that no
  candidate test would fail on, and that record carries a link to the criterion
  text it comes from.
- A recommendation asking for evidence the review already holds cannot be
  produced.
- The ratings keep the names they have today, and what each of them means is
  unchanged.
- Where the review's measured accuracy is reported, that report says the figures
  do not span this change.
- Two recorded runs over the same input produce byte-identical review state and
  byte-identical report output.

## Scope exclusions
- Recording the ways a criterion could fail, and judging one of them against a
  candidate test.
- Which criteria the review derives from the mandate, and how it derives them.
- Running the delivered code or any test.

## Completion expectations
- Implementation.
- Documentation update.
