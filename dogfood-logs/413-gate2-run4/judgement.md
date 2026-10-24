# 413 Gate 2, run 4 — judgement

Continuing run 3 (`fdafedfbfed085ce`) after one change: `pyproject.toml` moves
LiteLLM to `>=1.106,<1.107`. CI on PR #420 had installed 1.96.2 from the old
range, and on it LiteLLM passes temperature through to Claude, which refuses any
temperature. The two tests that ask LiteLLM which controls survive failed in CI
and caught it. $0.22 on 3 live calls.

Verdict INCOMPLETE. Not clean. Nothing new beyond what the owner accepted at run 3.

- `prompt-test-assertions-hold-on-claude-answers` still 4 of 5: #418.
- `recordings-rerecorded-against-new-default` is back to "addressed" with no
  change to its evidence, a second flip, which supports #419.
- Unrequested change 1, `in_service`: the LiteLLM range change. Accurate: no
  obligation names a dependency, and the change is needed for any live Claude call
  on the new default. Kept; no filing.
- Unrequested changes 2 and 3, `in_service`: the recommended tests again, #376.
