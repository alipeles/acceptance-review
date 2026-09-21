# #334 Gate 1, run 1 — judgement

Run `7be8d2eaf9d5acd6`, 27 live calls, $0.1377. Worktree
`334-sample-candidate-edits` at `0b751b4`. No `--continue`; this was the first
run for this task.

**Not accepted.** 24 obligations over 7 requirements, of which about 7 are
duplicates of another in the same run and 1 is invented. Zero open questions were
raised.

## Duplicates

| requirement | the pair | verdict |
|---|---|---|
| task-01 | `failed-candidate-set-aside` / `next-is-tried` | **tool defect** |
| task-02 | `behavior-unchanged-edits-refused` / `no-op-change-refused` | task-file wording |
| task-02 | `always-true-condition-is-refused` / `always-true-condition-refused` | task-file wording |
| task-02 | `no-effect-reordering-refused` / `no-effect-reordering-refused-2` | task-file wording |
| task-02 | `value-the-caller-ignores` / `ignored-value-refused` | task-file wording |

**task-02's four pairs are mine.** The task file stated the compiled-form check
in one sentence and then restated it in the next with three illustrative cases,
which is exactly the authored duplication CLAUDE.md warns about: *"Say each
requirement once — a constraint restated in a completion list is a duplicate
obligation we authored ourselves."* One of the pair members is also malformed —
`value-the-caller-ignores` reads *"The edit changes a value the caller ignores"*,
which drops the refusal and so is not an obligation at all — but that is a
consequence of being asked to decompose an illustration as though it were a
requirement.

**task-01's pair is not mine.** *"A candidate that fails a check is set aside and
the next is tried"* appears once in the task file, as one clause, and produced
two obligations whose descriptions differ only in word order: *"A candidate that
fails a check is set aside and the next candidate is tried."* and *"A failed
candidate edit is set aside and the next candidate is tried."*

Nothing merged and **no diagnostic was printed**. The run's log contains no
`Unreconciled linking answers` line, so this is not #242, where a cluster holding
one denied pair refuses to merge and says so. It is closer to #304, twin
Constraint/Completion obligations left unmerged with no diagnostic, but the twins
here are inside a single requirement rather than across two sections.

## The invented obligation

`candidate-edit-makes-defect-true` `[human_review/explicit]`: *"The review needs
an edit that makes a named plausible defect true."*

That sentence is the subordinate clause opening task-01 — *"When the review needs
an edit that makes a named plausible defect true, it asks for…"* — which sets the
condition under which the requirement applies. It is not a requirement, and the
same run derived `defect-truth-not-judged` from Scope exclusion 1, *"Whether an
edit that passes the checks really makes its named defect true"*. So the run
produced an obligation and its own exclusion, and tagged the obligation
`human_review`, which under the gate rules is a mandatory pause.

**Tool defect.** Drafted as a filing under #181, the decomposition umbrella.

## Disposition

The task file was rewritten — folding task-02's three illustrations into the
sentence that states the check, dropping the restated set-aside clause, and
rewording task-01's opening so the condition is not phrased as a need the review
has. Run 2 continues this run so the obligation set is carried rather than
re-derived.
