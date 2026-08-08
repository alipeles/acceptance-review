# Gate 1, run 1 — #204 at `ffc67b4` (main, post-#216)

`Requirements: 35   with obligations: 34   deliberately none: 1`. No
unaccounted-for line — the first Gate 1 run since #216 landed, on a file with no
nested content, so the parser change is exercised but not stressed.

**My assessment: the decomposition is accurate and I would defend it.** Human
confirmation still required before coding (Gate 1 step 4).

## Coverage — every requirement yielded an obligation stating its own content

All sixteen constraints, all six exclusions and all ten completion expectations
carry an obligation whose text restates that requirement. I checked each one by
reading the obligation's text against the requirement's, not by following the
arrow — the failure mode #223 taught. Nothing invented, nothing missing.

`completion-01` ("Implementation") was declined `no_obligation` with the reason
*"Section marker only; it does not impose a checkable requirement by itself."*
Correct, and the same decline the last three files produced.

## Two known defects did NOT recur, and that is diagnostic

**#223 did not recur.** `constraint-15` ("Typed schemas are pydantic models") and
`constraint-16` ("Tests issue no live model calls") are the *same two
requirements* — word-for-word — that #216's runs absorbed into an obligation
stating neither. Here each yielded its own obligation:

```
constraint-15 -> obligation-pydantic-schemas
                 Represent typed schemas as pydantic models.
constraint-16 -> obligation-no-live-model-calls-in-tests
                 Keep tests free of live model calls.
```

**#210 did not recur.** All six scope exclusions yielded their own obligations,
each stating what is not done. In #216's Gate 1 run 2, five of five were
over-merged onto another requirement's obligation.

**This narrows the #223 claim I filed.** That comment says the absorption is
*"deterministic, not run-to-run noise"* — true as stated, and it was: same
obligation id, same two constraints, across three runs and two stages **on one
task file**. This run shows the same two constraints in a *different* task file
are not absorbed at all. So the trigger is **task-file dependent**, not
unconditional. That is diagnostic information the fix needs, and it belongs on
#223.

## The premise of #204 did not reproduce here

#204 rests on Gate 1 for #195 dropping 9 of ~36 requirements in a single call at
~2.5k input tokens. This run is the same shape and larger:

| | #195's failing run | this run |
|---|---|---|
| requirements | ~36 | 35 |
| partition | none | `None` (verified in the transcript) |
| prompt tokens | ~2.5k | **3547** |
| requirements lost | 9 | **0** |

A single unpartitioned call over more tokens than the one that failed, and
nothing was shed. **This run is not evidence for #204.** It does not undermine
#204 either — #195's loss is recorded, and a probabilistic failure that does not
fire on one sample is not thereby absent — but it is worth stating plainly
rather than letting the issue's premise stand unchallenged in a log that happens
to sit next to it. It also means the "loses no requirement" acceptance item
(`completion-10`) can pass **vacuously** on a corpus that was not going to lose
anything, which is the #216 lesson applied here: the fixture has to be able to
fail.

## Open questions: zero, for the fourth consecutive run

Nothing to triage, so no case from the Gate 1 table applies. Recorded because
the streak is the point: four task files in a row, including one that explicitly
declared a design fork undecided, have produced no open question. Standing
concern against **#206**; not a blocker for this task, whose design is settled
in DR-204.

## One redundancy, not a blocker

`obligation-partition-by-requirement-batch` carries the CLI flag in its text
(*"...and make the batch size configurable from the command line as
`--decompose-batch-size`"*) while `constraint-03` separately yields
`obligation-batch-size-configurable` for the same flag. Two obligations state
it. Nothing is lost, and #144 is what merges such pairs. Noted so it is not
rediscovered as a finding at Gate 2.

## Linking is heavy here, and correct

40 links over 24 obligations. The many-to-one cases I checked are genuine
restatements — `obligation-partition-by-requirement-batch` serves `task-01`,
`task-03` and `constraint-01`, which really are the same requirement stated as
mandate, restatement and constraint.

Worth noting for what comes next: **after #204 lands, this same task file will
stop producing those links**, because derivation will no longer be permitted to
make them. The three would become three obligations, merged by #144. That is the
intended change, and it is why #144 must follow immediately — between the two,
this file's obligation set roughly doubles.
