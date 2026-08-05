# Judgement — #190 Gate 2, run 2 (`e8e8755`)

Verdict: **INCOMPLETE**. 9 of 29 below `strongly supported` (7 partial, 2 unsupported),
down from 14. 20 `strongly supported`.

| obligation | disposition |
|---|---|
| `use-existing-scoring-path` | **REAL.** `score_case_set` aggregates via `_all_counts` and never calls `score_case`, so the stated constraint was satisfied only in spirit. Fixed in `c5620ae`. |
| `no-live-model-calls` | **REAL.** Counting stub invocations is weaker than proving no provider is reached. Now patches `litellm.completion` to raise. Fixed in `c5620ae`. |
| `no-recorded-transcript-committed` | **REAL.** The check covered two directories; the stated defect was a transcript stored elsewhere. Now walks the whole fixture tree. Fixed in `c5620ae`. |
| six scope exclusions | **Attributed to #153**, recorded there. `do-not-set-thresholds`, `do-not-rebuild-unlisted-runs`, `do-not-change-judgement-production`, `do-not-touch-decompose-stability`, `preserve-corpus-evidence-record`, `do-not-restore-incremental-state`. |

All six exclusions show #153's documented signature: `code evidence: addressed`,
test evidence demanded and missing. The code evidence is right in each case.
Writing tests anyway moved several from `unsupported` to `partially supported`
but never to strong — **an exclusion cannot be discharged by testing**, which
makes #153's fix the only exit and means this gate cannot come back clean while
it is open.
