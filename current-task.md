# Task
Fix the disposition classifier (`classify_dispositions`, `coverage/disposition.py`, M3.5.3) so it stops calling a load-bearing cross-file rename `separable`. Surfaced dogfooding M5.4 (#28): `parse_test_function` was promoted from a private helper in `extraction.py` to public, in the same diff as `weak_patterns.py` adding `from acceptance.evidence.extraction import parse_test_function`. `acceptance classify` flagged the rename as an unrequested change and called it `separable`, recommending it be split into its own PR — wrong, since reverting the rename would break the import the same diff depends on.

## Constraints
- The removability litmus's deterministic fast-path already checks coverage-region overlap and pure-new-file-addition; it does not check whether a changed/renamed symbol is imported and used by another file changed in the SAME diff — direct structural evidence sitting in the diff, not something requiring semantic judgment.
- The model-judgment fallback also missed this case; the fix should not rely solely on sharpening the model prompt.
- This is a general, structural signal — not specific to this repo or this instance.

## Completion expectations
- Implementation
- A synthetic case: file A renames/exports a symbol; file B (changed in the same diff) imports and uses it. The rename in file A classifies `in_service`, not `separable`, without a model call (the new fast-path).
- Existing disposition tests (fast-path and model-judgment paths) are unaffected.
