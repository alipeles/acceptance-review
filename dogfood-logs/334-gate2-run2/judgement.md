# #334 Gate 2, run 2 — judgement

Run `26c89d617a05a505`, base `fdf8254`, continuing decompose run
`d39591e2b11c3da4`. $0.6124 over 210 live calls.

**Clean by the gate's definition.** Verdict `NO-MATERIAL-GAPS`: 10 obligations
addressed and strongly supported by discriminating tests, 3 scope exclusions
confirmed from code evidence, no open questions, no recommended tests,
`Recommended next instruction: (none)`.

Both of run 1's findings are resolved. The third exclusion, reworded, is
confirmed not breached. `which-candidate-it-used` is now strongly supported, by
the two tests added for it.

The mapping step was not blind: every behavioural obligation names the tests
that support it and the enumerated defects they kill.

## Unrequested changes — eight, all `in_service`, all accepted

The per-candidate report, the `max_candidates` setting, the candidate
bookkeeping and new outcome, the `changes_nothing` helper, the widened builder
signature and the exported `LiveDescriptorBuilder`, the in-flight cap, and the
observed-call `seconds` field. Each is part of the delivery.

## The candidate loop, second real review

35 defects. 25 got an edit that passed the gates: 12 on the first candidate, 8 on
the second, 5 on the third — 13 rescued by asking again, the same as run 1. 10
ended `no_usable_edit` after three tries. The edit-building stage made 73 calls
at $0.2112, with 50.9% of prompt tokens served from the provider's cache.
