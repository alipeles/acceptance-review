# Task
Unrequested-change detection emits spurious, location-less findings (diff_ref "?") whose rationale concludes the change IS requested.

## Context
Surfaced dogfooding #118. `acceptance classify` on that PR's own diff emitted this unrequested-change finding:

```
[separable] (adjacent_behavior) The new alignment logic is applied to gap, decomposition, and
mapping scoring joins, but the obligations only require those joins to be updated through the
alignment path; the exact implementation choice of remapping reviewer descriptions before
intersection is requested, so this is not unrequested.
   -> ?
```

Two defects in one finding:

1. **Self-contradictory:** the rationale literally ends *"so this is not unrequested"* — yet it was emitted AS an unrequested change. The detector (`detect_unrequested_changes`, M3.2) produced a finding it simultaneously argues is requested.
2. **No resolvable location (`-> ?`):** the finding has empty `diff_refs`. The model returned hunk labels that `resolve_refs` couldn't map to real hunks (dropped them), leaving no diff region. The CLI renders it anyway as `?`.

## Inconsistency worth noting
The benchmark path already handles case 2: `benchmark/coverage.py::_unrequested_finding` returns `None` when `change.diff_refs` is empty ("no diff location to point to means nothing a human can act on"). But the CLI path (`run_classify` -> `render_classify`) does **not** drop empty-`diff_refs` unrequested changes — it shows them with `?`. So the two consumers disagree, and the CLI surfaces location-less phantom findings the benchmark correctly suppresses.

## Deliverable / directions
- Drop (or clearly de-rank) unrequested changes with no resolvable `diff_refs` in the CLI path too — consistency with the benchmark path; a finding with no location a human can act on is noise.
- Investigate why the detector emits a change whose own rationale concludes it is requested — the M3.2 prompt says "Do not report changes that a listed obligation requires"; this is a prompt/detection soundness miss.

## Acceptance
- An unrequested change whose model-returned hunk labels don't resolve does not appear as a bare `?` finding in CLI output.
- A synthetic check that a change the model itself judges "requested" is not emitted as unrequested.
