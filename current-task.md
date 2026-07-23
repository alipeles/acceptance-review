# Task
Add a `disposition` field to unrequested-change findings (in_service / separable / risky), and a strict/loose scope-expansion policy setting.

## Constraints
- Disposition is obligation-less by construction: it appears only on unrequested-change findings.
- The Finding invariant permits obligation-less findings only for unrequested_change (strict), expressed via a named allow-set that M6 can extend for declaration mismatches.
- The scope-expansion policy is a strict-vs-loose run setting; it is introduced now and consumed by the separability classifier (M3.5.3).

## Completion expectations
- Implementation
- Unit tests: an unrequested-change finding round-trips with a disposition and no related_obligation; the invariant rejects an obligation-less finding of any other type, an unrequested-change finding that carries a related_obligation, and a disposition on any non-unrequested finding.
