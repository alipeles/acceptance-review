# Run 4 — prediction, written before the run

Recorded in advance because run 2's judgement noted that a reconstructed
expectation is worth less than a recorded one. This is the first run of this
corpus with a genuine pre-registration.

The edit under test brings the **decompose stage into the measured surface**
(human decision), adds a constraint that cross-run obligation comparison uses
`benchmark/alignment.py::align_obligations`, and widens the perturbation figure
from "obligations whose evidence class changed" to "watched judgements that
changed".

## Predictions

1. **Obligation count rises to roughly 22–23**, from 20. Two genuinely new
   requirements were added (report decomposition variance; compare obligations
   semantically), plus the widened perturbation wording.
2. **Two specific new obligations appear**: one for reporting how the
   decomposition varies across runs, one for semantic cross-run comparison via
   `align_obligations`.
3. **Open questions: 0**, if run 3's zero was earned. **Non-zero — most likely
   `oq-output-format` returning — if run 3's clean sheet was the instability this
   corpus documents.** This is the discriminating prediction, and it is the
   reason this run is worth recording: run 3 dropped two questions for no reason
   traceable to the edit, so their reappearance under an unrelated edit is the
   confirming observation.
4. **Risk of an invented obligation.** The new Task-prose paragraph ("A Gate 1 run
   of this very task showed the decompose stage dropping two open questions…") is
   *motivation*, not a requirement. If an obligation appears demanding that the
   harness reproduce or fix that specific dropped-question behaviour, that is the
   decomposer converting narrative into a requirement — a finding, not a pass.

## What each outcome would mean

| outcome | reading |
|---|---|
| 0 questions, 2 expected new obligations, nothing invented | clean; run 3's zero looks earned after all; weakens the run-3 finding |
| `oq-output-format` returns | run 3's drop was instability; strengthens the run-3 finding materially |
| an obligation invented from the motivation paragraph | separate decomposer defect (narrative → requirement); file against #181 |
