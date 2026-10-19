# #276 — `decompose` does not show `required_evidence` or its reason

#271 (`9269171`, fixing #266) made *"which kinds of evidence does this obligation require"* a
decomposition-time judgement, and the dogfooding procedure now requires reading
the stated reason at Gate 1 — a wrong *"no test is owed here"* is the false green
the design is most exposed to, and the reason is the only thing a reader can
argue with.

`acceptance decompose` prints the requirement, the obligation id, its
`type/derivation` and its restated text. It does not print `required_evidence`,
`required_evidence_reason` or `satisfied_by_absence`. Checking them means
re-running with `--json` and parsing it by hand, which is what #258's Gate 1 run
3 had to do (`dogfood-logs/258-gate1-run3/`).

## Where

`src/acceptance/cli.py:340-381`

## Deliverable

Append the value to the existing bracket — `[test_demand/explicit, tests_only]` —
and print the reason under the restated text when one is given, the way
`report.py` already does for the rendered report. Only obligations that departed
from the `code_and_tests` default carry a reason, so on a typical task file this
adds a handful of lines.

## Acceptance

- `decompose`'s text output shows each obligation's `required_evidence`.
- Where an obligation carries a `required_evidence_reason`, the output shows it.
- An obligation that is `satisfied_by_absence` is distinguishable in the output.
- A test asserts each of the above against a decomposition fixture.
