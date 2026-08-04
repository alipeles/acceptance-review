# Run 6 — prediction, written before the run

Second pre-registration (see run 4). The edit adds the **content vs shape**
classification of differences (human decision): four new non-compound bullets
plus a rationale paragraph in the Task prose.

## Predictions

1. **Obligation count rises to roughly 28**, from 24 — four new bullets, each
   deliberately written as a single non-compound sentence after run 4's finding
   that a compound bullet lost half its content.
2. **The two definition bullets are the risk.** "A content difference is …" and
   "A shape difference is …" are *definitions*, not requirements. If the
   decomposer emits them as obligations, downstream stages will try to find test
   evidence for a definition, which cannot succeed. Watch for this — it is the
   inverse of run 4's failure: there, prose was correctly ignored; here, prose
   that looks like a requirement may be wrongly promoted.
3. **Open questions: unknown, and that is the point.** `report-format` has now
   oscillated present/present/absent/absent/present. If it is absent here the
   oscillation continues; if present, it persists two runs running for the first
   time since run 2. Either outcome is data. **No prediction offered** — a
   prediction I could satisfy either way is worthless.
4. **The Task-prose rationale paragraph should NOT produce obligations.** It
   explains why the classification matters and imposes no requirement beyond the
   four bullets. Run 4 established that this decomposer does not generally
   promote motivation prose, so an obligation derived from it would be a
   regression.

## What each outcome would mean

| outcome | reading |
|---|---|
| ~28 obligations, definitions not promoted, nothing from the rationale | clean |
| definitions promoted to obligations | task-file fix: restate the definitions as constraints on the report rather than as standalone bullets |
| rationale paragraph promoted | new finding for #193 — narrative → requirement |
