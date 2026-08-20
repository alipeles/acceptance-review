# Task
The rule deciding whether a stored result may be reused is stated in one place
that names no stage of the review, and the stage that already applies that rule
reaches its answer through it.

## Constraints
- The rule deciding whether a stored result may be reused is stated in one place
  that names no stage of the review.
- The rule refuses reuse unless all four of these hold: the unit is still
  present, re-deriving it would issue the same request, the logic turning a
  response into a result has not moved, and the stored result still fits the
  inputs it is being reused against.
- What a unit is, how it is identified, which of its inputs enter the request
  identity, and what it means for a stored result to fit its inputs, are supplied
  by the caller rather than by the rule.
- A refusal to reuse a stored result carries the reason for the refusal.
- Requirement decomposition reaches its reuse decision through that one statement
  of the rule rather than through a copy of it.
- The request identity computed for a requirement is unchanged by this work.

## Scope exclusions
- Applying the reuse rule to any stage other than requirement decomposition.
- Narrowing which criteria are judged again on a repeated review.
- Whether a stored result is correct on its merits.
- Selecting which stored earlier state a repeated review continues.
- The set of obligations requirement decomposition produces.

## Completion expectations
- Implementation
- The reuse rule is stated in one place that names no stage of the review.
- The rule refuses reuse when any one of its four checks fails.
- A caller supplies the unit's identity, the inputs entering the request
  identity, and the test of whether a stored result fits those inputs.
- A refusal to reuse carries the reason for the refusal.
- Requirement decomposition's reuse decision is produced by the shared statement
  of the rule and not by a copy of it.
- The request identity computed for a requirement is byte-identical to the
  identity computed for that requirement before this work.
- Requirement decomposition produces the obligations it produced before this
  work.
