## Deliverable
an evidence-tier enum (builder-claim < static < coverage-confirmed < defect-killed < CI-confirmed) with an ordering and a rule that a tier can only be raised by the component authorized to produce it.

## Acceptance
attempting to set `defect-killed` from the static analyzer raises; ordering comparisons match §8.1.
