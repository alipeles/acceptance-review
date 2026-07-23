# Task
Classify each unrequested change's disposition (in_service / separable / risky) via the removability litmus, and emit a split recommendation for separable changes.

## Constraints
- Apply the removability litmus — would the task still be complete if this change were removed? — reusing the M3.1 coverage output: a change whose region is load-bearing for an obligation is in_service.
- Reconcile the two axes: a change whose region is already addressed-coverage for an obligation must classify as in_service, never a bare unrequested flag.
- Use a hybrid: deterministic fast-paths for the unambiguous cases, a schema-constrained model judgment (recorded for replay) for the ambiguous modifies-existing cases.
- Consume the strict/loose scope-expansion policy: strict treats adjacent-behavior edits as risky, loose as separable.
- Emit an advisory "consider splitting into its own PR / backlog item" recommendation for separable changes.

## Completion expectations
- Implementation
- Unit tests: a load-bearing change → in_service (no model call); a planted separable feature → separable with the split recommendation; a modifies-existing change escalates to the model.
