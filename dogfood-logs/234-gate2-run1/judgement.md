# Judgement — #234 Gate 2, run 1

`INCOMPLETE`. Three obligations short of strongly supported. All three findings
were real; none was a tool defect.

## The two unsupported obligations were correct findings

- **constraint-04** — "what a commit records is determined by file content
  alone, not by modification times" — `unsupported`, no mapped test.
- **constraint-05** — "does not change when git compares using fewer fields" —
  `unsupported`, no mapped test.

My reflex was that both were mapping failures, because
`test_head_content_wins_when_the_replacement_has_matching_metadata` already
forced `core.checkStat=minimal` and holds mtimes equal, and the recommendation
for constraint-04 described that setup almost verbatim. Reading the
recommendations properly says otherwise, and they are right:

- That test holds mtime **constant** and varies content. constraint-04 is the
  converse claim — vary the mtimes, and the commit must not move. Nothing
  asserted it.
- That test runs **only** under the narrowed comparison. constraint-05 is a claim
  about *equality across* the two configurations. Nothing compared them.

A test that establishes the hostile condition is not the same as a test that
pins invariance under it. The tool drew a distinction I had elided.

**Disposition:** addressed in code —
`test_modification_times_do_not_change_what_is_committed` and
`test_recorded_commits_survive_git_comparing_fewer_status_fields`. Both fail
against `git add -A` alone and pass with the index reset, so they discriminate.
`task-01` (`partially supported`) cleared as a consequence.

## The separable formatting finding was also correct

> Reflowed `_git` into a single-line return expression and collapsed the
> `declaration_text` assignment formatting.

Real, and not mine: the repo's `PostToolUse` formatter hook made both edits. I
reverted them and the hook immediately re-applied them, so they cannot be
removed from this branch. Unrelated churn in the diff, attributable to tooling
rather than to the change.

## Not tool defects

The `in_service` unrequested changes (the `_stage_worktree` helper, the docstring
explaining the stale-stat-cache mechanism, the test helpers) are correctly
dispositioned — they are the means to the requested end. The two `separable`
entries for `docs/DEFERRED.md` and `session-state.md` are also correct: those are
process files, genuinely unrelated to the mandate.

Re-run: `234-gate2-run2`, clean.
