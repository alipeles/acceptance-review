# Judgement — #275, Gate 2, run 1

`check --task current-task.md --base bcbed91 --head 8dd9e88 --mode record`.
SHAs in `revisions.txt`.

**Not clean.** `Task completion: INCOMPLETE` — 20 of 31 obligations rated
`partially supported` on the test-evidence axis, each carrying a recommended
test. Nothing was `not_addressed`, nothing `unclear`, no open questions, and
mandate coverage was 32 of 33 (the deliberate `completion-01` decline).

**The tool completed the run**, which is the first thing this log records: the
same stage that aborted #258's Gate 2 twice returned a report, a verdict and 31
obligations here.

## The 20 recommendations, read before judging them

They split cleanly in two.

### Real, and acted on — three of them

| obligation | the defect it named |
|---|---|
| `prescriptions-for-answered-criteria-are-kept` | *"the current test inputs only include one answered criterion so the defect is not exposed"* |
| `not-obtained-distinct-from-prescribed-test` | *"the mapped tests only inspect one omitted case"* |
| `deterministic-report-for-same-inputs` | *"deterministic for the tested inputs but not for other inputs with more than one recommendation"* |

All three are correct and were my mistake, not the tool's. Every omission test I
wrote carried exactly **one** answered criterion and **one** skipped one, so
"the answers survive" could not be distinguished from "the answer survives" —
and the failure this whole issue is about is about the plural: twelve answers
discarded to report a missing thirteenth. Fixed in `5f50f64`: four criteria with
two answered and two non-adjacent omissions at the stage level, three weak
obligations with two prescriptions surviving at the pipeline level, and two
prescriptions in the determinism run.

### Unfalsifiable — the other 17

The remaining surviving defects are all one shape:

- *"correctly marks the tested omission case indeterminate, but mishandles a
  different omitted criterion elsewhere"*
- *"includes the required wording for the tested omission case, but not for some
  other omitted-criterion scenario"*
- *"rejects unasked criteria in general, but the specific test input is
  accidentally treated as asked"* — a hypothesised bug in the test's own setup
- *"the report is deterministic for the tested inputs but not for other inputs"*

None of these is a defect a test can kill. They are restatements of "your test
only covers what it covers", and under `strength.py`'s `caught == total` rule
(#252) a single unkillable entry in the enumeration caps the rating at
`partially supported` forever. #252 owns the permissive direction of that
mechanism — a lazily enumerated defect list buying `strongly_supported`; this run
is the strict direction of the same arithmetic, and the two are the same defect
seen from opposite ends. Queued as a comment on #252.

Also visible, and already filed: several recommendations prescribe the test the
same run cites as that obligation's evidence — #250, in this run's obligation 1
(`prescribing-stage-returns-rather-than-raises-on-omission`, whose recommendation
describes the test at line 1.1 of its own block).

## Unrequested changes — 7, one `risky`

All seven are about the same design decision: `recommend_tests` returns a
`RecommendationResult` instead of a `list[TestRecommendation]`, and `Review`,
`report.py` and `recommendation.py` were widened to carry the new record. The
`risky` disposition landed on the signature change alone.

Correct observation, and it is a decision I made rather than one the mandate
demanded. It is not separable: the mandate requires the stage's result to
distinguish a prescription from a prescription that was not obtained, and a bare
list cannot carry the second. The alternative — an out-parameter, or a sentinel
`TestRecommendation` with blank §9.5 fields — is the shape the not-obtained
record exists to avoid. Reported at the gate rather than changed.

In run 2 the same change came back as one `in_service` entry rather than seven
entries with a `risky` among them, on an identical source diff. That movement is
its own instability signal and is recorded in run 2's judgement.
