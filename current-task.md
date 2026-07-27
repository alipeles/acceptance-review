# Task
Compare the builder declaration's claimed mandate, implementation, tests, exclusions, assumptions, and limitations against the obligations, the diff, and the tests; emit discrepancies as findings treated as claims, never proof. Archetype #7's shape: the declaration claims `get_user` raises `KeyError` on a missing id, but the code returns `None` and no test exercises the missing-id path — a claim matching neither the task nor the code.

## Constraints
- A declaration is a claim, not proof — every discrepancy finding carries the weakest (builder-claim) evidence tier.
- Keep two situations apart. A claim of work that was actually done (real code changed, even outside the mandate) is a separate unrequested-change concern and must not be re-flagged here. Only a claim of work that was claimed but not done — no code path and no test — is a declaration mismatch.
- A declaration mismatch is advisory and low-weight: nothing was mis-delivered in the code, so it flags the declaration as untrustworthy without blocking acceptance of the actual change. It is obligation-less by construction.
- The comparison is a semantic judgment routed through the model harness, recorded for replay; no live model call in tests.

## Completion expectations
- Implementation
- Archetype #7 produces a discrepancy finding for the claimed-but-absent error condition (declares an error condition implemented; no code path or test found).
- A truthful declaration whose claims the code and tests support produces no discrepancy finding.
