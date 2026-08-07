# Task
Report the span of every requirement.

## Constraints
- The span points at the exact source text, so this holds for every span:

  ```python
  assert source[span.start : span.end] == span.text
  ```
- A wrapped bullet keeps an exact span too.

## Completion expectations
- Implementation
