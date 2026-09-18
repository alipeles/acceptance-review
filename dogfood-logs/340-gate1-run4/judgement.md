# #340, Gate 1, run 4 — a test_demand obligation that #325 says can never be met

Run `3dfa03e43b7edb95`, continuing `23bd6200d738cd1e`. 13 requirements, 0
derived, 11 carried, 2 revised. No open questions.

## Two problems, one of them serious

**`run-project-tests` came out typed `test_demand`** — *"Run the project's tests
so the review can drop pairs."* My sentence was *"A run of the project's tests
that would let the review drop pairs is worth doing on that ground alone"*, which
is about a **decision rule**, and it was read as a demand that tests be run.

This matters more than it looks. #325, a filed defect where a `test_demand`
criterion is never enumerated for and so stays permanently indeterminate, means
this obligation cannot reach a verdict at Gate 2 no matter what is built. Left in
place it would make a clean Gate 2 unreachable for reasons unconnected to the
work. Reworded for run 5 to describe the decision rather than the run:
*"When the review decides whether running the project's tests is worth doing, it
counts the pairs that running them would let it drop."*

**`must-not-read-as-though-it-had-been` got worse on unchanged text.** Run 3
rendered it *"The review output states that the pair was not decided and does not
present it as though it had been."* Run 4, from the identical sentence carried
under `--continue`, rendered it *"The requirement must not be read as though it
had been"* — now about the requirement rather than the pair, and meaningless.
Another instance of #330 (an obligation description that refers outside itself),
already filed. Worth noting that a carried-and-revised obligation moved
**backwards** here; the sentence did not change between the two runs.

## Disposition

Both reworded for run 5. Neither queued as a new filing: the `test_demand`
typing is #325 and the pronoun loss is #330, and both are already on the backlog.
