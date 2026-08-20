# Judgement — #291 Gate 1, run 1

Run `80d887644354ab0f`, continuing `e6c1f946e47d5280` (#292's last Gate 1 run).
Base `bcf2779`. 6 live calls, $0.0241.

## Verdict: Gate 1 passes.

20 requirements, 19 with obligations, 1 deliberately none. **No open questions
were raised**, so there is nothing to triage under the gate's three cases.

> **Correction, same day.** Do not read that line as evidence the mandate was
> unambiguous. A per-requirement disposition is exactly one of `yielded`,
> `open_question` or `no_obligation`, so a requirement that produces an
> obligation *cannot also* raise a question, and the prompt tells the model
> `yielded` "should be the large majority". Checked against the committed
> corpus: the last run to print an `Open questions:` section is
> `dogfood-logs/202-gate1-run{1,2}/`. Nothing in the ~30 issues since has raised
> one. The axis is dead, so this run's silence reports nothing either way.
> Raised by the #265 session; queued as a filing.

- **No invented obligations.** Every obligation traces to a line of
  `current-task.md`.
- **None of the real ones missing.** All six Constraints, all five substantive
  Completion expectations and all five Scope exclusions produced an obligation.
- `completion-01` ("Implementation") correctly produced no obligation — it is a
  section marker.

## Real finding: three twin pairs left unmerged (#242)

The task-file convention states each rule as a Constraint and mirrors it as a
Completion expectation. The linker merged three pairs and left three unmerged:

| merged | left unmerged |
|---|---|
| `constraint-01` + `completion-02` | `constraint-02` / `completion-03` — "refuses unless all four hold" vs "refuses when any one fails" |
| `constraint-05` + `completion-06` | `constraint-03` / `completion-04` → `caller-supplies-reuse-context-2` and `caller-supplies-reuse-context` |
| `constraint-06` + `completion-07` | `constraint-04` / `completion-05` → `reuse-refusal-carries-reason-2` and `reuse-refusal-carries-reason` |

Two of the three unmerged pairs produced obligation ids differing **only by a
`-2` suffix**, which is the decomposer naming the same obligation twice and the
linker then declining to merge them. That is stronger evidence than #242 currently
carries.

`task-01` also produced `reuse-decision-reaches-answer-through-shared-rule`,
which restates the merged `decomposition-uses-shared-reuse-rule`. A fourth
near-duplicate, from a different source line.

**Disposition:** attributed to a tool defect (#242), queued as a filing in
`docs/DEFERRED.md`. Not addressed by a reword: the wording is the repo's own
task-file convention, and rewording to move the linker is the forbidden kind of
edit ("fix the wording, never the output"). Expect it to split evidence between
twins at Gate 2, exactly as it did across #292's three rounds.

## Second finding: a model call attributed to stage `unknown`

The usage table reports `unknown  1 (1 live / 0 replayed)  1,236 prompt tokens`.
This is #296 — `benchmark/alignment.py` called from `requirement/carry.py::plan_carry`
without a stage label. Already filed; recorded here as another instance, no action.
