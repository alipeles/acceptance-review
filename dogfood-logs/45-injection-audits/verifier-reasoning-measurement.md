# The edit verifier with reasoning, measured against audit v10's labels

Run 2026-09-24. **Reasoning does not help the verifier.** The catch rate is
identical with and without it, false alarms are no better, and it costs three
times as much.

## The design, and why it is the cleanest arm so far

The verifier is measured over **audit v10's 52 observed edits, held completely
fixed**. Nothing re-builds an edit, nothing re-runs a test, and nothing is
re-judged: `labels/v10.json` is still the ground truth because the edits it
labels did not change. Only the verifier moves.

Every earlier comparison on this stage moved two things at once. Audits v9 and
v10 differ in both the candidate loop and the edit-building model; an arm with
reasoning on the edit builder would also unpin temperature, since OpenAI does
not accept a temperature on a reasoning call. Here one control moves and nothing
else can account for the result.

`reverify.py` does it, and a rerun is free:

    .venv/bin/python dogfood-logs/45-injection-audits/reverify.py \
        --repo ../45-audit-head --base 61c5a3c --head 518f876 \
        --attempts dogfood-logs/45-injection-audits/injection-audit-v10.attempts.json \
        --reasoning "mutation verification: defect match=high" --mode replay \
        --out dogfood-logs/45-injection-audits/verifier-reasoning-high.attempts.json

## The numbers

| | bad edits refused (bar ≥80%) | good edits refused (bar <10%) | cost |
|---|---|---|---|
| two questions, as audit v10 recorded | 16 of 21 (76%) | 5 of 31 (16%) | — |
| one question, no reasoning | 16 of 21 (76%) | 6 of 31 (19%) | $0.5009 |
| one question, reasoning `high` | 16 of 21 (76%) | 7 of 31 (23%) | $1.5779 |

70,572 reasoning tokens were spent in the third row. The bar is missed in all
three.

**The false-alarm column moves by one edit per row and should not be read as a
trend.** The no-reasoning arm moved 3 of 52 verdicts against v10's own recording
on an all-but-identical request, so one edge is this stage's measured
run-to-run noise. The reasoning arm moved 8 of 52 and still landed on the same
rate.

## What it says

**The verifier's weakness is not insufficient thinking.** All three versions miss
the *same five* bad edits, and 70,572 reasoning tokens recovered none of them.
That points at what the question is given rather than how hard it is considered:
the verifier sees the defect's two behaviours and 30 lines either side of the
edit, and by design it never sees the tests or what they did.

So the next thing worth trying on this stage is a different input — more code,
the enclosing call sites, or the defect's own `code_refs` — not more effort.
Raising effort is measured and spent.

**It also lowers the prior on reasoning for the edit builder.** A probe of three
defects with the edit builder on `openai/gpt-5.4-mini` at `high` cost $0.0699
per call against $0.0048 without, about 15 times, and 103 seconds per call. If
reasoning does nothing for judging an edit, a full arm at that price needs a
better argument than it had before this.

## Audit v10's published verifier rates are stale

The control arm here exists because v10's verification transcripts **cannot be
replayed**. #367, which removed the behaviour-change question, also edited the
remaining prompt: it deleted the sentence "The edit is already known to change
the code's behaviour", true only while the first question ran. The prompt is
hashed into the request key, so every verification recording from v10 orphaned.
A second change compounds it — the old code block rstripped each line, the new
one does not.

Nothing shared moved: v10's edit-building calls replay cleanly, 3 of 3 with no
live call, so the corpus is intact and only this stage was affected.

The practical consequence is that **v10's 76% and 16% describe a verifier no
longer in the code**, and #367's own commit message says its rates were not
re-measured. The middle row above is that re-measurement: removing the
behaviour-change question cost nothing, which is what #367 predicted.

## Limitations

- One run per arm, and `docs/audit-protocol.md` warns a small move is not
  separable from noise. Here the headline move is zero, and the noise floor was
  measured directly rather than assumed.
- 21 bad edits and 31 good ones. A single edit is 3 to 5 points.
- The labels come from one judging pass with three entries hand-checked, as the
  v10 judgement records.
- `high` only. A lower effort was not tried, because the case for it rests on
  high having helped.
