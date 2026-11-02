# 432 decompose run 2 — judgement

Data for #440 (evaluating the decomposition redesign on real mandates). Not a
gate.

**Input:** run 1's issue text with its five headings mapped, and nothing else
changed (`diff` against run 1 shows only heading lines): The problem, Rejected
alternatives and Cost became `## Context`; Proposal and Acceptance became
`## Task`. Done deliberately, to see whether the current parser reads the
issue once its headings are ones it knows. Branch `432-provider-adapters`,
2026-11-02.

**Output:** again no requirements, no model call, no obligations.

**Judgement: wrong, and silently so — a second, separate cause.** The parser
does not read a bulleted list under `## Task`: `_list_target` in
`requirement/task_file.py` routes lists under Constraints, Scope exclusions and
Completion expectations, and has no case for Task, so the list goes to
`unclaimed`. A paragraph under the same heading is read. Probe:

```
'## Task\n\n- a thing.\n- b thing.'               behavior 0  unclaimed 2
'## Context\n\nbg.\n\n## Task\n\nThe parser …'     behavior 1  unclaimed 0
```

Proposal and Acceptance in #432 are entirely bullets, so all nine blocks were
unclaimed. This gap is already filed as #373 (a bullet list under the Task
heading is not read as any requirement), found at #372's Gate 1. What is new
here: the report printed no `!! NOT READ AS ANY REQUIREMENT` warning, because
`cli.py::render_decomposition` returns before `_unread_source` runs when no
requirement was found at all. A drafted comment on #373 is in
`docs/DEFERRED.md`. #436 (claims from every parser unit) is expected to
replace this path.

Neither run exercised the native Anthropic adapter, since neither made a call.

**Why the input is `mandate.md`, not `current-task.md`:** three tests read every
`dogfood-logs/*/current-task.md` and require it to parse into at least one Task
behaviour, which this file deliberately does not. Named `mandate.md`, the
owner's choice on 2026-11-02, matching #435's term for the issue as filed.
