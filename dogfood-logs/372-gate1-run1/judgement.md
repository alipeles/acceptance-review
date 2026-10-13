# #372 Gate 1, run 1 — judgement

Run `2f202a31d78db8e1`. 9 requirements, 25 obligations, no open questions.

**Verdict: not accurate. Two real requirements produced no obligation.**

## Tool defects

- **Two Task bullets unread.** The bullets naming the two label sources (BugsInPy
  fixed-operator mutants; the #45 audit edits judged to inject their defect) are
  listed under `NOT READ AS ANY REQUIREMENT`. Cause, verified:
  `task_file.py::_list_target` has no branch for the Task section, so a list
  under `# Task` goes to `unclaimed`. Queued as a filing under #181
  (decomposition) in `docs/DEFERRED.md`, 2026-10-05.
- **`implementation-hunk-the-defect-was-injected-into` typed `human_review`.**
  It is a record field, automatable. Known: #196 (automatable obligations typed
  `human_review`). Not a pause: the flag is the tool's error, not a question
  needing a person.
- **`case-records-source` and `separate-scoring-by-source` unmerged.** The
  same property, from one requirement. Known: #273 / #277 (restating
  obligations not reconciled).
- `test-source`, `describe-defect`, `exact-edit-applied` typed `docs_config`.
  These are data fields, not documentation. Minor; in #181's typing family.

## My wording

- **`survivors-include-no-behaviour-change-edits`** is an invented obligation
  that came from a background sentence ("Survivors include edits that change no
  behaviour"). Fair; rewrite it as the reason for the spot-check, not a
  statement of fact. Same family as #212 (background becomes an obligation).

## Accurate

The other obligations match the task: each case's six fields, the
sandbox, setting aside tests that are already red, the survivor sample and its
report, the 200 / 30% / 30% counts, never committing BugsInPy-derived cases,
rebuilding from pinned ids, and the typed loader. The scope exclusions are
reframed as prohibitions, which is expected.

## Open questions

None were raised. I expected one on where a BugsInPy mutant's "requirement
text" comes from, since BugsInPy bugs carry no requirement. Its absence is
consistent with #303 (decomposition has raised no open question since #217).
I did not file it again.
