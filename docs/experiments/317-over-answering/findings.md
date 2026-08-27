# #317 — the decomposer over-answers when the batch contains the `task` paragraph

*Measured 2026-08-21 over the 1,748 recorded transcripts in `.acceptance/cache/transcripts/`.
Script: `analyse.py` in this directory. Nothing here required a live call.*

---

## Summary

1. The fourteen dispositions in `7d6f41d2…` are **not** one requirement split twelve
   ways. Entries 3–13 quote `constraint-01` … `constraint-12` verbatim, one per
   constraint, in order. The model answered for the whole Constraints section; the
   `requirement_id` enum forced every one of those entries to be labelled `task-01`.
   `session-state/317.md`'s one-paragraph diagnosis is wrong, and the merge direction
   the issue proposes repairs the wrong thing.
2. Over the corpus, **every** over-answering call has a `task-*` requirement in its
   batch: 8 of 35, against 0 of 68 without one (Fisher one-sided *p* = 0.0001).
3. **The disposition count is a symptom, not the defect.** Five of the eight
   over-answering calls returned exactly the right number of dispositions and put the
   foreign obligations inside `obligation` / `more_obligations` instead. Those calls do
   not crash — they misattribute silently.
4. Therefore the per-requirement-field response model does not fix this. Replayed
   against the eight recorded responses it changes nothing in five of them and converts
   the crash into silent misattribution in the other three.
5. A **prompt** change costs exactly what a schema change costs: `request_key` is a
   sha256 over the whole request dict, messages included (`llm.py:93-99`). There is no
   cheap prompt fix. The only free fixes are post-response.
6. There is a free post-response fix that resolves the recorded failure exactly and
   loses nothing: **an obligation whose quotation lands inside a requirement this call
   was not asked to answer for is not this call's work.**

---

## 1. What the failing response actually says

`.acceptance/cache/transcripts/7d6f41d2…json` — batch 4 of 4 (`partition` sorts by id,
so `task-01` always lands in the tail batch), asked for `exclusion-05, exclusion-06,
task-01`, 27 requirements in the registry.

| entry | requirement_id | obligation | its `source_quote` lands in |
|---|---|---|---|
| 0 | `exclusion-05` | `no-running-or-mutating-delivered-code` | exclusion-05 |
| 1 | `exclusion-06` | `no-external-expected-set-comparison` | exclusion-06 |
| 2 | `task-01` | `record-concrete-failure-ways-before-tests` (+1) | task-01 |
| 3 | `task-01` | `recorded-failure-way-fields` (+1) | **constraint-01, constraint-02** |
| 4 | `task-01` | `persist-recorded-failure-ways-unchanged-across-reload` | **constraint-03** |
| 5 | `task-01` | `record-ways-without-tests` | **constraint-04** |
| 6 | `task-01` | `checklist-guided-recording-with-exceptions` | **constraint-05** |
| 7 | `task-01` | `empty-record-set-is-valid-with-reason` | **constraint-06** |
| 8 | `task-01` | `reuse-recorded-set-only-when-…-unchanged` | **constraint-07** |
| 9 | `task-01` | `changed-criterion-text-forces-full-regeneration` | **constraint-08** |
| 10 | `task-01` | `continued-run-reuses-entitled-sets-only` | **constraint-09** |
| 11 | `task-01` | `report-when-set-was-reused` | **constraint-10** |
| 12 | `task-01` | `report-recorded-ways-of-failing` | **constraint-11** |
| 13 | `task-01` | `recording-does-not-affect-completion-or-ratings` | **constraint-12** |

One entry per constraint, in registry order, quoting each constraint's own text. The
model built the answer it wanted — a disposition per requirement it intended to answer
for — and the enum, being the only constrained field, collapsed eleven distinct labels
onto the one value it was allowed to write.

The other three batches of that run (`5040f2d5…`, `ac322f19…`, `cbfd27e6…`) each
answered cleanly, one obligation per requirement, and between them derived every
`constraint-*` and `completion-*` correctly. **The eleven smuggled obligations are
duplicates of work another batch did properly.** Nothing is lost by dropping them.

## 2. Base rate

103 batched decompose calls in the cache. "Over-answering" = at least one obligation
whose `source_quote` is not inside any requirement the call was asked for, but is
inside one it was shown as context.

| batch | calls | over-answering | rate |
|---|---:|---:|---:|
| contains a `task-*` requirement | 35 | **8** | 23% |
| contains no `task-*` requirement | 68 | **0** | 0% |

Fisher exact, one-sided: **p = 0.0001**.

Batch size is confounded (16 of the 17 batches of ≤3 contain the task paragraph,
because it sorts last), but it is not the driver: `3595816c…` over-answers at a batch
of eight, and 68 non-task batches at every size produce zero instances.

| transcript | asked | dispositions | foreign obligations |
|---|---|---:|---:|
| `3595816c` | 8 (incl. task-01) | 15 | 20 |
| `7d6f41d2` | 3 (incl. task-01) | 14 | 12 |
| `7c89d741` | task-01 alone | **1** | 11 |
| `25caf088` | task-02, task-03 | **2** | 10 |
| `41077159` | task-01 alone | **1** | 10 |
| `042b0c6d` | exclusion-06, task-01 | **2** | 5 |
| `dffe0cbb` | 5 (incl. task-01, task-02) | **5** | 5 |
| `0ef82650` | task-01 alone | **1** | 1 |

## 3. Why the count is the wrong thing to constrain

Six of the eight rows above have a disposition count equal to the number of ids asked
for. A response model with one required field per requirement id — `task_01`,
`exclusion_05`, `exclusion_06` — accepts every one of them unchanged, because the
foreign obligations travel inside `more_obligations`, which is unbounded, carrying
`source_quote`, which is free text. Neither is lockable in strict mode, and neither
would be locked by the fixed-field shape.

Replaying the fixed-field model against the eight recorded responses:

- five (`7c89d741`, `25caf088`, `41077159`, `042b0c6d`, `0ef82650`) — accepted
  unchanged, defect intact, still silent;
- three (`3595816c`, `7d6f41d2`, `dffe0cbb`) — the duplicate labels become
  unrepresentable, so the crash goes away and the same foreign obligations arrive
  inside the single surviving disposition. **The loud failure becomes a quiet one.**

That is a worse outcome than today's abort, and it costs the whole decompose transcript
corpus. `DR-302` also already priced the fixed-slot mechanism and rejected it: N slots
inline N copies of the item model (mapping went 1,233 → 13,055 bytes at N=12), billed as
ordinary input tokens.

The strict-mode premise itself is correct — `minItems`, `maxItems` and `uniqueItems` are
still on the unsupported list. It is just not the constraint that matters here.

## 4. What the silent cases cost today

`_resolve_attributions` re-files an obligation onto the requirement its quotation lands
in, when that requirement also yielded — which, for a foreign quote, it did, in its own
batch. So today's non-crashing over-answers end as **two obligations on the same
requirement, one from each batch**, differing only in wording and id.

That is the exact input to the open blocker *"unmerged twin obligations starve each
other of mapped tests"*. Worth checking whether some share of the recorded twins are
manufactured here rather than by genuine cross-section restatement: it is one query over
the linking corpus, filtering merge pairs to those whose members came from different
decompose batches.

## 5. Proposed fix, at no transcript cost

**Rule.** An obligation whose `source_quote` resolves inside a requirement that is not in
this call's `batch_ids` is dropped and recorded as an `UnusableAnswer`. `_locate_quotation`
already returns the owning `RequirementRef`; the batch ids are already in scope at the
call site (`obligations.py:922-970`). No prompt byte moves, no schema field moves, every
recorded transcript still replays. `DECOMPOSE_STAGE_LOGIC_VERSION` moves, as
`session-state/317.md` planned for.

**Then**, and only then, the duplicate-disposition question answers itself: a repeated
disposition left carrying no obligations is dropped as an unusable answer rather than
merged into its sibling. Keep the raise for dispositions that disagree on kind, which is
what #217 actually names.

**Applied to the failing run:** entries 3–13 lose every obligation and are dropped;
entry 2 survives with both of its own; batch 4 returns one disposition per asked id;
the review proceeds. The eleven dropped obligations were already derived, better, by the
batches that owned them.

**Guard.** Never empty a `yielded` disposition — `_resolve_attributions` already has
`emptied` for this. In the corpus the guard never fires: every over-answering
disposition retains at least one obligation quoting its own requirement, and the eleven
all-foreign entries in `7d6f41d2` are duplicates of an entry that keeps two.

**Why this and not the merge in the issue.** Merging entries 2–13 gives `task-01`
sixteen obligations, eleven of which `_resolve_attributions` then scatters onto
constraints that another batch already derived — manufacturing eleven twins to avoid an
abort. The obligations are real work, as the issue says, but they are not *lost* work.

## 6. For the eventual re-record, not for #317

Three things in the prompt invite the behaviour. None can be changed without orphaning
the corpus, so they belong to whichever change next pays that cost.

- **The accounting rule contradicts the batch scoping.** `_SYSTEM_PROMPT` says *"Return
  `requirement_dispositions` containing EXACTLY ONE entry for EVERY requirement id you
  were given"*. The call was given all 27. The scoping that narrows "given" to three sits
  at the very end of the SUBJECT block — after the whole 12.5 KB instruction block and
  after the full registry. On the reading the instruction block supports, the model
  complied.
- **Nothing says an obligation must quote its own requirement.** The prompt asks for
  `source_quote` as "an EXACT substring of the task text" — the task text, not the
  requirement's. The one place attribution is discussed tells the model that two
  requirements stating the same thing each get their own obligation, which is about
  duplication, not about scope.
- **The framing sentence is false for this stage.** The system message says *"You are
  given material to judge and, after it, the instructions for one specific judgement"*;
  `assemble` puts INSTRUCTIONS first and SUBJECT last, so the last block the model reads
  is the material, presented as though it were the instruction.

## 7. Input to the queued two-pass decision

`DEFERRED.md` [2026-08-20] proposes Pass B scoped to **one** requirement. Pass B is a
batch of one, and the corpus has four batches of one asking about a `task-*`
requirement: `7c89d741` (11 foreign obligations), `41077159` (10), `0ef82650` (1),
`d3a29e9d` (0). **Three of four over-answer, and the two worst instances in the whole
corpus are of exactly this shape.**

The two-pass split does not contain this defect; scoping a call to the task paragraph
alone is its most reliable trigger. Sequence the quotation-scope rule ahead of it, and
treat "Pass B answers for the requirement it was given" as something that pass must
demonstrate rather than something it inherits.

---

# Part two — fixing the cause

Section 5 is damage limitation. It belongs in the tree as instrumentation — it is how
you would measure whether a real fix worked — but it does not stop the model producing
the answer. This part is about what does.

## 8. The cause, stated precisely

The call asks a question whose correct answer is not bounded by anything the schema can
see. Two separate unboundednesses, and they need separate fixes.

**(i) Which requirement an answer is about is carried only by free text.** The batch
scope lives entirely in prose. `requirement_id` is enum'd, but an enum restricts the
*label*, not what the entry is about — which is why the model could write eleven entries
about the constraints and label all of them `task-01`. The field that actually carries
the violation is `source_quote`, and it is unconstrained.

**(ii) The Task block is the parent of every other requirement, and the registry treats
it as a peer.** `DR-216` decides that the registry's unit is a source block, not a
semantic requirement. For bullets that is exactly right and the data agrees — 0 of 68
non-task batches over-answer. For the `# Task` paragraph it is not: the Constraints and
Completion sections *are* its elaboration, so "what obligations does this paragraph
impose" has no bounded answer, and the model gives the unbounded one.

## 9. Fix A — one requirement per call, with `source_quote` as an enum of that requirement's own spans

This closes (i) structurally, on the field that carries the violation.

```python
class _DerivedObligation(StrictResponseModel):
    ...
    source_quote: Literal["<sentence 1 of this requirement>", "<sentence 2>", "<whole block>"]
```

- **An obligation about `constraint-03` becomes unrepresentable in a call about
  `task-01`.** Not detected afterwards — unsayable, which is the standard `DR-163` set
  and `#217` met.
- **It dissolves the strict-mode problem rather than working around it.** "Exactly one
  disposition per id" needs no array-length constraint once a call answers for one
  requirement: one requirement, one required field. `minItems` is genuinely unsupported
  (still on the current unsupported list), and with this shape it is also unneeded.
- **Measured schema cost** (`schema_cost.py`, real registry from
  `dogfood-logs/313-gate1-run1/current-task.md`, 27 requirements, rendered through
  `inline_schema_refs` exactly as `llm.py` sends it):

  | batch | today | one field per id | one field per id + quote enum | **one requirement + quote enum** |
  |---:|---:|---:|---:|---:|
  | 1 | 10,809 | 12,130 | 12,315 | **12,315** |
  | 3 | 10,911 | 35,298 | 33,835 | **12,315** |
  | 8 | 11,166 | 93,218 | 87,312 | **12,315** |

  The per-id-field shape at batch 8 costs **93 KB of schema against today's 11 KB** —
  `DR-302`'s rejection of fixed slots, reproduced on this stage. The single-requirement
  shape costs **+1,506 bytes, +14%**, because there is one copy of the item model and one
  small enum (a requirement's span set runs 100–700 bytes). Prompt caching is not a
  counter-argument here: `DR-302` Decision 2 measured decompose's shared prefix at 694
  tokens, below the provider's 1,024-token floor, so a per-call schema forfeits nothing.

- **The cost moves to call volume**, and `DEFERRED.md` [2026-08-20] has already priced
  it: ~505 per-requirement calls against 79 batched, about $4.50 to re-record, and
  *cheaper* on re-runs because each call is individually carry-forwardable.
- **It makes `#231` structural** — a per-requirement request key is a function of that
  requirement alone, so editing bullet 7 cannot re-split bullet 12.
- **It repairs the two-pass proposal rather than competing with it.** Pass B as drafted
  is a batch of one with a free-text quote, which is the corpus's *worst-performing
  shape*: 3 of the 4 recorded single-`task-*` calls over-answer, and the two largest
  instances anywhere are of exactly that form. Pass B with a scoped quote enum is the
  version that works. This is the same re-record either way — do them together.
- **`_locate_quotation` retires.** The returned value is one of the spans offered, so the
  whitespace-insensitive matching and the re-filing logic in `_resolve_attributions` both
  stop having a job.

**What it does not close.** Paraphrase. The model can still write a `description` about
`constraint-03` while quoting a sentence of `task-01`. That cannot be made
unrepresentable, and it should be stated in the DR rather than glossed. But it degrades
the failure from *misattribution* — an obligation filed under the wrong requirement,
which corrupts the requirement map — to *duplication*, which is the linking stage's
existing job.

## 10. Fix B — tell the model what the Task block's relationship to the rest is

This is (ii), and no schema closes it: an obligation restating `constraint-03` while
quoting `task-01`'s own second sentence is structurally legal under Fix A.

**Do not solve it by making the Task block context-only.** That was the obvious move and
the data does not support it. Across the 30 recorded reviews that carry a requirement
map, **173 of 738 obligations (23%) come from `task-*` requirements**, which are about
10% of the registry — and on a lexical proxy (Jaccard over content words), only 40 of
those 173 reach even 0.35 overlap with the closest bullet-derived obligation, and 133 sit
below it; median 0.18. The proxy is weak evidence — paraphrase evades it — but it
points the wrong way for "the paragraph says nothing new", so silencing it would risk
losing requirements, which is the one failure this project treats as worst.

What to do instead: make the containment explicit in the prompt. The registry is handed
to the model as a flat list that never says the Constraints section elaborates the Task
paragraph. Say it, and say what follows: obligations for the Task block are the ones its
elaboration does not state, and `no_obligation` with a reason is an honest answer when
the elaboration is complete.

**Measure it before believing it.** Residual judgements are unstable, and `no_obligation`
is already a suspect disposition (89 of 1,109 dispositions ever returned; the
`open_question` disposition has been returned zero times since `#217`). The
decompose-regression suite is the instrument; the failure mode to watch is the
`no_obligation` rate on task blocks rising to swallow real content.

## 11. Fix C — the prompt contradictions, which ride along with any re-record

Section 6 lists three. None is sufficient on its own — an instruction that competes with
another instruction is what already failed — but they cost nothing extra once a
re-record is being paid for, and leaving a prompt that says *"EXACTLY ONE entry for EVERY
requirement id you were given"* in place while building a schema that contradicts it is
how a future session re-derives this whole investigation.

## 12. Suggested order

1. **The quotation-scope rule from §5**, now — free, no re-record, and it is the
   before/after instrument for everything below.
2. **Fix A + Fix C** together, as one re-record, with the two-pass decision.
3. **Fix B**, measured against the decompose-regression suite, after A has removed the
   structural half of the problem and §5's counter tells you what is left.

---

## Reproducing

```
python3 analyse.py                    # reads .acceptance/cache/transcripts/
.venv/bin/python schema_cost.py       # renders the candidate schemas, prints the table
```

Prints the per-call table, the 2×2 and the Fisher p, and the per-disposition
own/batch/foreign breakdown for the eight over-answering calls. It classifies a quote by
whitespace-normalised containment in the registry text carried in the request itself, so
it needs nothing but the transcripts.
