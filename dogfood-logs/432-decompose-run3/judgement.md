# 432 decompose run 3 — judgement

Data for #440 (evaluating the decomposition redesign on real mandates), per the
M11 block in `CLAUDE.md`. Not a gate.

**Input:** `mandate.md`, the body of #432 exactly as filed, the same input as
`dogfood-logs/432-decompose-run1/`. Run on branch `437-synthesis` (claims and
synthesis, uncommitted), 2026-11-02, live, `anthropic/claude-sonnet-5-5`,
$0.0518.

**Output:** 16 claims, 12 units set aside as background, 12 synthesized
obligations. The per-requirement path still finds no requirement (the headings
are unrecognised), so it prints no obligations, as in run 1.

**Against #437's Acceptance, as the owner extended it on 2026-11-02:** the four
`## Acceptance` bullets are claims 25 to 28 (lines 34 to 37), and every one is
cited by at least one obligation. Met. Run 1 found nothing at all.

**Judgement, item by item:**

- Real criteria: the provider interface, the native Anthropic adapter, the
  LiteLLM general adapter, capability declarations and the client reading them,
  usage and cost taken from Anthropic's response, the corpus re-recorded once and
  noted where figures are compared.
- Good splits: "on the official SDK" became a separate constraint
  (`anthropic-adapter-uses-official-sdk`), and `llm.provider_of` became a
  constraint beside the interface — the "one claim, two obligations" behaviour
  #437 asks for.
- Questionable: `no-native-adapter-for-other-providers` reads a policy sentence
  ("a native adapter is written only for a provider used heavily enough") as a
  scope exclusion. Defensible, but the mandate does not exclude it outright.
- Questionable: `general-litellm-adapter` cites claim-03, which is motivation
  from "The problem" section. Harmless as a citation; the unit classifier fed it.
- `decouple-tests-from-litellm-internals` is entailed from the problem
  statement; it is the kind of item pruning (#438) should judge.
- One claim uncited: "The general adapter alone changes nothing that is recorded
  today." Correctly not an obligation.
