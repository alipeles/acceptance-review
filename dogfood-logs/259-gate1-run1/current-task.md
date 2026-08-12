# Task
Obligation pairs too dissimilar to state one requirement are not asked about.

## Constraints
- Each obligation is embedded as a vector.
- The distance between two obligations is the cosine distance between their
  embeddings.
- A pair whose distance exceeds a threshold is never sent to the model.
- A pair whose distance is within the threshold is sent to the model.
- The threshold is configurable.
- The threshold defaults to 0.10.
- A pair excluded for stating a different kind of demand stays excluded whatever
  its distance.
- The number of pairs excluded by distance is recorded.
- The threshold in force is recorded.
- Both records are part of the persisted review state.
- An embedding request is recorded for replay.
- An embedding request is replayed rather than issued again once it has a
  recording.
- Changing the threshold invalidates the recorded linking requests.
- Changing the embedding model invalidates the recorded linking requests.
- Two runs over the same obligation set choose the same pairs.
- Two runs over byte-identical task text produce byte-identical review state.
- Tests issue no live model calls.

## Scope exclusions
- Whether a pair that is asked about is judged to state one requirement.
- How an obligation is derived from a requirement.
- How many pairs are grouped into one request.
- Measuring how precisely obligations are linked, which is #211.
- Recalibrating the threshold for a different embedding model.

## Completion expectations
- Implementation
- A test asserts that a pair whose distance exceeds the threshold is not sent to
  the model.
- A test asserts that a pair whose distance is within the threshold is sent to
  the model.
- A test asserts that the number of pairs excluded by distance reaches review
  state.
- A test asserts that the threshold in force reaches review state.
- A test asserts that a pair excluded for stating a different kind of demand
  stays excluded whatever its distance.
- A test asserts that changing the threshold invalidates the recorded linking
  requests.
- A test asserts that changing the embedding model invalidates the recorded
  linking requests.
- A test asserts that an embedding request is replayed from its recording rather
  than issued again.
- A test asserts that two runs over the same obligation set choose the same
  pairs.
