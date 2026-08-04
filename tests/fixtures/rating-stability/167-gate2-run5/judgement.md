# Judgement — #167 Gate 2, run 5 (`dd0a6a5`)

Verdict: **INCOMPLETE**. **1** obligation below `strongly supported`.

| obligation | run 1 → 5 | judgement |
|---|---|---|
| `replace-written-file-with-command` | UNSUP → STRONG → STRONG → STRONG → `partial` | **A wrong verdict from M5.2. Attributed to #180.** |

> **This file was rewritten.** I first attributed this to #144 (compound umbrella
> obligation), reasoning that no single test could target the conjunction. That
> reasoning does not survive checking — see below. It is the **second** time in
> this corpus I concluded "not a real defect" too quickly.

## The isolation

Runs 4 and 5 are one commit apart and the obligation's mapped tests are
**byte-identical**. The discrimination stage named the same plausible defect in
both and judged it oppositely:

| run | `would_be_caught` | reason given |
|---|---|---|
| 4 | **true** | "The test explicitly checks that the file does not exist after `check`, so any implementation that still writes it would fail." |
| 5 | **false** | "The mapped tests mostly check that the command exists and that the file is absent in the exercised run… could slip past." |

**Run 4 is correct.** `test_check_writes_no_instruction_file_even_when_the_review_has_gaps`
invokes `check` on a review *with gaps* — exactly the case that previously wrote
the file — and asserts its absence. Run 5's verdict is not a defensible
difference of judgement; it is wrong about what the test does.

Because M5.3 is a pure deterministic reduce, that single flipped boolean is the
entire cause of the `partially supported` rating and of the run's verdict.

**What this exonerates:** mapping (identical set both runs, so not #150/#173) and
the strength reduce (a pure function). The variance is entirely in M5.2's
per-defect verdict — the sharpest localization in this corpus.

The runs also *worded* the defect differently, so defect enumeration is unstable
too: pinning verdicts is insufficient if the defect set they range over moves.

The obligation is a compound umbrella ("replace the file *with* the command
surface, *defaulting to JSON*") emitted **alongside** the individual obligations
covering each of its parts. Every constituent is strongly supported.

The obligation is also a compound umbrella emitted alongside obligations covering
each of its parts, which is a genuine #144 instance and makes the judge's job
harder. But it is **not** what produced this finding, and attributing it there
closed the question prematurely.

## Where the five rounds landed

Findings per round: 2 → 4 → 3 → 3 → 1. **Seven real gaps were found and fixed**,
including a `--json` path that deleted a file in the user's repo silently. The
tool earned its keep here even while being unreliable — which is the strongest
argument in the corpus against "fixing" #180 by damping the judge.
