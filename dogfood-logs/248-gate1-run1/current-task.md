# Task
A requirement does not yield the same obligation twice.

## Constraints
- Where one requirement yields two obligations whose descriptions are identical,
  only one of them is kept.
- Two obligations yielded by one requirement whose descriptions differ are both
  kept.
- Two descriptions count as identical only when they match exactly, character
  for character.
- Dropping a duplicate obligation is recorded, not silent.
- The obligation that survives is the first one the requirement yielded, so
  which one survives does not vary between runs over the same text.
- A surviving obligation's identifier carries no disambiguating suffix that was
  earned only by a duplicate that was dropped.
- A requirement that yielded obligations is never left holding none.
- Dropping a duplicate leaves the surviving obligation's own content unchanged.
- Two runs over byte-identical task text produce byte-identical review state.
- Tests issue no live model calls.

## Scope exclusions
- How finely a single requirement is split into obligations, and how many
  obligations one requirement may yield, which is #117.
- Whether two obligations stating the same thing in different words are merged,
  which the linking stage decides.
- Whether an obligation that lands on a requirement because its quotation was
  traced there duplicates one that requirement already yielded, which the
  linking stage decides.
- Assigning obligation types, which is #205.
- Which open questions are raised, and what they cite, which is #206.
- Measuring how accurate decomposition is, which is #211.

## Completion expectations
- Implementation
- A test asserts that a requirement yielding two obligations with identical
  descriptions keeps one of them.
- A test asserts that the dropped obligation is recorded.
- A test asserts that a requirement yielding two obligations with differing
  descriptions keeps both.
- A test asserts that a surviving obligation's identifier carries no
  disambiguating suffix earned only by a dropped duplicate.
- A test asserts that dropping a duplicate leaves the surviving obligation's
  content unchanged.
- A test asserts that two runs over byte-identical task text produce
  byte-identical review state.
