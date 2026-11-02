# 432 decompose run 1 — judgement

Data for #440 (evaluating the decomposition redesign on real mandates), per the
M11 block in `CLAUDE.md`. Not a gate.

**Input:** the body of #432 exactly as filed on GitHub, unedited. Run on branch
`432-provider-adapters` (native Anthropic adapter, uncommitted), 2026-11-02.

**Output:** no requirements, no model call, no obligations, no open questions.

**Judgement: wrong, and silently so.** The issue has five `##` sections — The
problem, Proposal, Rejected alternatives, Cost, Acceptance — none of which the
parser recognises (`requirement/task_file.py` reads only Task, Constraints,
Scope exclusions, Completion expectations and Context). Every block is
unclaimed, so nothing reaches decomposition. The output says "Obligations:
(none)" and gives no sign that the whole mandate went unread. A real
acceptance reviewer would list at least the four Acceptance bullets.

This is the case the redesign targets: #435 names "#212's task-file sections"
as resolved by the mandate being any shape. For #440 it is the baseline: the
current tool yields nothing on an issue as filed.

**Why the input is `mandate.md`, not `current-task.md`:** three tests read every
`dogfood-logs/*/current-task.md` and require it to parse into at least one Task
behaviour, which this file deliberately does not. Named `mandate.md`, the
owner's choice on 2026-11-02, matching #435's term for the issue as filed.
