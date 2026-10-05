# 338 Gate 1 run 2 — judgement

Run id 8d4503eee4e98ff8, continuing 450939fd50f3f9d9. 7 carried, 3 revised.

## Run 1's wording fixes held
task-03's restated "no privileged path" obligation and task-04's three-way
restatement are gone.

## Real (my wording) — fixed in run 3
- task-03 now enumerates the four checks I listed as separate obligations
  beside an umbrella `same-checks-as-any-other-candidate`, and `text-checks`
  reads "The text checks are satisfied" — wrong meaning: an agent candidate
  that fails a check is set aside, not required to pass. The list was detail the
  code already defines. Replaced with "every check any other candidate goes
  through, before and after it is run against the tests".

## Tool defects — already tracked
- exclusion-01 still inverted after rewording ("The change adds an adapter for
  Codex ..."): #310. No further rewording; the wording is plain.
- `set-aside-when-edit-is-not-contiguous-within-region` typed `human_review`;
  `test-files-removed` typed `docs_config`: #196.
