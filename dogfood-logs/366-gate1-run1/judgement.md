# #366 Gate 1, run 1 — judgement

Run `9ee9b55ca53a9814`, `decompose` only, $0.0890.

No open questions. Fourteen obligations over five requirements, plus one scope
exclusion that deliberately derived nothing (the command-line option).

**One real finding, attributed to my wording.** `actual-provider-temperature-and-seed`
dropped "for each stage". The sentence put "for each stage" once, ahead of two
things it governed ("the reasoning effort in force and the temperature and
seed…"), and the tool attached it only to the first. The per-stage scope matters:
temperature is dropped only on the stages that reason, so a run-level figure
cannot say which stage lost it. Rewritten to say "for each stage" for both, and
re-run as run 2 with `--continue`. Not filed as a tool defect: the sentence was
genuinely ambiguous about what the qualifier covered.

Near-duplicates accepted as real, not merged by hand:
`preserve-unchanged-requests-with-empty-config` and `replay-existing-recordings`
(the second follows from the first but is what a user cares about);
`reasoning-configured-use-is-preserved` and `stop-before-discarded-effort-call`
(the first is the general rule, the second the mechanism).
