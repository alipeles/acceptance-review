# Task

The text output of `acceptance decompose` shows, for every obligation it lists,
which kinds of evidence that obligation requires (its `required_evidence`
value), placed inside the bracket that already carries the obligation's type and
derivation, for example `[test_demand/explicit, tests_only]`. Where an
obligation carries a `required_evidence_reason`, the output prints that reason
beneath the obligation's restated text. An obligation that is
`satisfied_by_absence` is marked so a reader can tell it apart from one that is
not.

A regression test asserts each of these three things against a decomposition
fixture.

## Scope exclusions

- The `--json` output of `decompose` is unchanged.
- The rendered review report is unchanged.
