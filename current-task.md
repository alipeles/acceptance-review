# Task

A review can be configured to run individual stages with a reasoning effort, the
same way it can already give an individual stage its own model. The setting maps
a stage's label to an effort value. A stage not in the map runs exactly as it
does today, and with nothing configured every request the review sends is
unchanged, so every response recorded before this change still replays.
Configuring one stage changes only that stage's requests.

A run never quietly goes without the reasoning it was configured to use. If the
provider would discard the requested effort for a stage's model, the run stops
before calling it, with an error naming the stage and the model.

For each stage, the review's provenance records the reasoning effort in force.
It also records, for each stage, the temperature and seed that actually reached
the provider for that stage's calls, rather than the ones that were asked for,
since a provider may refuse a temperature on a reasoning call. Each call's usage records its reasoning tokens, so the cost the
report shows includes them.

## Scope exclusions
- Which stages should use reasoning, and at what effort. No stage's default
  changes.
- A command-line option for the setting.
- Changing any stage's temperature.
