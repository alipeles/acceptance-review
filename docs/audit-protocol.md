# The injection audit protocol

How an injection run is judged, and what the recorded labels mean. Written
because #45 (M8.4, targeted mutation) measured the same thing nine times and
every number it reported — "half the edits are valid", the verifier's catch rate
— rests on this method rather than on anything the tool computes. A number
produced by an unrecorded method cannot be reproduced or disputed.

The label sets themselves are `dogfood-logs/45-injection-audits/labels/*.json`.

## What is being judged

The mutation stage asks a model for the smallest edit that makes one named
defect true, applies it to a copy of the project, and runs the candidate tests
against it. An audit asks a question the tool cannot ask itself: **did that edit
actually make the named defect true?** Everything downstream — the kill, the
survival, the criterion's rating — is only worth what the answer is worth.

A defect carries two behaviours (`Defect.expected_behavior`,
`Defect.defective_behavior`), and an audit judges the edit against them, not
against the defect's prose description.

## The five categories

Exactly one per edit.

| category | meaning |
|---|---|
| `injects` | After the edit the code does the defective behaviour, and before it did the expected one. A plausible small mistake. **This is the only category that makes the run's result evidence.** |
| `backwards` | The code already did the defective behaviour and the edit moves it toward the expected one. It repairs the code, so a test failing afterwards is catching the repair. |
| `unrelated` | The edit changes behaviour, but not the behaviour the defect names — including edits that change nothing observable. |
| `overbroad` | The edit makes the defect true and also breaks much more: it crashes, disables a whole feature, or refuses everything. A kill is then credited for the wrong reason. |
| `unclear` | Cannot be decided from the diff and the source. |

For an `already_present` answer — the model claiming the code already has the
defect — two separate judgements are recorded: whether the claim is **right** or
**wrong**, and whether its repair edit **repairs**, **does not repair**, or is
absent (**no repair**).

## How a run is judged

1. The run writes one Markdown file per audit, with a section per defect: the
   outcome, the two behaviours, the reason any check refused it, the tests that
   failed, and the diff.
2A judging pass reads every section against the project source **at the audited
   revision**, checked out in a separate worktree, read-only. It runs no tests:
   the categories are about what the edit means, not about what happened.
3. Each edit gets one category, with a one-sentence reason naming the lines that
   decided it.
4. Counts are derived as: every killed or survived entry is `injects` unless the
   pass named it otherwise. Refused entries are counted separately, because they
   never became a result.

## Known limitations of the method

These are not caveats to be waved off; each one has changed a published number.

- **The judging pass is a model, and its calls are wrong sometimes.** In audit
  v7 it called an edit `overbroad` that audit v8's pass called `injects` on the
  identical diff; reading it by hand, v8 was right. Rule since: **hand-check a
  sample, prioritising edits where two runs disagree**, and record which were
  checked.
- **The judge is a Claude model.** Any arm whose edits are also built by a
  Claude model is judged by its own family. Such an arm needs a larger
  hand-checked sample.
- **The v6 label set has been measured against twice**, so a result that clears a
  bar on it is not confirmed. The verifier's adoption bar must be met on labels
  it has not been tuned or measured against.
- **Comparisons across runs are rates, not paired defects.** Re-listing the
  defects changes them, so only a run that reuses a stored defect list compares
  defect by defect.
- **One run per arm.** A five-point move is not separable from noise.

## Counting rule for the refused entries

An edit refused by a mechanical check never becomes a kill or a survival, so it
is excluded from the validity rate and reported on its own line. Whether each
refusal was *correct* is judged too: a refused edit that would have injected its
defect is a cost of the check, and audit v8 recorded the first one — the reversed
containment check in `region.py`, refused because it failed 26 candidate tests,
which it did because every injected edit passes through that check.
