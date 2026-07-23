# Task
Per criterion, judge whether the mapped tests would fail under a named plausible defect — considering whether inputs distinguish competing interpretations, whether boundaries and negatives exist, and whether assertions target the required result. The output includes the named plausible defect.

## Constraints
- Inputs are M5.1's per-test extraction and the §9.3 central question.
- This is a semantic judgment (a static prediction of which plausible defects a mapped test would catch), so it is a schema-constrained model call recorded for replay, with no live calls in capability tests.
- A criterion is discriminating when its mapped tests catch at least one plausible defect, non-discriminating when every plausible defect survives.
- Only criteria that have a mapped test are judged here; a criterion with no mapped test is unsupported and classified later.

## Completion expectations
- Implementation
- Unit tests: a non-discriminating input is judged non-discriminating with the specific reason; a genuinely strong test is judged discriminating. Prompt quality is verified by a live before/after run, since injected-response tests cannot assert it.
