# 338 Gate 1 run 1 — judgement

Run id 450939fd50f3f9d9. 10 requirements, 24 obligations, no open questions.
Task file: ticket grade, not deliberately over-specified. `current-task.md` here
is the run-1 version, reconstructed from the requirement texts in output.log
(the file was rewritten before run 2).

## Real (my wording) — fixed in run 2
- task-03 `no-privileged-path` restates `same-checks-as-other-candidates` and
  `unverified-edit-no-privilege`. My opening sentence "Its edit gets no
  privileged path" said the paragraph twice. Sentence removed.
- task-04 three obligations for one requirement (`cannot-read-project-tests`,
  `test-files-removed`, `restriction-holds-regardless-of-agent-action`). Three
  sentences said one thing. Collapsed to one sentence.

## Tool defects — already tracked
- exclusion-01 inverted: "A Codex adapter. Only Claude Code is driven in this
  change." became `codex-adapter-only-claude-code-driven`, "The change is
  limited to adding a Codex adapter". A scope exclusion read as a positive
  obligation: #310. Wording also tightened in run 2 (tie-break: I regretted the
  fragment).
- `cannot-read-project-tests` typed `human_review`; it is enforced by a
  mechanical file filter and is automatable: #196. `test-files-removed` typed
  `docs_config`, also a wrong value; recorded against #196 (wrong type values).

## Accurate
task-01, task-02, task-05, task-06, exclusions 02-04.
