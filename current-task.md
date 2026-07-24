# Task
Feed the M5.1-M5.3 test-evidence classifications into the evidence-classification-agreement metric, so the archetype set reports a real figure.

## Constraints
- Wire test discovery, mapping, extraction, discrimination, and strength classification into the benchmark's static pipeline (classify_case), ahead of coverage classification.
- Add a field on the reviewer's Obligation for the §9.3 evidence class, populated by the strength classifier's output.
- Update the evidence-classification-agreement metric to score real matched/reported counts instead of always reporting zero reported.
- The metric must use the same semantic-alignment mechanism as the other obligation-keyed metrics, so it isn't defeated by reworded reviewer criteria.

## Completion expectations
- Implementation
- Unit tests: on an archetype, the checker's own classification of its real candidate tests agrees with ground truth and evidence_agreement reports a real, non-trivial number.
