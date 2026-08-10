# Judgement — #228 Gate 1, run 1

**Outcome: decomposition accurate; two obligations traced to weak wording in
`current-task.md`, which was rewritten. Run 2 re-arms the gate.**

18 requirements, 17 obligations, 1 deliberately none, **no open questions**.

## Was the decomposition accurate?

Yes. Every obligation traces to a bullet I wrote; none is invented; none of the
18 requirements is missing. The one requirement with no obligation is
`completion-01` ("Implementation"), correctly read as *"Section marker standing
alone with no requirement under it"* — that is the right call, not a loss.

The five scope exclusions came back in absence form ("The change does not alter
…"), which is #153's `AdmissibleEvidence.CODE_ONLY` behaviour working as shipped
one commit earlier.

## Findings

### 1. `constraint-05` was overreaching — my wording, not a tool defect

I wrote *"No case reaches a scoring hook without having been checked."* The tool
typed it `invariant/explicit` and restated it faithfully. The problem is that it
is not true of the change I intend to make, and not what #228 asks for.

Evidence: benchmark scoring hooks are also called on synthetic cases built
inline in tests, whose task text is `"## Deliverable\n...\n"` or `"..."` —
neither has a `# Task` heading, so **both yield an empty registry**.

```
tests/benchmark/test_runner.py:46      task_text="## Deliverable\nAdd CSV export with active filters.\n"
tests/benchmark/test_scoring.py:21     task_text="## Deliverable\nAdd CSV export with active filters.\n"
tests/benchmark/test_alignment.py:123  task_text="..."
tests/benchmark/test_case.py:104       task_text="..."
```

An unconditional guard at hook entry would fail all of those. #228's Acceptance
names only `tests/fixtures/archetypes/` and `tests/fixtures/decompose-regression/`,
so the guard belongs on the corpus case builders, and the constraint had to say
so. Rewritten to *"A case built from either corpus is checked before it can be
scored."*

Disposition: **fixed the task file** (sanctioned rewrite of weak wording).
The synthetic-case task texts are queued as a separate filing — see below.

### 2. `completion-03` was ungrammatical — my wording

*"A test asserts that failure by supplying a task file that yields no
requirements…"* is not a well-formed sentence, and the tool reproduced it
verbatim into the obligation. It would have reached mapping and evidence
judgement at Gate 2 in that state. Rewritten to *"A test demonstrates that
failure with a task file the test supplies, not with a task file taken from
either corpus."*

Disposition: **fixed the task file**. Tie-break applied — the response made me
regret the wording.

`completion-05` was rewritten to stay consistent with the new `constraint-05`.

## Not findings

- **Obligation ids differ from run 2.** Known, #231; ids are minted per response.
- **Obligation *types* differ from run 2** for `constraint-06`
  (`invariant` → `regression`) and `constraint-07` (`functional` → `invariant`).
  Not a determinism breach: the task text changed between runs and the prompt
  carries the whole registry, so the request differed. Type assignment is #205.

## No tool defects attributed

Both findings are authoring defects in `current-task.md`. Nothing is queued
against a tool umbrella from this run.
