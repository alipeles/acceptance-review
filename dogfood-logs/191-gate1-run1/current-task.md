# Task
Plausible defects are enumerated for an obligation in one step, and the verdict
on each of them is reached in a separate step that covers one obligation at a
time.

## Constraints
- The plausible defects for an obligation are enumerated by a call of their own.
- The verdict on an enumerated defect is reached by a call separate from the one
  that enumerated it.
- A verdict call carries the defects of a bounded number of obligations.
- That number of obligations is configurable.
- That number of obligations is part of the recorded request.
- The enumeration request is determined by the obligation's text and by the
  changed code.
- The enumeration request is not determined by the tests mapped to the
  obligation.
- Editing a test mapped to one obligation leaves a different obligation's
  enumerated defects unchanged.
- Adding a test mapped to an obligation leaves that obligation's enumerated
  defects unchanged.
- The review pipeline reaches its defect verdicts through the separated steps.
- The change does not reduce the defects the tool identifies.
- Two runs over the same obligations and the same changed code enumerate the
  same defects.
- Two runs over the same obligations and the same changed code reach the same
  verdicts.
- Tests issue no live model calls.

## Scope exclusions
- How a rating is derived from the defect verdicts, which is #252.
- Which tests are mapped to an obligation.
- How an obligation is derived from a requirement.
- Reporting a rating that could not be reproduced, which is #254.
- Choosing the number of obligations per call for cost or latency.
- Whether a defect verdict is correct about the test it describes.

## Completion expectations
- Implementation
- A test asserts that enumerating an obligation's defects and reaching a verdict
  on them are separate calls.
- A test asserts that a verdict call carries the defects of no more than the
  configured number of obligations.
- A test asserts that the number of obligations per verdict call reaches the
  recorded request.
- A test asserts that editing a test mapped to one obligation leaves a different
  obligation's enumerated defects unchanged.
- A test asserts that adding a test mapped to an obligation leaves that
  obligation's enumerated defects unchanged.
- A test asserts that the review pipeline reaches its defect verdicts through the
  separated steps.
- A test asserts that two runs over the same obligations and the same changed
  code enumerate the same defects and reach the same verdicts.
