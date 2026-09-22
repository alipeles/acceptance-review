# Task

Before an injected edit's result is allowed to count as evidence, the review
checks that the edit really makes its named defect true. That check asks two
questions, in sequence.

The first asks whether the edit changes the code's behaviour at all. Both
versions of the code are compared with comments and whitespace removed, so an
edit that only reformats or re-comments the code is not mistaken for a change.
An edit that changes no behaviour is refused at this step, without the defect
being considered.

Only an edit that does change behaviour reaches the second question, which asks
whether the changed behaviour matches the defect's defective behaviour. An edit
whose changed behaviour does not match is refused.

An edit is verified only when it passes both. When an edit is refused, the review
records which of the two questions refused it and why, so that the two can be
told apart wherever refusals are counted.

Verification is on by default.

## Constraints
- Neither question is shown the tests, or what the tests did under the edit.

## Completion expectations
- Implementation
- Documentation update: the mutation-targeting decision record states the
  measured refusal rates that justify turning verification on by default.

## Scope exclusions
- Building an edit, choosing the region it falls in, or the mechanical checks
  that decide whether it is valid.
- Which tests are candidates, and running them.
- What a verified or unverified result does downstream once the check has
  decided.
