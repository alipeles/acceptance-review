# Judgement — injection audit v10 (candidate edits, model held at gpt-5.4)

Judged 2026-09-22 by four judging passes reading 16 sections each of
`injection-audit-v10.md` against the source at `518f876`, by the categories in
`docs/audit-protocol.md` and the instructions in `judge_audit.md`.

**This is the like-for-like arm #334's Acceptance asks for.** Same 64 defects,
same 22 criteria, same revision and same edit-building model as audit v8. The
only thing that changed is #334's candidate loop: up to three candidate edits
per defect, each later request showing why the earlier one was refused. Audit v9
moved the model as well, so it could not attribute anything; this one can.

## The comparison, with only the candidate loop moving

| | v8 (one candidate) | v10 (up to three) |
|---|---|---|
| edits counted (kills and survivals) | 48 | 52 |
| put the named defect into the code | 25 (52%) | **31 (60%)** |
| the same, per defect asked about | 25 of 64 | **31 of 64** |
| defects that produced no usable edit | 7 | **0** |
| real kills | 21 of 39 (54%) | 25 of 38 (66%) |
| repair a defect the code already had | 4 | 5 |
| change something other than the defect | 17 | 13 |
| break far more than the defect | 2 | 3 |
| already-present claims | 9: 9 right | 12: 12 right |

**The clear result is the refusals: 7 to 0.** Every defect got a usable edit.
That is precisely what #334 was for — before it, one refused edit and "this
defect got no mutant" were the same event — and it is far too large a move to be
noise.

**The validity result is real but smaller than it looks.** 52% to 60% is an
eight-point move on one run per arm, and `docs/audit-protocol.md` warns that a
five-point move is not separable from noise. The count that is less sensitive to
the denominator is injections per defect asked about: 25 of 64 to 31 of 64. Six
more defects got an edit that genuinely injects, and none lost one.

**What it cost.** $1.5952 and 236 seconds of live model time for edit building,
$0.0249 per defect asked about; $2.4834 and 1182 seconds of wall clock for the
whole run including verification. Only 72 candidate edits were bought for 64
defects — 1.12 each — because 46 defects used their first candidate, 5 the
second and 1 the third. The candidate loop is therefore nearly free on this
model: it costs a retry only where the first edit was refused.

Against the other arm, `openai/gpt-5.4-mini` is 2.8 times cheaper per defect
($0.0089) and produces less than half the valid edits (24%), needing 117 calls
for the same 64 defects because its refused candidates so often repeated
themselves.

## The share that change no behaviour: 4 of 52, 8%

This is the figure #334's Acceptance makes its conditional on, and **it is
larger on this arm than on the smaller model's (2 of 41).** The four are:

- `continue-with-set-aside-tests/set-aside-tests-still-count-in-conclusions` —
  `pipeline.py:509` filters on `v.test_id in set_aside_tests`, comparing a string
  against a list of `SetAsideTest` models, so the list is always empty.
- `mechanical-validity-checks/mechanical-checks-bypassable-through-execution-settings`
  and `run-candidate-tests-on-altered-copy/baseline-halt-prevents-execution` —
  an added conjunct at `pipeline.py:284` that is always true, because
  `baseline.py:148-160` only sets `halted` when `allow_failing_tests` is already
  false.
- the two `_parser_for` rewrites at `validity.py:138-142`, which produce the same
  result for every input.

None of these is reachable by a text comparison: each differs from the original
by far more than comments and whitespace. **Three of the four survived**, and a
survival is the finding that the builder's tests are weak — so a no-op edit does
not merely waste a slot, it manufactures a false accusation against the tests.

## The verifier's first question does not catch them (#335)

The behaviour-change question exists to refuse exactly these edits. Measured
across both arms, **it caught one of the six.** On this arm it caught none of the
four, and one of them — `parse-check-applies-only-to-some-file-types` — it
positively verified as good.

## The verifier against these labels: the bar is not met

**16 of 21 bad edits refused (76%, bar at least 80%) and 5 of 31 good edits
refused (16%, bar under 10%).** Every refusal came from the defect-match
question; the behaviour-change question refused nothing at all.

This is close to the earlier measurement on the v6 labels (77% caught, 26% false
alarms) and it contradicts audit v9, where the bar was met at 94% and 0%. The
disagreement is explained rather than mysterious: v9's edits came from the
smaller model and were wrong in more obvious ways, so refusing them was an
easier task. **This arm is the one that matters**, because it is the arm whose
edits are worth keeping.

So `ExecutionSettings.verify_edits` stays false, and `DR-171`'s Decision 3 is
not reversed.

## Limitations

- One run per arm, as the protocol requires noting. The refusal move (7 to 0) is
  large; the validity move (52% to 60%) is at the edge of what one run can show.
- The judge is a Claude model and the edits here were built by an OpenAI model,
  so the protocol's same-family caution does not bite.
- Judged against v8's labels as rates over the same defect list, and v8's own
  labels were produced by an earlier judging pass with the same known limits.
