# Task
The §16 report prints test recommendations in their own block at the foot of the
report. An obligation whose test evidence is weak says nothing about the
recommendation that explains it, and the recommendation identifies its
obligation only through a `--criterion` slug that appears nowhere in the
obligation's own block. Joining the two is manual, and in the run that prompted
this they sat about two hundred lines apart.

§16 already rules this out: output is organised by obligation so that a
criterion's axes sit together rather than in separate lists the reader must join
by eye. A recommendation is a third axis and received exactly the treatment §16
forbids. The join key already exists, because `TestRecommendation.obligation_id`
is what builds the `--criterion` command.

Separately, `coverage/recommendations.py::recommend_tests` iterates the
recommendations a response returned and never reconciles them against the weak
obligations it asked about. A response returning three recommendations for five
weak obligations produces a report in which two weak obligations carry none, and
nothing distinguishes that from a complete answer.

Render each recommendation with the obligation it explains, and make a missing
recommendation an error rather than an absence.

## Constraints
- A recommendation is rendered inside the block of the obligation it names.
- A recommendation is rendered on the test-evidence axis, which is the axis it
  explains.
- The report contains no standalone recommendations section.
- The `--criterion` retrieval line stays with each recommendation.
- The report keeps its closing line pointing at the retrieval command.
- An obligation whose test evidence is below strongly supported carries a
  recommendation.
- An obligation whose test evidence is strongly supported carries none.
- A response that omits a recommendation for a weak obligation the call supplied
  is rejected.
- A response naming an obligation that is not weak is rejected rather than
  silently dropped.
- The count of recommendations in a produced review equals the count of weak
  obligations.
- The verdict summary counts weak obligations from the obligations themselves,
  not from the recommendation list.
- Typed schemas are pydantic models, as the rest of the repository defines them.
- Tests issue no live model calls.

## Scope exclusions
- Whether an obligation needs test evidence at all, which is #148. The rule
  built here is that a recommendation exists exactly when test evidence is below
  strongly supported; the further condition that tests are the right evidence
  for the obligation is not computable until #148 lands.
- Changing the strength classifier, or what counts as weak.
- Changing what a recommendation contains.
- Retrying or repairing a rejected response.
- The separate rendering of open questions and unrequested changes.

## Completion expectations
- Implementation
- A report containing weak obligations has no standalone recommendations
  section.
- Each weak obligation's rendered block contains its own recommendation.
- A strongly supported obligation's rendered block contains no recommendation.
- A response omitting a recommendation for a supplied weak obligation is
  rejected.
- A response naming a non-weak obligation is rejected.
- A review carrying weak obligations has one recommendation per weak obligation.
- A report with no weak obligations renders no recommendation text.
