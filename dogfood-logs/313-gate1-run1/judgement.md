# Judgement — #313 Gate 1, run 1

*Run at `03c96e5` on branch `313-defect-enumeration` (working tree clean apart
from `current-task.md`, which is the input recorded here). 2026-08-21.*

Command:

```
.venv/bin/acceptance decompose --task current-task.md
```

Exit 1. No decomposition, no obligation breakdown, no open questions, no ledger
entry. The whole run produced nothing:

```
acceptance: model error: requirement 'task-01' was disposed more than once
```

## What the recorded response actually contained

Decomposition ran in four batches (batch size 8). Three were clean. The
disposition ids each batch returned:

| batch | requirement ids disposed |
|---|---|
| 1 | `exclusion-05`, `exclusion-06`, then `task-01` **twelve times** |
| 2 | `constraint-09` … `constraint-12`, `exclusion-01` … `exclusion-04` |
| 3 | `constraint-01` … `constraint-08` |
| 4 | `completion-01` … `completion-08` |

Batch 1 is the failure. All twelve `task-01` dispositions say `yielded`, and
each carries a **different** obligation — they are not repeats of one another.
The model split one requirement across twelve dispositions instead of putting
the twelve obligations inside one disposition's `more_obligations` list, which
is what that field exists for. Only the first copy used `more_obligations` at
all; the other eleven left it empty.

The obligations themselves look correct. Reading all twelve, they are a
reasonable decomposition of the Task paragraph — distinct, each with a
plausible `source_quote` drawn from the paragraph, no invention. Nothing about
the *content* of the answer is wrong. Only its shape is.

Transcript holding it, for anyone reproducing this (not committed — transcripts
embed the full request):
`.acceptance/cache/transcripts/7d6f41d26691cbafbebf90e16d0efcf0b25b95f9c3b2a0b1b4dd909d6a39bc04.json`

## Triage: a tool defect, and a new one

`_requirement_map` (`src/acceptance/requirement/obligations.py:1275`) raises on
any second disposition for a requirement that is not byte-identical to the
first. That rule implements #217's ban on a self-contradictory disposition —
"two different answers for one requirement". These are not two different
answers. Twelve dispositions all saying `yielded`, carrying twelve different
obligations, are one answer expressed twelve times.

`_batch_dispositions` (`:1214-1244`) has the guard that was meant to absorb
this, and it only drops an **exact** repeat (`previous == entry`). Differing
copies fall through to the raise.

**This is a sibling of #298, not #298.** #298 ("A repeated disposition with
mechanically-renamed ids aborts the entire review") is the same crash at the
same line from #265's Gate 1, but its cause is a verbatim repeat with `-dup`
appended to every id — a degenerate generation. Its proposed fix, comparing
dispositions for equality while ignoring ids, would **not** catch this one: the
copies here differ in every field, not just their ids. What the two share is the
blast radius, which #298's "worth deciding alongside it" paragraph already
raises: whether one batch's `SchemaValidationError` should end the run at all.

Both dispositions permitted by the gate rules were considered:

- **Address it in the work under review** — not available. The fault is in
  `requirement/`, which is the #181 decomposition umbrella's area, not #313's.
- **Attribute it to a tool defect** — this, with a drafted filing queued in
  `docs/DEFERRED.md` for review at the gate.

## Consequences worth recording

1. **The failure is permanent for this input.** The response is recorded, so
   every re-run replays it and dies identically — confirmed by run 2, which is
   byte-identical to this one. Clearing it means finding and deleting the
   transcript by hand, and nothing in the output says so. #298 records the same
   property.
2. **A crashed run leaves no ledger entry**, so there is no run id to pass to
   `--continue`. The next attempt cannot carry anything forward and starts from
   scratch, however small the edit to `current-task.md`.
3. **Eighteen requirements were decomposed and none survive.** Three of the four
   batches answered cleanly and their work is discarded with the fourth.

## Not a defect: the Task paragraph is genuinely weak

Independent of the above, and the honest half of this judgement. The Task
section restates material that Constraints already carries word for word — the
"persists with the rest of the review … refers to by its identifier" sentence
appears in both. Twelve obligations out of one paragraph is a signal about the
paragraph as well as about the tool. By the gate's tie-break — *rewrite when the
tool's response makes you regret your wording* — this wording is worth
rewriting. The rewrite is not the fix and does not discharge the filing above.
