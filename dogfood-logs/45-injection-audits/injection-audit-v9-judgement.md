# Judgement — injection audit v9 (candidate edits, smaller model)

Judged 2026-09-22 by four judging passes reading 16 sections each of
`injection-audit-v9.md` against the source at `518f876`, by the categories in
`docs/audit-protocol.md` and the instructions in `judge_audit.md`. Refusal
correctness for seven sections was re-judged after a fix to the renderer, below.

**Two things changed at once from v8, so this run cannot attribute either.** It
adds #334's candidate loop — up to three candidate edits per defect, each later
request showing why the earlier one was refused — *and* it moves edit building
from `openai/gpt-5.4` to `openai/gpt-5.4-mini`. The validity drop below is
therefore not evidence about the candidate loop. #334's Acceptance asks for a
like-for-like comparison against v7 or v8, and that needs a second arm holding
the model fixed.

Same 64 defects, same 22 criteria, same revision as v7 and v8. Verification on,
with its two questions on `openai/gpt-5.4` so that #335's bar is measured on the
model it was set on.

## The table

| | v7 | v8 | v9 |
|---|---|---|---|
| edit-building model | gpt-5.4 | gpt-5.4 | **gpt-5.4-mini** |
| candidates per defect | 1 | 1 | **up to 3** |
| edits counted (kills and survivals) | 44 | 48 | 41 |
| put the named defect into the code | 25 (57%) | 25 (52%) | **10 (24%)** |
| repair a defect the code already had | 3 | 4 | 10 |
| change something other than the defect | 12 | 17 | 18 |
| break far more than the defect | 4 | 2 | 3 |
| change no behaviour at all | not recorded | not recorded | **2 (5%)** |
| real kills | 23 of 36 (64%) | 21 of 39 (54%) | 10 of 31 (32%) |
| defects with no usable edit | 8 refused | 7 refused | **19** |
| already-present claims | 12: 9 right | 9: 9 right | 3: 3 right |

## What it says

**The smaller model is much worse at building edits, and the candidate loop does
not rescue it.** Under a quarter of the edits that passed the gates inject their
defect, and 19 of 64 defects produced no usable edit at all after three tries —
most of those three tries returning the same no-op edit, because temperature is
zero and the refusal shown in the later request did not move the answer. That is
direct evidence for #354, the issue on raising this stage's temperature, which
was sequenced after this measurement.

**The share of passing edits that change no behaviour is 5%, 2 of 41.** That is
the figure #334's Acceptance makes its conditional on. On this arm it is small.
Both cases are re-insertions of code that is already there: a duplicate
unreachable `except OSError` at `mutation/runner.py:136-145`, and an added
conjunct at `pipeline.py:284-285` that is always true. Neither is the kind of
edit a text comparison could catch, so if the figure is larger on the other arm,
the better check #334 contemplates is still the answer.

**What it cost.** $1.2276 and 970 seconds of wall clock for 64 defects, of which
$0.5664 and 256 seconds of live model time was edit building — $0.0089 per defect
asked about, at k=3. 117 candidate edits were bought for 64 defects, 1.83 each.
Of the 42 defects that got a usable edit, 28 used the first candidate, 13 the
second and 1 the third, so asking again is what produced a third of the usable
edits.

## The verifier, against these labels (#335)

**The bar is met: 29 of 31 bad edits refused (94%, bar 80%), and 0 of 10 good
edits refused (0%, bar under 10%).** The defect-match question refused 28 of
those; the behaviour-change question refused 1.

**This is not yet enough to adopt it.** Ten good edits is a small denominator,
and 0 of 10 is consistent with a true false-alarm rate well above 10%. The arm
also differs from the one the bar was written against: these are the smaller
model's edits, which are wrong in more obvious ways, so refusing them is an
easier task than refusing `gpt-5.4`'s.

## The refusals, and two that were wrong

The renderer did not show refused candidates' diffs, so the first judging pass
could not grade seven refusals and returned `null` for them. The renderer was
fixed, the Markdown re-rendered from the stored attempts at no cost, and those
seven were re-judged. **Two refusals were incorrect — a real injection thrown
away in each case:**

- `single-continuous-edit-in-named-region/region-containment-check-too-permissive`.
  All three candidates invert `if not any(region.contains(...))` at
  `mutation/validity.py:119`, which is the defect's defective behaviour word for
  word. Set aside for failing 29 of 339 tests — which is what a correct
  injection of *this* defect looks like, since every injected edit passes through
  that check. **Audit v8 recorded the same false refusal on the same defect**, so
  this is systematic, not a one-off.
- `execution-could-not-settle-defects/unsettled-defects-dropped-from-review-state`.
  Candidate 3 rewrites `pipeline.py:643` so no unsettled attempt is stored, which
  is the defect's defective clause. Refused only because the span sits outside
  the region the defect named.

The other five refusals were correct: byte-identical repeats, an unparsable
edit, one that reads a name before its only assignment, one that tightens the
rule the defect wanted loosened, and one that crashes at import.

## What was hand-checked

The protocol requires a hand-checked sample, because the judging pass is itself
a model. I checked three labels by reading the source at `518f876` directly, and
all three stood:

- `parser-files-still-parse/parse-errors-treated-as-acceptance` — `injects`. The
  edit makes `validity.py:132-133` return `None` on a parse error, so an edit
  that does not parse is accepted.
- `report-lists-set-aside-tests/report-omits-set-aside-tests` — `injects`. The
  edit drops `{test.test_id}` from `report.py:312-315`, so the set-aside section
  names no test.
- `no-whole-suite-run/whole-suite-execution-flag` — `changes_behaviour: false`. I
  read `runner.py:130-147` and the `except OSError` handler the edit adds is
  already there, so the edit produces a second, unreachable copy.

**v8 and v9 carry different edits for the same defects**, so a different category
is not evidence that either judge erred, and the protocol's rule about
prioritising disagreements does not apply between these two runs. It applies
between two passes over one diff.

## Limitations

- One run per arm. A five-point move is not separable from noise; a 28-point one
  probably is, but it is not attributable while two variables moved together.
- The judge is a Claude model. The edits here were built by an OpenAI model, so
  the same-family caution in the protocol does not bite on this arm.
- Rates, not paired defects, for anything compared with v6.
