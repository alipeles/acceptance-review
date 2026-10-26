# #212 Gate 2, run 2 — judgement

Run `39ddd65329d04089`, `acceptance check --base 21d12a9 --head 060fef5
--mode record --continue dd5825e534a944a8`.

**Not clean. Verdict INCOMPLETE** (run 1 was NO-MATERIAL-GAPS). Run 1's two
findings are gone: no unrequested changes, and the sub-heading defect is no
longer listed. Two obligations moved from strongly to partially supported.

## The rating moved on code that did not change

Both obligations are about `obligations.py`, which is byte-identical between
run 1's head (2fa5577) and this run's (060fef5); so are the tests run 1 cited
for them. Run 1 judged the same defects covered. That is a judgement flip, not
a regression in the change. I did not attribute it to a tool defect, because
both recommendations ask for evidence that was genuinely missing, and I
addressed both.

## context-section-optional-background — partially supported, addressed

Recommendation: nothing structural stops an obligation that quotes the Context
text. Partly right. The response schema already offers only the answering
requirement's own text as a quotation, so a compliant provider cannot quote
the background. But no test pinned that, and a provider that ignores the schema
gets the obligation kept (by design, `_obligations_from`) with only an
unusable-answer record. Added:
`test_the_context_is_never_offered_as_a_quotation` and
`test_an_obligation_quoting_the_context_is_reported_not_attributed_to_it`.

## context-shown-labelled-and-separate — partially supported, addressed in code

Recommendation: the background shared the requirement list's message, kept
apart only by a label. Right. Moved it to its own `TASK_CONTEXT` block in
`request_blocks.py`, which `assemble` places in the reusable-opening message,
a different message from the requirement list. An empty block is dropped, so
requests for a file without Context are unchanged. Added
`test_the_context_travels_in_a_different_message_from_the_requirement_list`.

## Defects the delivered code already has (needs human review)

Nine entries. (A first draft of this file said two; that was wrong, from
reading the section's tail only.)

- `deeper-mandate-heading-swallowed-into-context` — **real, owner's call.** My
  run-1 fix kept every deeper heading inside Context, so `### Constraints` under
  `## Context` swallowed real constraints silently. Put to the owner, who ruled
  2026-10-25: a mandate-named sub-heading ends Context (DR-216 decision 2's
  asymmetry). Fixed; `test_a_sub_heading_naming_a_mandate_section_ends_context`
  replaces the test that pinned the opposite.
- `context-in-same-subject-block-as-requirements` — real; the same finding as
  the partially-supported rating above. Fixed with the `TASK_CONTEXT` block.
- `context-label-not-named-context` — fair and cheap: the label read
  "BACKGROUND" while the mandate says "labelled as context". Renamed to
  "TASK CONTEXT".
- `context-heading-match-exact-only`, `context-heading-exact-match-only` — not
  a defect, as in run 1: every section heading is matched exactly, and
  unrecognised headings must stay unread source.
- `subheading-text-dropped-from-context`, `context-subheadings-dropped-from-shown-text`
  — not a defect: headings are structure under every section and are never
  recorded as blocks.
- `context-text-drives-obligations` — not a defect: its repair is to stop
  showing the context, which the mandate explicitly requires.
- `parsed-model-gains-context-field` — not a defect, as in run 1.

## Tool defects

None attributed.
