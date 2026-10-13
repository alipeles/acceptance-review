# #372 Gate 1, run 2 — judgement

Run `9a1225e794aaffef`, continuing `2f202a31d78db8e1`. 9 requirements (6
carried, 3 revised), 26 obligations, no open questions, nothing unread.

What changed in the task file since run 1, and why:
- **The #45 audit source was dropped.** It was the human's decision on
  2026-10-05, because the audit edits were judged valid by a model, not a
  person. BugsInPy is now the only source, so the two-source bullet list (which
  the parser skipped, see run 1) is gone, and the sources are written as prose.
- **The survivor sentence was reworded** into a "because" clause giving the
  reason for the spot-check.

**Verdict: accurate, with one invented obligation attributed to a known
defect.**

## Tool defects

- **`survivors-not-evidence-of-weak-test`** is still an obligation. It came
  from the reason clause, "Because an edit can change no behaviour at all, some
  survivors are not evidence of a weak test." This is #212 (background becomes
  an obligation) again, after a rewrite meant to avoid it. A comment for #212
  is queued in `docs/DEFERRED.md`.
- `test-source`, `defect-text-description` and `exact-edit-applied` are typed
  `docs_config`, but they are data fields. This is in the same family as run 1.
- `implementation-hunk-present` says "the response includes". The wording is
  odd but the meaning is correct.

## Needs a person

- **`random-survivor-sample-for-human-check`** is typed `human_review`, and
  correctly: the spot-check is a person's job by design. The person is the
  human, at Gate 2.

## Accurate

- **`defect-description-matches-edit`.** It turns "can never misdescribe" into
  "the description must match the edit". I accept it as a real obligation: the
  text description has to be generated from the operator and the edit.
- **The rest.** BugsInPy fixed-operator mutants; the six case fields; the
  sandbox; setting aside tests that are already red; the survivor sample and
  its report; 200 cases with at least 30% killed and at least 30% survived;
  never committing BugsInPy-derived cases; rebuilding from pinned ids; the
  typed loader. The two scope exclusions became prohibitions, which is
  expected.

## Open questions

None. I'd still have expected one on where a mutant's "requirement text" comes
from, since a BugsInPy bug carries no requirement. #303 (decomposition raises
no open questions) already covers that absence. My proposed answer is in the
Gate 1 plan.
