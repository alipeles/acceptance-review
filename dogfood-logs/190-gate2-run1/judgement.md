# Judgement — #190 Gate 2, run 1 (`4d05f2d`)

Verdict: **INCOMPLETE**. 14 of 29 obligations `unsupported` — no mapped test at all.

**Mapping audit first (DR-164):** 14/14 entries populated, **zero foreign ids**,
15/29 obligations reached. The 14 never mapped were exactly the 14 flagged. So
this was *not* a half-blind review — the mapping worked and the finding is real.

| disposition | obligations |
|---|---|
| **REAL, addressed** | All 14. I had built a suite that scores the judge while nothing asserted the requirements the task itself was written against — the "test the wiring, not just the function" hole. |

The five most valuable were the ones nothing covered at all: no test asserted the
README claim, that all six cases were committed, or — most importantly — that
runs 3 and 5 encode the *corrected* reading. Getting those backwards is the exact
failure the corpus exists to prevent, and nothing would have caught it.

Fixed in `e8e8755`.
