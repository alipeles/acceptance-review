# Gate 2, run 1 — #204 at `9aeb46e`

**The run does not complete.** It aborts before producing a review:

```
acceptance: model error: response did not account for 2 of 34 requirements: task-02, task-03
```

Deterministic — replay over the recorded transcripts reproduces it exactly.

## What happened, from the transcripts rather than the message

34 requirements, 5 batches at size 8. **Four batches were clean**: each disposed
exactly its own ids, no overstepping, no linking. The fifth — `task-02`,
`task-03` — returned this:

```
obligations:
   partition-derivation-by-requirement-batch
   stop-derivation-linking
dispositions:
   task-02 -> yielded  [partition-derivation-by-requirement-batch, stop-derivation-linking]
   task-03 -> yielded  [partition-derivation-by-requirement-batch, stop-derivation-linking]
```

Both requirements named **both** obligations. That is precisely the linking
DR-204 forbids, so `_batch_dispositions` recorded two `unusable_answer`s and
dropped both dispositions; `_requirement_map` then found two requirements
unaccounted for and raised.

**The validator did exactly what it was built to do, on the first real response
it ever saw.** That is the finding, and it is two findings at once.

## Finding 1 — the model violates the new prompt rule immediately

The system prompt now says, in as many words, that every obligation belongs to
exactly one requirement and that two requirements stating the same thing get an
obligation each. The model ignored it on the first live run.

This is #219's shape — *the decomposer already violates an explicit instruction*
— and it is the evidence DR-204 relied on when it chose **a validator, not a
prompt rule**. So the architecture is vindicated. What it also means is that the
validator is not a backstop for a rare event; it is going to fire routinely, and
its remedy is therefore load-bearing in a way DR-204 did not treat it as being.

Worth noting: the model's answer is not *unreasonable*. `task-02` and `task-03`
in this task file genuinely restate each other — `task-03` is a one-line summary
of the paragraph above it. Under DR-204 the correct output is two obligations
for `task-02` and two duplicates for `task-03`, merged later by #144. The model
took the shortcut the old prompt used to demand.

## Finding 2 — the remedy makes the tool unable to review the file at all

This is the part I do not think DR-204 settled, and I am not resolving it alone.

The chain is: reject the link -> neither requirement is disposed -> the mandate
is unaccounted for -> `_requirement_map` raises -> **no review is produced**.
Each step is defensible on its own, and #217 established the last one
deliberately: *a response that does not account for the mandate is not a review
with a gap in it; it is not a review.*

But that rule was written when derivation was **one call**. A bad response then
meant the whole mandate was unread, and aborting was proportionate. Under
partitioning, four batches out of five were perfect and the run still dies. And
because temperature is 0 with a fixed seed, **re-running changes nothing** — the
tool cannot review this task file, ever, until something changes.

A reviewer that refuses to review is not a safe default. It is a different
failure from the one #217 was preventing.

## Options, and what I would do

**A — keep the abort (current).** Honest: we genuinely do not know what
`task-03` requires, because the only answer we got states `task-02`'s content.
Cost: a single linking slip in any batch destroys the whole review,
deterministically.

**B — duplicate the shared obligation, one copy per claimant.** Superficially
"noisy not lossy", and it is what DR-204's principle sounds like it wants. I
think it is wrong: the second requirement would receive an obligation stating
the *first* requirement's content under a fresh id. That is #223's exact damage,
laundered rather than repaired, and it would read as a clean result.

**C — report the affected requirements as unaccounted-for in the review, and
block the verdict, instead of aborting.** The other four batches' work survives,
the user sees the whole picture, and the two damaged requirements are named
loudly with the reason. This is what `unread_source` already does for text the
*parse* could not read — #202's rule applied one stage later, to text the
*derivation* could not honour.

**I would take C**, with the verdict hard-blocked rather than softened. The
tension to settle first is that it is adjacent to the `UNDISPOSED` disposition
#217 removed — but not identical to it. `UNDISPOSED` covered a requirement the
response silently *ignored*; this covers one whose answer we *examined and
rejected*, with the reason recorded. The objection #217 raised was that a
malformed response flowed on to a verdict as a soft finding; that objection is
met by blocking the verdict, not by aborting the process.

This wants a DR-204 amendment either way.

## Not attributable to the work, and not a task-file rewrite either

I considered rewriting `task-03` — it is a redundant summary sentence, and
CLAUDE.md's sanctioned edit covers weak wording. **I did not.** The tool did not
raise a finding about my wording; it hard-failed. Editing the input to get past
a hard failure is fixing the output, which is the thing that rule exists to
forbid. The wording being defensibly improvable does not make the edit honest
*here*.

## Standing

**Gate 2 has not passed and there is no PR.** The blocker is a design decision
on the no-linking remedy, not a defect to patch.
