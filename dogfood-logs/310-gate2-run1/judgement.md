# 310 Gate 2 run 1 — judgement: NOT CLEAN

Run `c25e896ecec51ca1`, base f1e71f2, head 78216a1, Sonnet 5.5. Cost $1.06.
Verdict UNABLE-TO-DETERMINE.

## Obligations
1-4: code addressed, test evidence strongly supported (5/5, 3/3, 2/2, 4/4). Real.
5 (`task-03`, the regression case, `tests_only`): test evidence **indeterminate,
no mapped test**. The delivered tests exist (`exclusion-05` in
`tests/prompts/test_decomposition_prompt.py`, exercised by
`test_every_scope_exclusion_yields_an_obligation_satisfied_by_absence`,
`test_every_scope_exclusion_requires_code_evidence_only`,
`test_no_obligation_anywhere_demands_the_excluded_work`). **Tool defect, already
tracked as #325** (a `test_demand` criterion is never enumerated for, so it is
permanently indeterminate); also #410's territory. No new filing.
6-7 (exclusions): addressed, code-only. Correct — and show this change working
on its own review: "test evidence: not required — A scope exclusion is satisfied
by work not done…".

## Unrequested change
`tests/test_pipeline_request_openings.py`, `in_service`. Real and needed: the
longer coverage prompt crosses Anthropic's minimum reusable opening, so the
client marks it and the message content becomes a list of blocks. Verified the
test passes on clean main, so the edit is caused by this change.

## "Defects the delivered code already has" (static, needs human review)
- `description-wording-left-to-model`: TRUE. The description is the model's;
  nothing rewrites it. This is the Gate 1 plan as confirmed (DR-310 Decision 2
  rejects an English check; the coverage mark makes the verdict robust). Owner's
  call: accept as designed, or add enforcement.
- `prompt-positive-reframing-still-possible` (bullets merged or dropped): FALSE.
  The prompt already says each bullet "produces EXACTLY ONE obligation"
  (obligations.py SCOPE EXCLUSIONS, outside the region shown to the judge), and
  the code rejects a response leaving any requirement undisposed (M1.2.r2).
  The judge reasoned from a slice of the prompt. Tool defect; filing drafted.
- `mark-without-bullet-falls-back-to-wording`: TRUE but narrow. An exclusion
  obligation has no source span only when the model quoted text outside its
  requirement (recorded as an unusable answer). Then the mark is a bare
  "(scope exclusion)". Fixable in code: fall back to the requirement's own span
  for an exclusion. Owner's call.
- `status-consistency-left-to-model-judgement`: TRUE by design. A breach is a
  model judgement; code cannot normalise statuses without overriding real
  breaches. Owner's call: accept.

## Injected defects that survived (not counted)
- `if exclusion and quote_override is None`: equivalent mutant — `quote_override`
  is set only for summary spans of the Task paragraph, never for an exclusion.
- `satisfied_by_absence=exclusion and not produced`: REAL gap. No test has an
  exclusion yielding two obligations, so marking only the first survives. A unit
  test closes it.

## Other
The mutation-descriptor stage's reason for `description-wording-left-to-model` degenerates into
repeated sentences ("No repair is offered beyond this.Reporting defective as
required…"). Noted in the drafted filing.
