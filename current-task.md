# Task
Fix the seed half of the documented determinism strategy. The configuration module states that Stage 1 achieves determinism through a fixed seed and temperature plus cached transcripts, but the seed defaults to nothing and no run ever sets one, so only half the strategy is in force. Give runs a fixed seed by default, send it with every model request, and record it alongside the other determinism controls.

## Constraints
- The seed must reach the model request, not merely sit in configuration; a seed that is configured but never sent changes nothing.
- The seed must be recorded with the review's provenance, so a reader can tell which determinism controls produced a given review.
- The seed must be part of the hashed request, so changing a determinism control invalidates recorded transcripts and forces re-verification rather than replaying responses produced under different settings.
- The recorded prompt corpus must be produced under the same determinism controls the tool actually runs with, in the same way it already must use the same model; corpus clients should take those controls from one source of truth rather than restating them.
- Re-record the committed corpus under the new controls, since the change invalidates the existing recordings by design.

## Scope exclusions
- Making requests finer-grained, so that changing one file no longer re-judges every obligation, is the larger structural fix and is out of scope here.

## Completion expectations
- Implementation
- A run carries a fixed seed by default, and that seed appears both in the model request and in the recorded provenance.
- Two runs whose seeds differ produce different request hashes.
- Every committed recording carries the production model, seed, and temperature.
