# 436 decompose run 1 — judgement

Input: #436's issue body exactly as filed (`mandate.md`), run on branch
`436-claims` before claims were wired into `decompose`. Data for #440 (the
evaluation of the redesigned decomposition), not a gate: M11 tasks take no
gates.

Result: no requirement, no model call, no obligation, no open question.

This is the same loss #432's runs recorded (`dogfood-logs/432-decompose-run1/`).
The body opens with a paragraph under no heading and lists its Acceptance
bullets under `## Acceptance`, which the parser does not recognise, so every
block is filed as unclaimed and the requirement registry is empty. No warning
says the mandate was not read (already queued as a comment on #373, where a
bullet list under `## Task` is lost).

All of it is a tool defect, and every finding is already tracked: #373 for the
lost text, and #436 itself, whose claims are built from every block the parser
produces, unclaimed ones included. Nothing new to queue.
