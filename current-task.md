# Task
For each criterion whose test evidence is missing or weak, produce a machine-readable §9.5 recommendation with the criterion, required input characteristics, boundary or negative conditions, expected output or relationship, required assertions, the plausible defect it should detect, and relevant repo conventions or fixtures. Archetype #4's shape: the daily-rate criterion's only test uses a 30-day month, where dividing by days_in_month and dividing by a hard-coded 30 give the same answer, so the recommendation must prescribe a discriminating test.

## Constraints
- Recommend a test for every obligation whose evidence class is anything short of strongly supported; an obligation with no evidence class set yet is not yet classified and is not recommended for.
- The plausible defect the recommended test must catch is the surviving defect the discrimination step already identified, not a newly invented one, so a passing added test demonstrably closes the gap rather than nominally addressing it.
- Every recommendation is structured, machine-readable data a coding agent can pick up and implement in a single iteration; "add more tests" is insufficient.
- The product recommends and never modifies code. Generation is a semantic judgment routed through the model harness, recorded for replay; no live model call in tests.

## Completion expectations
- Implementation
- Archetype #4's weak daily-rate criterion yields a recommendation with every §9.5 field populated, prescribing an input where a correct and a defective implementation differ.
- A strongly supported obligation yields no recommendation, and no model call is made when nothing is weak.
