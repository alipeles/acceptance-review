# Judgement — #302 Gate 1, run 3 (`f1f9a9c986aeaafe`, continuing `e5c2490c4a564ea5`)

Re-run after deleting `exclusion-04` and trimming `exclusion-01`'s trailing
commentary sentence. **0 derived, 17 carried, 1 revised, 1 decompose call.**

18 requirements, 17 with obligations, 1 deliberately none.

## Fixed

**The contradiction is gone.** The run reports it explicitly:

```
REMOVED exclusion-04: - Any guarantee about what a provider does with a request
it was offered. … (1 obligation(s) dropped)
```

`does-not-change-provider-request-reuse-behavior` no longer exists, so the set no
longer holds both "a provider able to reuse a repeated request is offered one"
and "the change does not alter whether a provider reuses part of a request".

## Not fixed — TOOL DEFECT, and this one is new

**Finding C — the carry retains an obligation whose source text was deleted.**

`exclusion-01`'s bullet was trimmed to its first sentence. The run shows the
trimmed text (`output.log:60`) and still carries **two** obligations, the second
being `changes-answers-carried-and-identified-not-asked-or-decided`:

> The work changes how answers are carried and identified, not what is asked or
> decided.

That is verbatim the sentence deleted from the requirement. The obligation now
traces to no text in the mandate, which breaches the standing invariant that
every finding links to exact requirement text.

**Isolated by `302-gate1-run4-diagnostic` (`e884fa0078cdfdce`)** — the same task
file decomposed fresh, with no carry, yields `exclusion-01` with **exactly one**
obligation. So the decomposition of the current text is correct and the carry is
what retains the orphan. Attributed to the tool; queued as a filing against #181.

**Finding B persists** — `task-01`'s `same-answer-format-per-stage-call` and
`constraint-01`'s `same-answer-format-within-run` still state the same demand and
did not merge. The diagnostic run reproduces it from scratch
(`keep-stage-answer-format-stable-within-run` vs `same-answer-format-within-run`),
so it is not an artifact of the carry either. Queued as an instance for #242.

## Instability worth recording

`does-not-change-asked-items-or-judgements` is typed `[compatibility]` in run 2
and `[regression]` in run 3, on identical requirement text under a carry. The
diagnostic run types every scope exclusion `[regression]`. Not acted on; noted
because obligation *type* moving under a carry is the same family as #180.

## Open questions

**None, in any of the three runs — not a positive signal.** Per #303 the axis
cannot fire for a requirement that yields obligations, and has not fired since
2026-08-06.

## Not new

The `unknown` stage row is **#296**, expected on a `--continue` run.

## Cost

1 decompose + 1 obligation-linking + 1 `unknown`, $0.0042 recorded.

`output.log` written **zero-byte on the first attempt** with exit 0 for the third
consecutive run this gate; removed and re-run, producing 6,913 bytes.
