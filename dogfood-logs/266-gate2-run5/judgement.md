# Judgement — #266 Gate 2, run 5

`check --task current-task.md --base 265bfac --head ffae0ae`. First run after the
mapping-precision fix.

## NOT CLEAN — but by one obligation, and it is a known defect

Verdict `INCOMPLETE`. One obligation short.

| | run 4 | run 5 |
|---|---|---|
| strongly supported | 19 | **39** |
| partially supported | 21 | **0** |
| unsupported | 0 | 1 |
| not required (test) | 5 | 5 |

## The precision fix worked

Run 4 mapped a mean of 5.0 tests per obligation with a maximum of 21, and 21
obligations rated `partially supported` — evidence present but not
discriminating, because much of it was never about the obligation. Naming the
per-obligation bar (*would this test FAIL if that obligation's behavior were
missing?*) and requiring every returned id to pass it independently took that to
zero.

Nothing else changed between the two runs. The 21-to-0 movement is attributable
to the prompt edit alone.

## The one that remains is #245, in its residual form

`completion-12` — *"A test asserts that a review of a change modifying only
configuration files produces a report"* — is `unsupported` with no mapped test.

The test exists and the same report cites it, one obligation over:

```
33. A review of a change that modifies only configuration files produces a
    report.                                        [constraint-16]
    test evidence: strongly supported
      33.4  tests/test_unevidenceable_obligations.py::test_a_config_only_change_produces_a_report
```

The constraint took the test; its completion twin got nothing. That is exactly
#245, and it is now the single surviving instance where run 1 had nine. Every
other twin pair in this mandate — and there are seventeen — was mapped to both
halves.

Attributed to #245. Nothing to fix here: the test exists, discriminates, and is
named in the same report.

## The tautology experiment, carried forward from run 4

`constraint-03` is deliberately unfalsifiable and was kept on the human's
instruction. In run 5 it is `strongly supported`, where run 4 rated it
`partially supported` and prescribed a test against an invented implementation
("two redundant internal flags"). So the finding stands but its shape moved: the
tool does not recognise a tautological obligation, and now simply accepts it.
Filed separately.

## Disposition

**Gate 2 fails on one obligation**, attributed to #245 with the evidence above.
Not fixable inside #266 — the test it asks for already exists.
