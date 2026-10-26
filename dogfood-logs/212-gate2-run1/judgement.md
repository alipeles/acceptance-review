# #212 Gate 2, run 1 — judgement

Run `dd5825e534a944a8`, `acceptance check --base 21d12a9 --head 2fa5577
--mode record --continue 9467b78f2b6336b7`. $1.20, 279 live calls.

**Not clean.** Verdict NO-MATERIAL-GAPS: 9 obligations addressed and strongly
supported, 5 code-only obligations addressed, mandate coverage 7 of 7. Two
things stop it.

## 1. Unrequested change — real, address it

`tests/support.py::client_returning_capturing_prompts`, rated `in_service`. The
helper is used only by `tests/requirement/test_task_context.py`. Fix: move it
into that test file.

## 2. "Defects the delivered code already has … needs human review" — a pause

Twelve entries, three distinct claims.

**(a) A sub-heading inside Context ends the Context section — real.** Nine of
the twelve entries. `parse_task_file` sets `section` from every heading at any
level, so `### Measurements` under `## Context` sends the blocks after it to
`unclaimed` (coverage reported incomplete), and `### Constraints` under
`## Context` would send background into the mandate. My tests never put a
sub-heading inside Context. Proposed fix: while in Context, a heading deeper
than the Context heading stays in Context; plus a test with `### Measurements`
and one with `### Constraints` under Context.

**(b) Only the exact heading `Context` is recognised — not a defect.** Every
other section heading is matched exactly too, and `Background` is deliberately
NOT recognised: `test_the_same_text_under_an_unrecognised_heading_still_bounds_coverage`
pins that unknown headings stay unread source. The repair the tool proposed
fails five existing tests for that reason.

**(c) `ParsedTaskFile` always carries `context: []` — not a defect.**
`ParsedTaskFile` is not stored in the review state, nor hashed into any request
or carry key. Requests for a file with no Context section are byte-identical:
the full replay suite (2,009 passed) replays every recorded decomposition
transcript, and a changed request would miss its recording and abort.

## Pairs left unjudged

Four `passed_under_edit` entries, each with another candidate test that failed
under the same unverified edit. The report itself says this is not evidence
either way. No action.

## Tool defects

None attributed.
