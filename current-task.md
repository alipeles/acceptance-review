# Task

The default model becomes `anthropic/claude-sonnet-5-5`, and the summary-span
stage, which today names `openai/gpt-5.4` as its own model, runs on the default
like every other stage.

A recorded Claude run replays with no live call, and two recorded runs over the
same input produce byte-identical review state. The run still requests
temperature 0 and seed 0, and the review's provenance records that Claude
applied neither. The module documentation states that recorded transcripts,
not a seed or a temperature, are what make a Claude run reproducible.

A Claude response that does not match the stage's response schema is rejected
with the same typed error as any other provider's.

The committed prompt recordings are re-recorded against the new default, and
each prompt test's assertions hold on Claude's answers. Recordings made against
OpenAI models still replay, and the committed set keeps at least one recording
from a provider other than the default.

Which model each stage runs on is set only in `config.py`.

## Scope exclusions
- Sending offline runs through the Message Batches API.
- Changing where prompt-cache breakpoints are placed.
- Reporting spend per run.
- Re-measuring benchmark figures on Claude.
- Changing any prompt or response schema.
