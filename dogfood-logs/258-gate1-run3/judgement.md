# Judgement — #258 Gate 1, run 3

Re-run of Gate 1 after #266 landed (`9269171`) and the branch was rebased onto
it. Gate 1 was re-armed, not merely Gate 2: #266 changed the decomposition
prompt — it now also asks which kinds of evidence each obligation requires — so
the run-2 breakdown recorded at `3aeb676` was against a prompt that no longer
exists.

`decompose --task current-task.md --mode record`, then rebuilt byte-identically
with `--mode replay` to produce `output.log`.

**Task file unchanged from run 2.** No rewrite was made at this gate, so run 3
is a controlled re-run: same input, new prompt.

## The breakdown is accurate

21 requirements → 20 obligations, 1:1, one requirement deliberately carrying
none. **No open questions.** No invented obligations; none of the real ones
missing.

The single decline is `completion-01` ("Implementation"), a section marker with
no checkable content. Correct, and the stated reason says exactly that.

Stable against run 2 in the shape that matters — 21 → 20 with one deliberate
decline, no composites, no unreconciled cluster. Zero open questions remains
**observed, not confirmed**: #193 says membership oscillates, and one run cannot
show otherwise.

## The `required_evidence` reasons — the thing this gate had to check

#266's note in `session-state/258.md` predicted the two obligations that blocked
Gate 2 run 1 — `region-coverage-case-list-omits-missing-path` and
`no-failures-without-root-task-file` — would come back "requiring less than both
kinds of evidence, each with a stated reason", and asked for those reasons to be
read, since a wrong *no test is owed here* is the false green this design is
most exposed to.

**The prediction was wrong, and in the safe direction.** Both came back
`code_and_tests` with no reason — the default. Nothing was excused from needing
a test, so there is no false green to find here.

Where the new axis did fire, it fired defensibly:

| obligations | value | reading |
|---|---|---|
| the six `test_demand` ones | `tests_only` | each requirement literally asks for an assertion; the test *is* the artifact |
| `parse-test-docs-state-inputs-covered` | `code_only` | a docs requirement, satisfied by the source text |
| the five `## Scope exclusions` | `code_only` + `satisfied_by_absence` | work deliberately not done, settled by the diff |

Every one of those carries a specific reason naming its own obligation, not a
generic sentence. I would defend all thirteen.

Two smaller observations, neither a stop:

- The five scope exclusions typed `functional` ×4 + `compatibility` ×1 — the
  same wholesale flip already queued as a comment on #205 from runs 1 and 2.
  Nothing here depends on the type.
- `decompose`'s **text** output renders neither `required_evidence` nor its
  reason. This gate is required to check those reasons, and the only way to see
  them is `--json`. Queued as a presentation gap, not a stop.

## Verdict

**Gate 1 passes, agent-confirmed, at `907779a`.** Awaiting human confirmation.
