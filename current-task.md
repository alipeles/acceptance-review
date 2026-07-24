# Task
Fix the disposition classifier (`classify_dispositions`, `coverage/disposition.py`, M3.5.3) so it stops labeling a change's own doc/comment updates as `separable`. Surfaced dogfooding #118: `acceptance classify` flagged a docstring update that accompanies an in-service code change as `separable`, with a recommendation to "split into its own PR" — actively bad advice, since updating documentation to describe the change you are making is in service of that change, not a distinct unit of work.

## Constraints
- `classify_dispositions` treats a change as `separable` when it isn't load-bearing for an obligation's coverage and looks self-contained; a docstring/comment change co-located with and describing a code change that IS load-bearing should inherit `in_service` instead.
- `separable` should mean "a coherent DISTINCT unit of work" — a docstring for the very change under review is not distinct work.
- Prefer a deterministic structural fast-path over a new model call where the signal is checkable without semantic judgment, consistent with the classifier's existing hybrid design (structural fast-paths for the unambiguous cases, model judgment for the genuinely ambiguous rest).

## Completion expectations
- Implementation
- A synthetic case where a PR edits a function AND updates its docstring/comments to match classifies the doc change as `in_service`, not `separable` with a "split into its own PR" recommendation.
