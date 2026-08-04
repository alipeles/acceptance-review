# Judgement — #167 Gate 2, run 5 (`dd0a6a5`)

Verdict: **INCOMPLETE**. **1** obligation below `strongly supported`.

| obligation | run 1 → 5 | judgement |
|---|---|---|
| `replace-written-file-with-command` | UNSUP → STRONG → STRONG → STRONG → `partial` | **Not real — a decomposition artifact, attributed to #144.** |

The obligation is a compound umbrella ("replace the file *with* the command
surface, *defaulting to JSON*") emitted **alongside** the individual obligations
covering each of its parts. Every constituent is strongly supported.

Checked rather than assumed, given this corpus's record: the defect the
recommendation names — a build that keeps writing `next-instruction.md` *and*
adds the command — **is** caught, by
`test_check_writes_no_instruction_file_even_when_the_review_has_gaps` and
`test_neither_the_pipeline_nor_the_cli_writes_into_the_reviewed_repo`. The
evidence exists; it is distributed across three tests because the obligation
bundles three claims, and no single test targets the conjunction.

Satisfying it would mean writing an artificial test asserting the union of what
five other tests already prove — fitting the suite to a decomposition artifact.
Recorded against **#144** instead.

## Where the five rounds landed

Findings per round: 2 → 4 → 3 → 3 → 1. **Seven real gaps were found and fixed**,
including a `--json` path that deleted a file in the user's repo silently. The
tool earned its keep here even while being unreliable — which is the strongest
argument in the corpus against "fixing" #180 by damping the judge.
