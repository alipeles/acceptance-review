# Decision Record 302 — Stop naming a batch's own ids in the response schema

*Relates to issue #302 (child of #265), and narrows part of `DR-163`.
Status: **implemented**, mapping stage only. Track: checker. Stage: 1.*

**This DR was rewritten after its first draft was measured and found wrong.** The
first version adopted the fixed-slot mechanism #302 proposes and argued the trade
purely as unrepresentability-versus-detectability. It never priced the schema
itself, which turned out to be decisive. The rejected mechanism and the numbers
that killed it are kept below, because the reasoning is the useful part.

---

## Context — the response schema is in the provider's cache key

`docs/experiments/265-cache-key-scope/` measured nine live calls against
`openai/gpt-5.4-mini`, both controls behaving:

| case | schema | cached |
|---|---|---|
| identical opening, different tail, same schema and same enum | `_Mappings` | **94.6%** |
| identical opening, different tail, same schema, enum VALUES differ | `_Mappings` | **0.0%** |

Same schema name, same fields, same opening. Only the values inside a constrained
id enum move, and reuse dies.

`supplied_ids.constrain` builds that enum per call (`DR-163`, Decision 1). For a
partitioned stage the supplied ids are *that batch's*, so two batches of one stage
necessarily send two different schemas and **every batch after the first is a
cache miss by construction**. That is mapping's measured 0.7% — 461 of 464 calls
caching nothing, over a 1,729-token prefix that was eligible throughout.

## Decision 1 — remove the enum, keep the response shape

For mapping's `test_id`, `constrain` is no longer given the field. The schema
changes in exactly one place:

```json
// before, and different in every batch      // after, and identical in every batch
"test_id": {                                 "test_id": {
  "enum": ["tests/a.py::test_x", …],           "title": "Test Id",
  "title": "Test Id",                          "type": "string"
  "type": "string"                           }
}
```

Nothing else moves — not the list wrapper, not `rationale`, not the messages.
Measured over the 464 recorded mapping calls, the schema goes from a mean of
2,443 bytes to 1,552, which is **221 fewer prompt tokens per call** before any
cache hit at all.

`obligation_ids` **keeps its enum**, unchanged from `DR-163`. That set is
identical in every batch of a run, so it splits no prefix — and it is the field
#163's defect was actually about (see Decision 4).

## Decision 2 — mapping only, because it is the only stage above the floor

The provider caches a prefix only from **1,024 tokens** up. Measured within-run
shared prefixes (`docs/experiments/265-prompt-cache-baseline/`):

| stage | calls | hit % | shared prefix | above the floor? |
|---|---:|---:|---:|---|
| **mapping** | 464 | 0.7 | **1,729** | **yes** |
| decompose | 43 | 8.9 | 694 | no |
| linking (two clusters) | 77 + 62 | 0.0 | 583, 509 | no |

#302 as filed names three fields — `test_id`, `requirement_id`, `pair_id`. Only
the first is on a stage that could ever be served from cache. For decompose and
linking the prefix is below the minimum, so **a stable schema cannot produce a hit
whatever it does**; linking measured 0.0% on both clusters and would still measure
0.0%.

Both enums therefore stay. Removing them would cost a full corpus re-record and
the `_APPROVED_TRANSCRIPTS` sign-off, would put #163's guarantee on the local
check alone, and would buy nothing measurable. Ten re-records per arm put the
prompt-corpus capability tests at **2/10 failing with the decompose enum removed
against 0/10 with it kept** — Fisher exact p = 0.474, which neither demonstrates a
regression nor excludes one. An unresolved risk for zero benefit is not a trade.

The narrowing also removes the whole re-record: the seven committed fixtures are
decompose ×3, disposition ×3 and linking ×1, and **none is mapping**.

## Decision 3 — detection replaces the enum, and there was already more of it than the enum provided

`test_id` is still checked against the batch. Three mechanisms, two of which
predate the enum:

- `mapping.py:185-186` skips a test id outside this batch, and its comment
  explains why a batch may only speak for its own tests;
- `supplied_ids.scan` records a foreign id as an `UnusableAnswer` regardless of
  what the schema said — `DR-163`'s Decision 2, and the reason it is not redundant
  stands unchanged: the harness runs `drop_params=True` against providers whose
  strict-mode support differs;
- `_requirement_map` and `_batch_dispositions` do the equivalent on decompose.

The `parse_as` seam (`DR-163`, Decision 3) is untouched: `obligation_ids` is still
enum-constrained, so what we ask for still differs from what we accept.

## Decision 4 — what this gives up against #163, and why it is narrow

`DR-163` made a foreign id **unrepresentable**. For `test_id` it becomes
**detectable**. That is a real reduction, and it is confined to one field.

It is affordable because of what #163's defect actually was:

> the other 16 named `show-fields`, `line-total`, `money-format`,
> `returns-in-parens` — **obligations** belonging to the archetype-1 fixture, which
> appears in the body of `tests/benchmark/test_coverage.py`, one of the candidate
> test files pasted into the prompt.

The model was harvesting **obligation** ids out of pasted test source. That field
is `obligation_ids`, its enum is constant within a run, and this decision does not
touch it.

`test_id` has a different exposure. It is the id of the item the batch is
*iterating over* — supplied in the prompt directly above the answer, under its own
`### ` heading — and already re-checked in code independently of the schema. The
model is not selecting one from a haystack; it is copying back the label on the
section it just read.

**Measured, not assumed.** Over the recorded corpus, an unconstrained `test_id`
produced no wrong ids and no omissions at today's batch size:

| `test_id` | batch size | calls | tests asked | omitted |
|---|---|---:|---:|---:|
| no enum | 1-12 (today's) | 35 | 383 | **0** |
| no enum | 13-25 | 7 | 139 | 0 |
| no enum | 26-50 | 3 | 118 | 0 |
| no enum | 51+ (pre-`DR-164`) | 18 | 1,278 | **196 (15.3%)** |
| enum | 1-12 | 401 | 4,578 | **0** |

Omission tracks **batch size, not the enum** — every instance is in a pre-`DR-164`
unpartitioned call, which is precisely what partitioning fixed. Zero in 383 is
low-risk, not no-risk: the rule of three puts the upper bound near 0.8%, which is
why Decision 5 exists rather than being waved off.

## Decision 5 — an omitted or repeated answer is recorded, not absorbed

No schema ever prevented either of these. An enum restricts which values may
appear, never how many entries do — so both holes predate this change and neither
was guarded.

- **A batch that comes back short.** Each unanswered test is an `UnusableAnswer`.
  Left unrecorded, a skipped test is indistinguishable from a test judged to
  evidence nothing, and any obligation resting on it is reported as having no test
  at all — #163's defect shape exactly: the review calling a change untested when
  it went unreviewed.
- **A test judged twice.** Previously a silent `continue`. Two judgments either
  agree, in which case the record is harmless, or they disagree, in which case
  keeping the first without saying so is the tool choosing between answers it has
  no basis to choose between.

Linking gained both as well, and there the second was worse than silent: a
repeated `pair_id` appended a **second** `MergeDecision`, so two contradicting
verdicts resolved by whichever sorted first. Those changes stayed even though
linking's schema did not, because they are post-response code and re-key nothing.

## Decision 6 — an unusable answer taints the unmapped set, per `DR-163` Decision 4

No new machinery and no new axis. `DR-163` already decided this:

> "No test evidences this obligation" is a substantive claim, and we forfeit it
> when the answer that would have mapped the obligation is exactly the one we
> could not read. Every batch judges every obligation, so a single unusable answer
> taints the whole unmapped set for that run.

Applied here: an obligation already mapped by another judged test keeps its
evidence — the unread answer could only have added to it, and under-crediting is
the safe direction under "positive results are bounded" (§3.7). An obligation
otherwise unmapped becomes `indeterminate`. The rule is coarse, and the coarseness
is the true epistemic state: which obligations the skipped test would have named
is exactly what we failed to learn.

One fix was needed to make it legible. `pipeline.py::unusable_answer_finding`
described **every** unusable answer as an id "never supplied to that call", which
is true only of the original case — it was already wrong for #204's no-linking
rejection and is plainly wrong for an answer that never arrived.
`UnusableAnswer.reason` now reaches the description.

---

## Rejected

**Fixed generic `slot_1 … slot_N` answers — the mechanism #302 specifies.** A
fixed-property object requires exactly N answers, so omission becomes
unrepresentable, closing #275 structurally. Rejected on cost, measured two ways:

- `inline_schema_refs` resolves every `$ref` (it must — #158 showed enum values
  behind a `$ref` measurably degrade the judgement), so N slots inline **N copies**
  of the item model, obligation enum included. Mapping's schema goes from 1,233 to
  **13,055 bytes** at N=12; linking's to 27,108 at N=25.
- Two live calls with identical messages and only the schema differing confirmed
  that this is billed as ordinary input: **+11,822 schema bytes → +2,927 prompt
  tokens**.

Mapping's whole cacheable prefix is 1,729 tokens. Slots would add 2,927 to every
call — **+57% on a 5,145-token mean request** — to make 34% of it eligible. Even
if cached tokens were free the stage ends up more expensive, and they are not
free: `cache_read_input_token_cost` is 90% off, not 100%. The mechanism cannot win
on the stage it was designed for.

**Constraining `test_id` to a run-constant enum of all tests.** Keeps one schema
per run and keeps unrepresentability. Rejected: the run's full test set would be
embedded in every request, and it would let a batch answer about another batch's
test, which `mapping.py:185-186` exists to prevent and `DR-164`'s partitioning
depends on.

**Re-asking for what a short batch omitted.** Would recover the lost judgements
rather than only recording them, and — contrary to this DR's first draft — it does
**not** break replay determinism: the first call replays byte-identically, so the
retry's request is identical and replays too. Deferred rather than rejected on
principle, and deliberately not built: the measured omission rate at today's batch
size is 0 in 383, so there is nothing yet to recover. Revisit if one is ever
observed.

**Hard-failing on an unmatched id.** Rejected for `DR-163`'s reason: one bad
answer out of ~1,600 judgements must not abort a review.

---

## Unmeasured

- **Whether the corpus capability tests are simply flaky.** They failed in 4 of 25
  re-records with the decompose enum removed and 0 of 12 with it kept, and every
  re-record produces a different response despite temperature 0 and a fixed seed
  (verified by hashing three consecutive recordings). Any single committed
  recording is therefore one draw from a distribution. Worth filing in its own
  right — a future re-record can turn the corpus red for reasons unrelated to the
  change being made.
- **Whether the realised cache share matches the prediction.** The 32.1% figure
  below assumes the first batch of a run misses cold and the rest hit, at a
  measured mean of 11.8 batches per run. It needs a recorded run under #285's
  per-stage accounting to confirm, and cache lifetime is the obvious way it could
  fall short.

## Expected effect, mapping stage

|  | current | after |
|---|---:|---:|
| prompt tokens / call | 5,145 | 4,924 |
| cacheable prefix | 1,729 | 1,729 |
| realised cached share | 0.7% | 32.1% (predicted) |
| $ / 464 recorded calls | 1.78 | 1.22 |

---

## Related

- **`DR-163`** — the constraint this narrows. Decisions 2, 3 and 4 are inherited
  unchanged; Decision 1 is narrowed by one field on one stage.
- **`DR-164`** — mapping partitioning. Why the stage has sibling calls at all, why
  a batch may only speak for its own tests, and — per the table in Decision 4 —
  the actual fix for the omissions the corpus contains.
- **#158** — enum values must be inline, not behind `$ref`. Still true, still why
  `obligation_ids` binds, and the reason the slot schema could not be compacted.
- **#265** — request ordering. Not a precondition here: mapping was already
  ordered invariant-first with a prefix over the floor.
- **#275** — omitted recommendations. **Not** closed by this DR; the mechanism
  that would have closed it structurally was rejected on cost.
- **#285** — per-stage token accounting, how the effect above gets confirmed.
