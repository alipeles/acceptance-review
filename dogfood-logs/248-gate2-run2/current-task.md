# Task
An obligation that a response states twice is read as one obligation.

## Constraints
- A requirement's obligations are read as a first obligation followed by the
  remaining ones.
- A first obligation that reappears at the head of the remainder is one
  obligation, not two.
- A remaining obligation is a repeat of the first only when every one of its
  fields is exactly equal to the first's.
- A remaining obligation that differs from the first in any field is kept.
- The same obligation appearing later than the head of the remainder is kept.
- Reading a repeat as one obligation is recorded.
- The record attributes the repeat to the shape of the response rather than to a
  faulty answer.
- A requirement that yielded obligations is never left holding none.
- The surviving obligation keeps its content unchanged.
- The surviving obligation carries no identifier suffix earned only by a repeat.
- Two runs over byte-identical task text produce byte-identical review state.
- Tests issue no live model calls.

## Scope exclusions
- What the response's obligation fields are called, and any instruction given
  about how to fill them.
- Whether two obligations stating the same thing in different words are merged,
  which the linking stage decides.
- How finely a single requirement is split into obligations, and how many
  obligations one requirement may yield, which is #117.
- Assigning obligation types, which is #205.
- Which open questions are raised, and what they cite, which is #206.
- Measuring how accurate decomposition is, which is #211.

## Completion expectations
- Implementation
- A test asserts that a requirement whose remaining obligations begin with an
  exact repeat of its first obligation yields one obligation.
- A test asserts that reading such a repeat as one obligation is recorded.
- A test asserts that a remaining obligation differing from the first in any
  single field is kept.
- A test asserts that a repeat appearing later than the head of the remainder is
  kept.
- A test asserts that the surviving obligation carries no identifier suffix
  earned only by a repeat.
- A test asserts that the surviving obligation's content is unchanged.
- A test asserts that two runs over byte-identical task text produce
  byte-identical review state.
