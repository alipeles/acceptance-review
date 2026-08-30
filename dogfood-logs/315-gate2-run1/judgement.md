# Judgement — #315, Gate 2, run 1

Run id `b2f43c4c61e97237`, continuing Gate 1's `3aa3bcb7cd13414e`.
Base `dc9a22a`, head `3d11408`. `--mode record`, 30 live calls, $0.25.

**Not clean.** Verdict INCOMPLETE, three obligations rated non-discriminating.
Under the suspension in `CLAUDE.md` this is a stop only for the things it
genuinely identifies, and the run is not repeated to chase a clean result.

A note on running it at all: `check` defaults to replay and refused the first
attempt, because #313's defect-enumeration stage had no recorded transcript for
this task file. Re-run with `--mode record`. `decompose` defaults the other way,
which is why Gate 1 needed no flag.

## One real defect in the change, found and fixed

`_defect_score` returned `None` — reported the figures as absent — whenever the
review recorded no defects at all, even with labelled defects present. That is
wrong in the opposite direction from the rule it was written to follow. A total
enumeration miss is a **result**, and reporting it as unmeasured makes the worst
outcome the corpus can show indistinguishable from a case the labels say nothing
about.

The enumeration stage found it three separate ways, most directly as
`labelled-share-by-classification/no-defect-score-when-no-recorded-defects`:
*"a case with labelled ways of failing but zero recorded defects produces no
per-classification share instead of a 0.0 figure"*. Correct, and mine to fix.

Fixed in `scoring.py::_defect_score`, which now separates three cases: nothing
labelled is absent, nothing recorded scores 0.0 with no model call, and no
client is absent because a match that cannot be attempted must not be reported
as a miss. Two tests added — `test_an_enumerator_that_recorded_nothing_scores_
zero_not_absent` and `test_no_client_leaves_the_figures_absent_rather_than_
scoring_every_match_a_miss`.

This is the first thing the new enumeration stage has caught in work under
review, rather than in its own tests.

## Three mapping misses — known defect, nothing new to file

`reference-set-records-failing-ways`, `recorded-failing-way-entry-fields` and
`reference-sets-load-and-validate` were each rated `unsupported` with *"(no
mapped test)"*.

I read the recommendations first, as the gate requires. All three prescribe
tests that already exist. The recommendation for `reference-set-records-failing-
ways` asks for one that loads *"a shipped archetype reference set that already
contains both obligations and defect labels"* and detects a loader that strips
them — which is `test_every_archetype_label_set_loads_and_validates`,
parametrised over all thirteen cases and asserting `labels.defects` is
non-empty. The other two are the same shape.

That is #250 and #287's failure: a recommendation restating evidence that
already exists, downstream of a mapping stage that returned nothing for the
obligation. It is the defect #312 exists to replace and #314 will replace
directly. Already known, so it is recorded here in this line and not re-filed.

## Enumerated ways of failing that are not real

Advisory only, and they change no verdict, but they should not go unremarked
since they are the new stage's first outing on real work.

- Four separate entries claim `_check_defect_integrity` may never be called —
  for instance `reject-unmatched-reference-set-entries/defect-reference-set-
  validation-not-called`. It is called from `_check_tree_integrity`, which is a
  pydantic `model_validator(mode="after")`, so it runs on every construction
  including `load_labels`. The enumerator saw the helper in the diff and not its
  single call site.
- `one-match-per-side/recorded-side-duplicates-not-rejected` says a duplicate
  match survives into *"the raw result the scorer consumes"*. The scorer consumes
  `align_defects`' return value, which is the filtered map; the raw model output
  is not reachable from outside the function.

Both are the enumerator reasoning about a hunk without its surroundings. Not
filed: #312's own design accepts that a statically enumerated way of failing may
be wrong, which is why nothing downstream of it moves a verdict yet.

## Unrequested changes: six, all `in_service`

All six are the delivery itself — the new model, the new module, the fixture
labels, the scoring wiring. The disposition is right in every case. Nothing
separable or risky, and nothing outside the task's area.

## Open questions and human review

None raised, and nothing flagged as needing non-code evidence or human review.

## Disposition

The one genuine defect is fixed. The three mapping misses are an already-known
defect and are not re-filed. Per the suspension, no second `check` run.

The labels themselves still need human review — #315 carries `human-gate`, and
that is the one part of this issue no test can settle.
