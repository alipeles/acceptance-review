# Judgement — #190 Gate 2, run 3 (`c5620ae`)

Verdict: **NEEDS-CLARIFICATION**. **3** obligations `strongly supported`, down
from 20 — on a diff over run 2 that only **added tests**.

## The isolation

| | run 2 | run 3 |
|---|---|---|
| `strongly supported` | 20 | **3** |
| obligations with ≥1 mapped test | 27/29 | 25/29 |
| total test-evidence links | 36 | **40** |
| defects enumerated | 55 | 51 |
| avg defects per obligation | **2.04** | **2.04** |
| `would_be_caught` | 48/55 (87%) | **29/51 (57%)** |

Mapping did not collapse — there were *more* evidence links in the worse round.
Defect enumeration did not move: 2.04 both rounds, which was my hypothesis and it
was wrong. The entire swing is M5.2's per-defect verdict with enumeration held
constant — a cleaner isolation than the corpus's own run-5 case, where
enumeration moved too. Recorded against **#191**.

## What this does NOT establish

**Not that round 3 is wrong.** The corpus's central finding is that in 7 of 8
unstable obligations the LOW rating was correct, and DR-180 names the inference to
avoid: *the diff was additive, added tests cannot weaken evidence, therefore the
fall is external.* Both premises true, conclusion false. These lower ratings may
be right and rounds 1–2 may have been issuing unearned STRONGs on my own tests.

The figures establish **where** the variance lives, not which end of it is correct.

## Open question 1 regressed

`which-corpus-files-to-add` went `[resolved]` in run 2 → `[open]` in run 3, with
the diff unchanged in that respect. Same #178 question, now oscillating on the
resolution axis as well as the wording axis. Recorded against #178.
