# Task
Make prompt changes testable. Every capability test currently injects a hand-authored model response, so it verifies plumbing only and cannot fail when a prompt is edited; a prompt can therefore be changed, or be wrong from the start, with nothing detecting it. Establish a corpus of real recorded model responses that tests replay, so an assertion over a capability's output is an assertion about real model behaviour.

## Constraints
- Replay the recorded corpus by default, so the ordinary test run makes no live call and needs no API key.
- Editing a prompt must make the test suite fail, and the failure must identify itself as an unverified prompt change and say how to re-verify it.
- Re-recording must run the assertions against the freshly recorded responses, so a prompt that produces worse answers fails rather than silently re-recording.
- Record the corpus only against archetype fixtures, never against this repository's own review runs, because a recorded request embeds the whole prompt including the diff and task text under review.
- Record against the model the tool actually runs, so the corpus reflects production behaviour.
- Keep the corpus small and curated; the existing ad-hoc local cache is a developer scratch area and stays out of version control.

## Scope exclusions
- Converting the rest of the suite's injected-response tests to recorded responses is out of scope; this change establishes the mechanism and demonstrates it on a single capability.

## Completion expectations
- Implementation
- A prompt-quality test asserts a real recorded model response, and the ordinary suite replays it with no network access.
- A missing recording fails with a message naming the likely cause and the re-record command.
- Where a recorded response reveals that a prompt does not actually work, the failure is recorded as a known defect that will fail the suite again once fixed, rather than being hidden.
