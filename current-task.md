# Task
Expand the unrequested-change archetypes beyond #8 with three sibling fixtures — a separable extra feature, an in-service refactor, and a risky adjacent-behavior change — each with ground-truth disposition labels.

## Constraints
- Each fixture must materialize as a real two-commit git repo with a non-empty base->head diff and a pytest suite that runs with its declared intended outcome.
- Ground truth must label each unrequested change's disposition (in_service / separable / risky), backed by a plausible rationale under the removability litmus.
- The separable and in-service scenarios must be genuinely distinct: the in-service change must be load-bearing for the requested obligation (removing it breaks completion), not merely tidier.

## Completion expectations
- Fixtures (task.md, base/, head/, meta.json, labels.json) for each of the three dispositions
- Ground truth validated against the existing generic archetype test suite
