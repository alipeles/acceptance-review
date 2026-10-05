# Judgement — injection audit v11 (coding agent on v10's wrong edits)

Judged 2026-10-05 by one Claude judging pass, following `judge_audit.md` and
`docs/audit-protocol.md`, against the source at `518f876`. Labels are in
`labels/v11.json`. **Not yet hand-checked.** The protocol asks for a larger
hand-checked sample when the builder is a Claude model, because the judge is a
Claude model too. This arm is Claude-built, so its figures are provisional until
a human checks a sample.

## What this arm is

#338 adds a coding agent, Claude Code, as the last candidate per defect, asked
only when every one-call candidate fails the mechanical checks. On v10's setup no
defect reaches that point: #334's three candidates gave every defect a usable
edit. So routing would never send any v10 defect to the agent. Decided by the
human, 2026-10-05: ask the agent directly, once each, about the 21 defects whose
v10 edit passed every check but was judged not to plant the defect
(`v11-defects-v10-got-wrong.json`). Agent: Claude Code with
`claude-sonnet-5-5`, through `run_audit.py --agent claude-code --agent-only
--only ...`. Verification on gpt-5.4, as in v10.

## Result, same 21 defects

| | v10 one-call (gpt-5.4, up to 3 candidates) | v11 agent (one run) |
|---|---|---|
| edits used (killed or survived) | 21 | 9 |
| planted the named defect | 0 | **6 (6 of 9 used; 6 of 21 asked)** |
| unrelated | 13 | 2 |
| backwards (repaired a defect already present) | 5 | 0 |
| overbroad | 3 | 0 |
| unclear | 0 | 1 |
| no usable edit | 0 | 12 |

Of the 12 with no usable edit, 11 runs made no change and 1 made two separate
edits. The judge's separate assessment of whether making no change was right:

- **already defective, 7:** the code already does the defective behaviour, so
  there was nothing to plant. v10's builder edited these anyway: its 5 backwards
  edits are among them.
- **no single contiguous edit plants it, 3:** plus the two-edit run, where
  neither edit alone would have planted it either.
- **plantable but not attempted, 1:**
  `does-not-run-first/static-judgement-still-runs-before-execution`, and only by
  a contrived extra call whose result is thrown away.

So on these defects the agent's answers were right in 16 of 21 cases: 6 edits
that plant the defect and 10 correct refusals. v10's one-call builder was right
in none.

## Cost and time

Agent: $3.52 for 21 runs, $0.17 per defect on average, 54 s of agent time per
defect (1,142 s summed), and 501 s wall clock with two runs at a time. v10's
one-call builder: $1.60 over 72 calls for 64 defects, about $0.025 per defect
and about 3 s per call. Those are averages: v10 predates per-defect recording.
Per-defect figures for v11 are in `injection-audit-v11.log` and the attempts
JSON's `per_defect`. The agent costs about 7 times as much per defect.

## What this does not show

- The labels are one Claude pass, unchecked by a human.
- These 21 are the defects the one-call builder got wrong, which is a selected,
  harder set. The rate is not comparable with v10's overall 31 of 52.
- One run per defect, one model, so there is no variance estimate.
- An agent that sees the code already has the defect can only make no change.
  It cannot record it as a finding the way the one-call builder's
  `already_present` answer does. So 7 true findings were lost here as plain "no
  usable edit".
- The two-edit run's diff is in the recording only, not in the audit Markdown.
