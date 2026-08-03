# Task
Stop the mapping stage from silently shedding work on a large review. Mapping
currently asks one model call to judge every candidate test against every
obligation — on this repo, 96 tests × 17 obligations in a single structured
response. The response stays schema-valid but arrives with most test entries
carrying an empty obligation list, so obligations that do have tests are
reported as having none, and the reviewer's own failure is rendered as the
user's untested change. Partition that request along the tests axis: a bounded
number of tests per call with all obligations repeated in each call, and merge
the per-call results into the mapping the stage produces today.

## Constraints
- Every candidate test must still be judged against every obligation, so
  partitioning changes how the question is asked and never which pairs are
  considered.
- Batch composition must be a pure function of the stage's input, so that two
  runs over the same input issue the same requests and a recorded run replays.
- The partitioning mechanism is built to be reusable, but applied to the mapping
  stage only in this change.

## Scope exclusions
- Constraining id-bearing response fields to the ids supplied in the call is
  #163, sequenced immediately after this change because both touch the same
  prompt and schema.
- Applying partitioning to the coverage, unrequested-change, recommendation or
  discrimination stages is out of scope and measured as unwanted (DR-164,
  decision 2).
- The mapping stage's foreign-id filter is out of scope and is not changed by
  this task; it keeps its current behaviour.
- Re-recording the invalidated mapping transcripts is an operational
  consequence of this change, not part of its deliverable.

## Completion expectations
- Implementation
- The mapping stage issues several model calls, each covering a bounded subset
  of the candidate tests with all obligations repeated, instead of one call
  covering every test.
- The mapping the stage returns is the merge of the per-call results, so a test
  mapped in any call appears in the final mapping and downstream stages see the
  same shape of mapping they see today.
- Every candidate test is judged against every obligation across the calls, so
  no test-obligation pair is dropped by the act of partitioning.
- The tests are partitioned from a deterministic order, so the same input
  produces the same batches on every run.
- Each call is recorded and replayed as its own request, so a partitioned run
  replays from recorded transcripts without live calls.
- The number of tests per call is a run control carried with the other
  determinism controls, so changing it changes request keys the way changing the
  seed does and a review discloses the value that was in force.
- The partitioning mechanism is expressed so that a future stage can adopt it
  without reimplementing batching, while mapping is its only caller here.
- The documentation states that mapping-accuracy figures are not comparable
  across this change, so a benchmark reader is not misled into comparing them.
