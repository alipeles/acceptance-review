# Task
Make the cost of a run attributable to the stage that incurred it. Every model
call the review pipeline issues records which stage issued it, how many tokens it
used, what it cost, and how much of its prompt the provider served from cache. At
the end of a run the tool reports that breakdown stage by stage, keeping what the
run itself spent separate from what its evidence cost when that evidence was
first recorded.

## Constraints
- Every model call the review pipeline issues records the stage that issued it.
- No model call the review pipeline issues reports its stage as unknown.
- Recorded usage carries the cached-token counts the provider reports alongside
  the prompt token count.
- A cached-token count the provider does not report is absent from the recorded
  usage rather than recorded as zero.
- A call answered from a recording is observed with the same fields as a call
  answered by the provider.
- Each observed call records the stage that issued it, its request key, whether
  it was answered from a recording or by the provider, and its usage.
- A run reports tokens, cost and cached prompt-token share for each stage that
  issued a call.
- The cached prompt-token share of a stage is the share of that stage's prompt
  tokens that the provider served from its cache.
- A run's report distinguishes calls answered by the provider from calls answered
  from a recording.
- The cost reported for a call answered from a recording is what that call cost
  when it was recorded.
- The amount a run reports as its own spend counts only calls answered by the
  provider.
- The command-line interface surfaces the breakdown.
- Recording the stage of a call leaves that call's request key unchanged.
- Recording cached-token counts in a call's usage leaves that call's request key
  unchanged.
- The breakdown appears in no review state.
- The breakdown appears in no rendered report.

## Scope exclusions
- Any work to make a run cheaper, and any work to increase how much of a prompt
  the provider serves from its cache.
- Attributing cost to anything finer than the stage that issued the call.
- Model calls issued by the measurement harness, which is not part of a review
  run.
- Recording what a call cost at any moment other than when the call was made.
- Computing the price of a token, which the provider's own accounting already
  reports for each call.
- Presenting the breakdown anywhere other than the command line.

## Completion expectations
- Implementation
- A run reports tokens, cost and cached prompt-token share by stage, with calls
  answered by the provider distinguished from calls answered from a recording.
- A test fails when a model call site in the review pipeline omits the stage that
  issued it.
- A test pins that recording usage fields leaves every request key unchanged.
- Two recorded runs over the same input produce byte-identical review state and
  byte-identical report output.
