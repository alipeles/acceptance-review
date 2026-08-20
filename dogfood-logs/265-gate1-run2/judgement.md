# Judgement — #265, Gate 1, run 2

Same `current-task.md` as run 1, byte for byte. The only change between the runs
is outside the tool's input: run 1's failing transcript was deleted from
`.acceptance/cache/transcripts/`, so the identical request was re-issued live.
No `--continue` — run 1 aborted and produced no run id to continue from.

## Outcome: the run completed. Run 1's abort did not reproduce.

```
run c001affb025eea79
  requirements: 18 derived, 0 carried, 0 revised; 3 decompose call(s)
Requirements: 18   with obligations: 17   deliberately none: 1
```

Same request, same model, same seed — one response repeated a whole disposition
with `-dup` appended to every id, the next did not. **So the run-1 defect is an
intermittent degenerate generation, not a property of this task file.** That
matters for how it is filed: the tool cannot prevent the model from repeating
itself, but it decides what to do when it happens, and today it abandons the
review.

It also means the failure is *latent and permanent once recorded*. The bad
response is stored under the request key, so every subsequent run replays it and
fails identically. Only deleting the transcript clears it, and nothing in the
tool tells you that is the remedy.

## The breakdown is accurate

18 requirements, 17 with obligations, 1 deliberately without. Checked against the
task file line by line:

- All six Constraints, all six Scope exclusions and all four real Completion
  expectations are present, each restated faithfully.
- `completion-01` is the bare section marker `Implementation`; it correctly got
  no obligation, with the reason *"Section marker standing alone with no
  requirement under it."*
- Nothing was invented.
- `task-01` and `constraint-05` were correctly merged onto a single obligation,
  `client-marks-reusable-opening-end`, reported as *"also serves constraint-05"*.

## Open questions: none.

**Corrected 2026-08-20:** read this as "the axis reported nothing", not as
evidence the mandate was unambiguous. A requirement that yields obligations
structurally cannot also raise an open question — see the correction in
`dogfood-logs/265-gate1-run3/judgement.md` for the code references and the corpus
count.

## The one thing worth acting on, and it is the input's fault

`task-01` yielded `share-opening-text-across-run-requests`:

> The model requests of a single review run share their opening text, with shared
> content written the same way in each request and placed at the front ahead of
> request-unique content.

That is `constraint-01` and `constraint-02` conjoined. It is a faithful reading —
the Task paragraph in this version of the mandate restated both constraints
almost verbatim — but a composite matches no single constraint, so the linker
cannot merge it with either, and it survives as a conjunction that mapping would
have to find evidence for as a unit.

Disposition: **the mandate was reworded**, which is the sanctioned rewrite of
weak wording. The Task section was cut to a one-sentence headline that states the
goal without re-listing the constraints. That is run 3.

This is not a workaround for a tool defect. The redundancy was written by hand
into the input, and the tool reported it accurately.

## Known defects observed, none newly filed

- `exclusion-04`'s obligation is typed `human_review`, and the six structurally
  identical Scope exclusions drew four different types (`regression` ×3,
  `compatibility`, `human_review`, `functional`). This is #196 and #205, both
  open, both already carrying instance comments that say more than this run
  does. No new filing. The type is consumed structurally only at
  `requirement/linking.py:171`, which keys on `TEST_DEMAND`, so nothing here is
  misrouted.
