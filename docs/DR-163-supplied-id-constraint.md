# Decision Record 163 — Constraining ids to the set actually supplied

*Relates to issue #163 (delivered in `#179`, merged as `839ea47`) and issue #164.
Status: **implemented**, all six model stages. Track: checker. Stage: 1.*

---

## Context — a valid answer to a different question

Every stage that asks the model to echo back an id we supplied typed that id as
a free-form `str`. Nothing in the schema said "this must be one of the ids I just
gave you", so **an id that does not exist was valid output**.

Observed dogfooding #36: the mapping call returned 96 entries; 80 had empty
obligation lists and the other 16 named `show-fields`, `line-total`,
`money-format`, `returns-in-parens` — obligations belonging to the **archetype-1
fixture**, which appears in the body of `tests/benchmark/test_coverage.py`, one
of the candidate test files pasted into the prompt. The prompt is 96% test
source, so it is full of obligation-id-shaped strings.

The model was not judging our 17 obligations and finding no match. It was
answering about obligations it had read out of the test sources. `mapping.py`
then filtered those foreign ids out **silently**, leaving a result
indistinguishable from "no test evidences any obligation" — so the review told
the reader their change was untested when the truth was that the reviewer had
answered a different question.

Four of the six id-echoing stages discarded a wrong answer without trace. Two
(`classify.py`, `open_questions.py`) already recorded a *missing* answer
honestly; none constrained the id.

---

## Decision 1 — the constraint goes in the schema, built per call

Each id-bearing response field becomes an **enum of the ids that call actually
supplied**, so a foreign id is not merely detected but **unrepresentable**: under
constrained decoding the tokens are not available.

This is the #158 lesson applied one level further. There we learned that enum
values must be *inline* rather than behind a `$ref` for the model to honour them,
and that the representation changed the answers. Same principle: encode the
constraint where the model is bound by it, not in the prose.

Built per call, never from a fixed list — so a partitioned stage constrains each
call to its own partition (mapping supplies that batch's tests, but every
obligation, because every batch judges all of them).

## Decision 2 — a local per-item check as well, and it is not redundant

`supplied_ids.scan` re-checks every returned id against the supplied set.

The two mechanisms answer different questions:

| | mechanism | purpose | binds |
|---|---|---|---|
| Schema enum, per call | `constrain` | **prevention** | providers honouring strict mode |
| Per-item local check | `scan` | **detection** | always |

The harness routes through LiteLLM with `drop_params=True` *specifically* so the
model can be swapped to compare quality and cost (M0.4) — Anthropic refuses
`seed` outright, OpenAI accepts it. A constraint that binds only one provider is
not a constraint on the tool. The local check is what makes the guarantee
provider-independent.

It also covers a case the schema cannot: a field whose supplied set is **empty**
is left unconstrained, because `Literal[]` is not a type. There the guarantee
degrades to detection rather than vanishing.

## Decision 3 — `parse_as`: what we ask for is not what we accept

**This is the non-obvious one.**

`ModelClient._validate` parses the *whole response object*. Validating against
the constrained model would therefore turn one bad id in a 96-entry mapping batch
into a `SchemaValidationError` that aborts the entire review — discarding 95
usable judgments to punish one.

So `complete()` gained a seam: `response_model` is what we **ask** for (it goes
into the request and is hashed into the request key), `parse_as` is what we
**accept**. They differ only where a stage constrains ids.

Two traps found while building it, both worth recording:

- **`_persist_live_call` re-validated with the constrained model**, silently
  defeating the seam on the RECORD path while REPLAY worked correctly. Gating on
  the constraint would also refuse to *record* the very replies that prove a
  provider ignores it. The gate is now `parse_as`.
- **Pydantic renders a one-value `Literal` as `const`, not `enum`.** Providers
  honour `enum` under strict decoding. Without normalising (`_const_to_enum` in
  `inline_schema_refs`), the one case where the constraint silently stopped
  binding would be a call supplying exactly one id — a one-obligation task, or a
  final partition. A defect that appears only at the boundary.

## Decision 4 — an unusable answer is `indeterminate`, never a negative

An obligation whose judgment could not be honoured is recorded as
`indeterminate`, **not** as `unmapped` / lacking evidence.

"No test evidences this obligation" is a substantive claim, and we forfeit it
when the answer that would have mapped the obligation is exactly the one we could
not read. Every batch judges every obligation, so a single unusable answer taints
the whole unmapped set for that run.

This required **no new type**: `evidence_class == "indeterminate"` already routes
through `verdict.py` to `UNABLE_TO_DETERMINE` and lists the obligation as an
escalation candidate. A review that could not read part of its own reviewer
cannot come back clean — the "uncertainty is first-class" invariant applied to
the tool's own machinery.

The finding is typed `unusable_answer` and is **not advisory**. An unrequested
change or a declaration overclaim is about the delivered work and leaves the
verdict alone; this is about the review failing to answer a question it asked,
which is precisely what a reader must not mistake for a clean result.

---

## Rejected

**Hard-fail the run on any foreign id.** Loudest possible signal, and it can never
be mistaken for a substantive answer. Rejected because one bad id out of ~1,600
judgments aborts an entire review, and a provider with weak strict-mode support
would make the tool unusable against it — defeating the provider-agnosticism the
harness exists to provide.

**Strict parse with per-batch recovery.** Catch the error at the batch boundary
and record the whole batch as unanswered. Rejected as too coarse: it discards the
good judgments that merely shared a batch with the bad one.

**Constraining `_DecomposedObligation.id`.** The model *invents* these; there is
no supplied set to constrain them to. Correct as-is.

**Verifying `source_quote` appears in the task text.** Same family — a claim about
supplied input we could verify — but a different check: the quote must appear in
a text, not belong to a set. Deferred, not rejected.

**Detecting empty answers.** A model returning an empty list is schema-valid and
indistinguishable from a correct "no test covers this". That is a judgment the
reviewer cannot audit. No fix attempted, and none proposed.

---

## Related

- **#158** — enum values must be inline, not behind `$ref`; the representation
  changes the answer. This decision is that lesson one level further.
- **#164** / `DR-164` — request partitioning. Sequenced first, deliberately:
  constrained decoding stops the model answering the *wrong* question, but not
  answering *thinly* under a call carrying 1,632 judgments. Re-recording the
  corpus once, after the prompt rework, was cheaper than twice.
- **#183** — evidence judgement umbrella. Constraining ids removes one source of
  unreliable output; it does not address whether the judgment itself is stable.
