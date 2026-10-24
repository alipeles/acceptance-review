# 414 Gate 1 run 4 — judgement

Run `0cb3e70c33b8e587`, Claude Sonnet 5.5, main afbf9b9 + task file de86192
(the same task file as run 3). It was not continued from run 3: this session
did not know runs 1–3 existed, because their commit is on `main` and not on
the branch. So it is a fresh derivation over the file run 3 passed on.

16 obligations, 0 open questions. Run 3 gave 21 obligations over the same
file. The difference is decomposition varying between fresh runs, which is
why `--continue` exists. It is not a new finding.

## Accurate
- task-01: both obligations real (512-token minimum; docs say "ignores", not "rejects").
- task-04: all four real. `check-and-decompose-call-model-directly-by-default`
  is close to `batch-setting-in-run-config-default-off`, but it carries the CLI
  wiring separately, which is worth checking.
- task-05: all four real.
- exclusion-01..04: one absence-form obligation each, as expected.

## Wrong — all three traced to my wording, not the tool
1. `pair-mapping-defect-list-in-reusable-opening` (task-02) turned my background
   clause "already places its defect list in the reusable opening" into an
   invariant. The clause was context, not a requirement.
2. `sonnet-5-5-cache-reads-occur` (task-02, inferred) widens the requirement to
   cache reads on every stage that repeats an opening. My clause "showed no
   cache reads on any stage" invited it. Only pair mapping is required.
3. `mutation-descriptor-one-call-per-defect` (task-03) turned my background
   clause "sends one call per defect" into a requirement.

## Possible tool defect, held until run 5
`region-source-in-shared-opening` and `region-source-in-reusable-opening`
(task-03) say the same thing and linking did not merge them. My two-sentence
wording may have caused it. If the duplicate survives the rewrite in run 5, it
is a duplicate-detection defect for #181 (the decomposition umbrella).

## Action
Rewrote task-02 and task-03 to state only the requirement. Run 5 continues
this run.
