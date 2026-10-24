# Task

The shortest opening the client marks as reusable follows Anthropic's current
documented minimum for each model: 512 tokens for Claude Sonnet 5.5, Opus 5.5 and
Haiku 5.5. The module documentation says that Anthropic ignores a breakpoint
below the minimum, rather than that it rejects one.

Repeated calls of the defect-to-test pair mapping stage that share an opening are
read from the cache.

In the mutation descriptor stage, a region's numbered source sits in the reusable
opening, so calls for defects in the same region share it instead of each
repeating it.

A run can opt in to sending its model calls through the Message Batches API. The
setting belongs to the run's configuration and is off by default, so
`acceptance check` and `acceptance decompose` keep calling the model directly.
Benchmark scoring and experiment scripts can switch it on.

How a call was sent does not change what was asked: a batched request is recorded
under the same key as the same request sent directly, and its recording replays
with no live call. The recording notes that it was sent through a batch. Two
recorded runs over the same input still produce byte-identical review state
whichever way their calls were sent.

## Scope exclusions
- Changing how live review runs split their requests into partitions.
- Reporting spend per run.
- Re-measuring benchmark figures on Claude.
- Changing any prompt or response schema other than the mutation descriptor's.
