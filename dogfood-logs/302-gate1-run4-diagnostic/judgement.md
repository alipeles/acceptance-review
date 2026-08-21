# Judgement — #302 Gate 1, run 4 (`e884fa0078cdfdce`) — DIAGNOSTIC, not a gate run

Run deliberately **without `--continue`**, over the same `current-task.md` as
run 3, for one purpose: to separate what the decomposer produces from the current
text from what the carry retains.

**This is not the run Gate 1 is judged on.** Without a continued run nothing is
carried (#269), so the obligation set is free to move for reasons unrelated to
the question being asked — and it did: nearly every obligation id differs from
run 3's despite identical input.

18 derived, 0 carried, 0 revised; 3 decompose calls. 18 requirements, 17 with
obligations, 1 deliberately none. $0.0184 recorded.

## What it establishes

**Finding C is the carry, not the decomposition.** `exclusion-01` here yields
**exactly one** obligation, `exclude-stage-asked-content-and-judgement`. Run 3,
over byte-identical task text, carries **two** — the extra one being the verbatim
sentence deleted from that bullet. The decomposer reads the current text
correctly; the carry retains an obligation whose source is gone.

**Finding B is not the carry.** The duplicate survives a from-scratch run:
`task-01` → `keep-stage-answer-format-stable-within-run` ("Each stage's answer
format stays the same across a review run") and `constraint-01` →
`same-answer-format-within-run` ("Every call a stage makes within one run declares
the same answer format, whatever items that particular call asks about"). Same
demand, two obligations, no merge, with no carry involved.

## Secondary observation

Every scope exclusion is typed `[regression]` here. Run 3 types two of them
`[compatibility]` and two `[functional]` on the same text. Recorded, not acted on.

## Cost note

`output.log` written **zero-byte on the first attempt** with exit 0 — fourth
consecutive occurrence this gate. Removed and re-run, producing 6,290 bytes.
