# Task
Keep each stage's answer format the same across a review run, so that a provider
able to reuse a repeated request is offered one.

## Constraints
- Where a stage's repeated requests share an opening long enough for the provider
  in use to reuse, every call that stage makes within one run declares the same
  answer format, whatever items that particular call asks about.
- An answer says which item it is about, naming that item by the identifier the
  request gave it.
- An item a call asked about, which its answer passes over, is recorded as an
  answer not obtained.
- An answer naming an item its call did not ask about is recorded as an answer not
  obtained, and is never read as a judgement about any item.
- A conclusion that holds only if every item was judged is withheld for a run in
  which some answer was not obtained.
- An identifier drawn from a set that is the same for every call of a run stays
  restricted to that set.

## Scope exclusions
- What any stage is asked, and the judgement it is asked to make.
- Which stages exist, how a stage divides its work across calls, and how large
  those divisions are.
- The order in which a request carries its content.
- Stabilising the answer format of calls whose shared opening is shorter than the
  shortest one the provider in use can reuse.
- Reporting tokens, cost or reused-token share, which a run already reports.
- Model calls issued by the measurement harness, which is not part of a review
  run.

## Completion expectations
- Implementation
- A test fails when two calls of one stage, whose shared opening the provider in
  use could reuse, declare different answer formats.
- A test fails when an answer naming an item its call did not ask about is read as
  a judgement about an item.
- A test fails when an item a call asked about is passed over by the answer and
  read as a judgement about that item.
- A test fails when a conclusion depending on every item having been judged is
  stated for a run in which some answer was not obtained.
- Two recorded runs over the same input produce byte-identical review state and
  byte-identical report output.
