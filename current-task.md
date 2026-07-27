# Task
Derive an overall completion result — no-material-gaps, incomplete, needs-clarification, needs-non-code-review, or unable-to-determine — from the review's findings, with stated confidence limitations. A positive (no-material-gaps) result renders the §3.7 caveat that it means no material gaps at the achievable evidence tier, not proof of correctness. An unresolved open question cannot render a positive result.

## Constraints
- The verdict is a deterministic, pure function of the findings — never a model call — so the headline result is auditable and traces to the exact obligations and findings that produced it, not a free-text conclusion.
- Any coverage gap or any non-strong test evidence blocks a positive result (positive results are bounded); severity or importance weighted materiality is a deliberate future refinement, not built now.
- Advisory findings — an unrequested change or a declaration mismatch — never move the verdict; a change whose obligations are all strongly supported is no-material-gaps even alongside an advisory finding.
- Obligations whose evidence is indeterminate are surfaced as escalation candidates: the set where deeper retrieval or execution could move the verdict, so a future try-harder loop attaches there while this rollup stays a stable function.

## Completion expectations
- Implementation
- Each verdict state is produced for its corresponding finding pattern; a coverage gap or weak evidence yields incomplete, an unresolved open question yields needs-clarification, and all-strong yields no-material-gaps with the §3.7 caveat.
- An indeterminate obligation yields unable-to-determine and is listed as an escalation candidate.
