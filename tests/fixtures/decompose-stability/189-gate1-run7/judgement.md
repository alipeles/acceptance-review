# Run 7 — judgement

*After making the default run count concrete ("a small number" → "three").
33 obligations, 1 open question.*

## Verdict at the time

**Gate 1 passed.** The most complete breakdown of the series: every task-file
section represented, nothing invented, one open question triaged to no-action.

Two findings recorded and attributed to the tool rather than fixed at source.
Iteration stopped here deliberately — see *Why this run is the last*.

## Finding 1 — run 6 dropped a scope exclusion, and run 7 recovers it

| run | obligations covering *"interpreting the figures, setting a threshold, or reducing the variance"* |
|---|---|
| 5 | 1 (`report-only-no-acceptance-decision`) |
| 6 | **0** |
| 7 | 3 (`no-acceptability-threshold`, `no-threshold-or-rating`, `no-variance-reduction`) |

Verified by grep across all three outputs. A whole scope exclusion vanished in
run 6 and returned in run 7, with the task file's Scope exclusions section
**unchanged across both** — the run 6 → 7 edit touches only the default run count,
in Completion expectations.

This is a **content difference** in the human's taxonomy: a requirement present in
one run and absent in another. It is the third instance in this corpus, after the
run 4 compound-bullet truncation and the run 3–5 open-question oscillation, and it
is the cleanest of the three, because the source text is unchanged and the loss is
total rather than partial.

Run 6's judgement has been corrected in place; the original wording is preserved
above the correction.

## Finding 2 — prohibitions are typed `human_review`

All three recovered obligations came back `[human_review/explicit]`:

- `no-acceptability-threshold` — *Leave acceptability decisions to the task that changes the judge.*
- `no-threshold-or-rating` — *Keep threshold-setting and rating interpretation out of the harness.*
- `no-variance-reduction` — *Preserve the measured variance without attempting to reduce it.*

**All three are wrong, and in a way that matters.** These are prohibitions on the
harness's own behaviour, and every one is statically checkable: you can test that
the harness emits no threshold, and that it does not reduce variance. None requires
a human to look at anything. But `human_review` is a mandatory Gate 2 pause under
CLAUDE.md, so as typed they would block a clean Gate 2 **by construction**, forever,
no matter what code is written.

The likely cause is surface vocabulary: the obligations mention acceptability,
thresholds and interpretation — human-judgement words — even though the
requirement is *that the harness must not do those things*. A prohibition on
exercising judgement is being read as a requirement for judgement.

**Interaction with #162 Part 2.** Part 2 proposes moving human escalation onto
`ObligationType`, with `HUMAN_REVIEW` among the escalating types. This corpus now
shows that axis producing false positives (here) as well as being unstable across
runs (`record-run-provenance`: `invariant` → `docs_config` → `functional` across
runs 3–7). Part 2 is still the right direction — an evidence-axis value is a worse
key than a type — but it inherits a defect it does not fix.

**Disposition: attributed to the tool, recorded against #193.** Not fixed at
source: the Scope exclusions text is correct and clear, and rewording it to dodge a
mistyping would be shaping the input to flatter the tool.

## The `report-format` question, final state

| run | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| present? | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ |

Seven runs, four transitions, task text on the subject unchanged throughout
(it says nothing about output format in any version). The runs-of-two pattern
noted in run 6 **does not hold** — run 7 breaks it after two. Recorded because run
6 explicitly warned against reading a period into a small sample, and one run later
the pattern dissolved. The warning was worth writing.

## Open-question triage

| question | case | disposition |
|---|---|---|
| `perturbation-default-value` — what default when the caller supplies none? | implementation detail | **No action.** Mine to design; the task file says only that a default exists. |

## Duplicates

`no-acceptability-threshold` / `no-threshold-or-rating` are the same requirement
from two sentences (Task prose + Scope exclusions). #144, unchanged.

## Why this run is the last

Seven decompose runs is already past the point of diminishing returns, and each
one costs a live call. Gate 1's bar is an accurate breakdown with every open
question triaged, and run 7 clears it. The two findings above are **tool defects
with a tracked backlog item**, which CLAUDE.md lists as a permitted disposition —
not blockers to be iterated away. Continuing to re-run in the hope of a prettier
breakdown would be tuning the input against a judge this corpus has just
demonstrated to be unstable, which is both futile and the exact anti-pattern the
project warns about.
