# Task
Fix unrequested-change detection (`detect_unrequested_changes`, M3.2) so it no longer emits spurious, location-less findings (diff_ref "?") whose rationale concludes the change IS requested. Surfaced dogfooding #118: `acceptance classify` on that PR's own diff emitted an unrequested-change finding whose rationale ended "...so this is not unrequested" — yet it was still reported as unrequested — with empty `diff_refs`, rendered by the CLI as a bare `?`.

## Constraints
- The benchmark path already drops empty-`diff_refs` unrequested changes (`benchmark/coverage.py::_unrequested_finding` returns `None`); the CLI path (`run_classify` -> `render_classify`) must behave consistently — a finding with no location a human can act on is noise.
- The M3.2 prompt already says "Do not report changes that a listed obligation requires" — the fix must address why the detector still emitted a change whose own rationale concludes it is requested, not just paper over the symptom.
- Prefer fixing this once at the source (`detect_unrequested_changes`) over duplicating a drop-check in every consumer.

## Completion expectations
- Implementation
- An unrequested change whose model-returned hunk labels don't resolve does not appear as a bare `?` finding in CLI output.
- A synthetic check that a change the model itself judges "requested" is not emitted as unrequested.
