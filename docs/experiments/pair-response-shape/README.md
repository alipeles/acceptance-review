# Pair response-shape pilot (#314)

Which response shape the (defect, test) pair question uses. **The decision and
its figures are `docs/DR-314-pair-response-shape.md`;** this file is how to
repeat the measurement and the traps in it.

## Running it

```bash
.venv/bin/python docs/experiments/pair-response-shape/pilot.py
```

Makes live calls — 13 cases × 2 arms × 3 seeds = 78 — and records them, so a
second run replays and costs nothing. Roughly $0.05 the first time. Writes
`findings.json` beside the script, holding every per-case prediction as well as
the aggregate figures, so a disagreement with the write-up can be traced to the
case that caused it.

## What it measures against

#315's human-reviewed defect labels on the archetype fixtures. Each labelled
defect carries `killed_by`, the tests that would fail if the delivered code
contained it. That is the ground truth; the arms are scored on how well their
predictions match it.

**This is a stronger control than #314's acceptance asks for.** #314 names the
current mapping stage's shared-mapping count, which compares one model stage's
opinion against another's. The labels compare against a human's.

## Traps

**The labelled defects are fed in, not enumerated.** Deliberate: #315 exists to
separate "the enumerator missed the defect" from "the judge missed the kill",
and this pilot chooses a shape for the judge. Holding the enumerator at perfect
means every difference measured belongs to the judge. It also means the recall
figures here are an upper bound on what a real run achieves.

**Both arms send identical request content.** Only the response schema differs.
If you change a prompt, change it in `_SHARED_PROMPT` so both arms move
together, or the comparison stops being attributable.

**One draw decides nothing.** The single-seed version of this pilot showed
0.875 against 0.9375 and would have been fairly dismissed as noise. Three seeds
showed the listing arm swinging across 4 labelled kills while the verdict arm
swung across 1, and the stability gap — not the mean — is what decided it. Vary
only the seed; temperature and prompts stay fixed.

**Seed 0 may replay for free.** It was recorded by the earlier single-seed run,
so its cost reads $0 and is not comparable with the other two. Take cost from
seeds 1 and 2, or clear the cache first.

**Node ids must match the labels.** `killed_by` uses `<file>::<name>` pytest node
ids, and the script parses tests into the same form. If a label names a test the
parser does not produce, that labelled kill silently becomes unreachable and
both arms lose recall for a reason that is not about either of them. The probe
that checks this is the id-matching assertion — run it after touching either
side.

## Sample size

13 cases, 38 defects, 68 pairs, 32 labelled kills. One flipped edge moves recall
by about 3 points. Enough to separate the arms; not enough for a confidence
interval on either.
