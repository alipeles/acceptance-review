# 338 Gate 2 run 1 — judgement

Run 96b59ff781e87bca, continuing Gate 1 run 3 (e1d7ebe971fc4390). Base 10cdf2d,
head c204c34. Verdict INCOMPLETE. Not clean. $1.35 live.

## Real — addressed in d8b7b0e
- Obligation 7 (`preserve-current-review-behavior-when-unconfigured`) and 19
  (`one-call-builder-attempt-figures`), each partially supported with one
  recommended test. Both recommendations were the same gap: `render_per_label`
  was tested, but `cli._report_usage`, the function that calls it, was not. Added
  `TestTheCliReportsCostPerDefect` (two tests). A planted fault that printed the
  table without an agent run failed the unconfigured case.

## Tool defects — drafted in docs/DEFERRED.md
- Obligation 23 (`existing-builder-prompt-and-candidate-count-unchanged`),
  partially addressed, which is why the verdict says "not fully implemented". A
  scope exclusion turned into a prohibition (#272). One of the two reasons for
  the rating says the label changed the one-call builder's request, which is
  false: `test_a_label_does_not_change_the_request_key`. The other reason says
  the recorded `candidates_asked` now counts the agent's candidate. True, but the
  one-call builder is still asked `max_candidates` times, which is what the
  exclusion protects. Drafted: an evidence comment on #272.
- Obligations 12 and 13 (`test-files-removed`, `cannot-read-test-files`) were
  ruled "test evidence: not required", though `TestTheAgentCannotSeeTheTests`
  tests the first and a planted fault fails two of its tests. Drafted: a new
  sub-issue of #183, linked to #196, where the obligation was mistyped
  `docs_config`.
- Unrequested change 1, rated [risky]: the optional `label` keyword on
  `ModelClient.complete`. It is how obligation 19 is delivered (DR-338 Decision
  5), and five parallel changes were rated in_service. Drafted: a new sub-issue
  of #185.

## Accurate
- Obligation 20, the inverted exclusion from #310 (the Codex adapter), was
  judged "none breaches this boundary". Coverage read it as a boundary despite
  the inverted text, so #310's predicted not-addressed did not happen this run.
- Unrequested changes 2-6 are in_service and correct.
- No open questions.
