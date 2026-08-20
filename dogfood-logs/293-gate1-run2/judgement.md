# Judgement — #293 Gate 1, run 2

Command:

```bash
.venv/bin/acceptance decompose --task current-task.md --mode record \
  --continue 136b6616a990d48f
```

Run id `a84c1b0c6e71916a`, continuing run 1 (`136b6616a990d48f`). `output.log` is
9,293 bytes. Exit 0. **1 decompose call against run 1's 3**, 4 live calls total,
$0.0095 against run 1's $0.0360. 22 requirements carried, 3 revised, 0 derived.

Run 2 exists because two requirements were reworded after run 1, both approved by
the human on 2026-08-20:

- `constraint-02` and its mirror in `completion-02`: "costs no evidence-judgement
  request" became "is not asked about in the evidence-judgement request", because
  `judge_discrimination` is one batched call and a carried criterion removes no
  request.
- `exclusion-04`: "Rejecting a re-judgement that names no change it was given"
  became "Changing how a re-judgement that names no change is rejected", because
  the first phrasing produced an obligation that is false about the delivered
  tree.

The first reword worked. **The second did not**, and the ledger says why.

## The breakdown is accurate

Same as run 1 on the two questions Gate 1 asks: 25 requirements, 24 with
obligations, `completion-01` correctly recorded as a bare section marker. Nothing
invented, nothing lost.

## Finding 1 — the twin merge rate improved from 2 of 7 to 4 of 7

Run 1 merged two of the seven Constraint/Completion-expectation twin pairs. Run 2
merges four:

| pair | run 1 | run 2 |
|---|---|---|
| `constraint-01` ↔ `completion-02` (rating kept) | unmerged | **merged** |
| `constraint-02` ↔ `completion-02` (not asked about) | unmerged | **merged** |
| `constraint-04` ↔ `completion-05` | merged | merged |
| `constraint-05` ↔ `completion-06` | merged | merged |
| `constraint-06` ↔ `completion-07` | unmerged | unmerged |
| `constraint-07` ↔ `completion-08` | unmerged | unmerged |
| `constraint-08` ↔ `completion-09` | unmerged | unmerged |

**This is a controlled observation and it is the useful part.** The only edit
between the runs that touches this pair is the trailing clause of `constraint-02`,
which was changed to match `completion-02`'s trailing clause word for word. The
meaning did not change. The merge outcome did — and it flipped for *both* halves
of `completion-02`, including `constraint-01`, whose text I never edited.

So lexical overlap moves the merge decision. It is not the whole story:
`constraint-01`'s "keeps the rating stored for it" and `completion-02`'s "keeps
its stored rating" are still a paraphrase and merged anyway. But a
meaning-preserving edit to a neighbouring requirement changed whether an untouched
pair merged, which is the instability #304 is about.

Of the three still unmerged, one is defensible: `constraint-08` says a repeated
review "produces the same review state" and `completion-09` says "byte-identical
review state", which is a genuinely stronger claim, so keeping them apart is a
reasonable reading. The other two are plain restatements and should have merged.

**Attribution: tool defect, recorded against #304**, a child of #181. Still no
`Unreconciled linking answers:` block, so still not #242.

## Finding 2 — a scope exclusion is re-derived from new text and lands on the old, false obligation

This is the more serious one.

`exclusion-04` was reworded specifically to stop the tool asserting something
false. The obligation did not move. Both runs produce, byte for byte:

- id `rejecting-a-re-judgement-that-names-no-change-it-was-given-not-done`
- description *"The change does not reject a re-judgement that names no change it
  was given."*
- `satisfied_by_absence: true`

**It is not a carry failure.** `.acceptance/ledger/a84c1b0c6e71916a.json` records
this requirement as `derivation: "revised"`, with
`revision_reason: "requirement text changed from: Rejecting a re-judgement that
names no change it was given."`, and its `source_spans` quotes the **new** text
correctly:

```json
"source_spans": [{"start": 1386, "end": 1447,
  "text": "Changing how a re-judgement that names no change is rejected."}]
```

`observable_behavior` was re-derived too — it differs between the runs ("no work
that rejects" → "no logic that rejects"). So the model was given the new wording,
re-derived from it, and normalised *"Changing how X is done"* back into *"The
change does not do X"*.

Those are different claims, and the second is false about this repo. #292 built
the rejection of a re-judgement that names no change; it stays, and #293 depends
on it. The exclusion means *"I am not touching that behaviour"*; the obligation
says *"that behaviour must be absent from the change"*.

**Predicted consequence at Gate 2, recorded now so it is not a surprise later:**
#293's diff edits `evidence/anchoring.py` and `evidence/discrimination.py`, which
are where that rejection lives. An obligation marked `satisfied_by_absence`
against exactly that behaviour is likely to be reported as breached by a diff that
is doing the right thing.

**Attribution: tool defect.** This is the scope-exclusion family already in the
queue — the echoed-obligation defect concentrating on scope exclusions, and #301
(scope exclusions receiving inconsistent dispositions in one run) — but it is a
sharper instance than either, because it comes with a controlled before/after pair
showing the wording is not the lever. Queued as a comment on #301.

**No third reword.** CLAUDE.md forbids rewording repeatedly to chase a gate, and
the evidence here says rewording would not work anyway: the decomposer normalises
both phrasings to the same sentence.

## Finding 3 — no open questions again (#303)

Same as run 1. The axis reported nothing. Recorded as silence, not as a pass.

## Minor, not filed

The obligation for `constraint-02`/`completion-02` is
`criterion-unchanged-inputs-no-judgement-request-**2**`. The `-2` is there because
run 1's ledger, which run 2 continues, already holds the unsuffixed id from the
old wording. Nothing is broken — the id is stable and unique, which is all it has
to be — but a `-2` suffix is also #304's other symptom, so a reader could easily
mistake this for one. Noting it here so the next person does not.

## Dispositions

| Finding | Disposition |
|---|---|
| 1 — twin merges moved 2/7 → 4/7 on a meaning-preserving edit | tool defect, queued as a comment on **#304** |
| 2 — reworded exclusion re-derives to the old, false obligation | tool defect, queued as a comment on **#301** |
| 3 — no open questions raised | tool defect, already filed as **#303** |

Nothing was suppressed and nothing was worked around. **Gate 1 passes on its own
terms** — the breakdown is accurate, and every negative finding is either fixed or
attributed with a queued draft.
