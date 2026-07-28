# Task
The disposition classifier mislabels test-fixture updates that a source change in the same diff requires as `separable`, recommending they be split into their own PR. Wiring a capability into the shared pipeline forces existing tests to add fixture and dispatch entries; removing those entries breaks the suite, so they are load-bearing, not separable. Fix the removability litmus rather than adding another special case.

## Constraints
- The litmus must ask both whether every obligation would still be satisfied if the change were removed and whether the rest of the diff would still work — tests still passing, imports still resolving. Asking only about obligations is what let this class of misclassification recur three times.
- A change confined to test files that adds no new test function and accompanies a source change is test scaffolding the existing tests need; classify it as in service, structurally, with no model call.
- Adding a new test function is the discriminator: that may be genuinely distinct test work, so it escalates to model judgment instead of being swept into in service.
- A diff containing only test changes is ordinary test work and must still be judged rather than assumed to be scaffolding for something else.
- Classifying a change as separable must not require it to be large enough to justify its own pull request. A small opportunistic edit is still unrequested scope the reviewer should see; size governs the recommendation, not the classification.

## Completion expectations
- Implementation
- A source change accompanied by the test-fixture edits it requires classifies those edits as in service without a model call.
- A change that adds a new test function still escalates to model judgment.
- A test-only diff still escalates to model judgment.
- A small opportunistic edit to an unrelated function is still classified separable.
