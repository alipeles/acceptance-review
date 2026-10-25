# 310 Gate 2 run 2 — judgement: NOT CLEAN

Run `c2c01d78f9d16af2`, head 237848f (adds the merge rules and a task-file sentence for them), Sonnet 5.5. Cost $1.13.
Verdict INCOMPLETE.

## Partially addressed (code evidence)
Coverage rationales, from the recorded `_Coverage` answer:
- `scope-exclusion-bullets-become-absence-obligations`: "the wording remains up to
  the model … it does not enforce that the obligation text is in absence form."
- `scope-exclusion-with-explanatory-clause-yields-absence-obligation`: "This is
  prompt guidance only … the effect is unproven."
- `scope-exclusion-same-evidence-same-status`: "It is still a model judgement, so
  consistency is not enforced in code."
All three are TRUE and are the two findings the owner accepted as design after
run 1 (description wording left to the model; status consistency left to the
model). Run 1 rated the same, unchanged code `addressed` and put these under
"already present … needs human review"; run 2 moved them onto the coverage
axis. Same code, different coverage status across runs: worth noting as
instability. Owner's call on how to dispose of them (see session state).

## Unsupported
`merge-non-scope-exclusion-same-type-only`: "kills 0 of 1", no mapped test,
although `test_two_obligations_of_different_types_are_not_merged_even_if_confirmed`
was in the diff. The one enumerated defect was "a merge carried from the ledger
bypasses the guard". I believe that defect is not present (carried decisions are
looked up only for pairs `_pairs` admits, and a merge component needs every pair
confirmed), but nothing pinned it. Added
`test_a_carried_merge_of_two_types_does_not_merge_them_either`; it fails under
the old rule.

## Indeterminate
Regression-case obligation (`task-04`): #325, as in run 1.

## Unrequested
- `tests/test_pipeline_request_openings.py` (`in_service`): needed, as in run 1.
- `docs/DR-310-…` (`separable`): CLAUDE.md requires a DR when a decision is
  resolved. Not flagged in run 1.
