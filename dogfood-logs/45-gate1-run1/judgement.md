# Judgement — #45 Gate 1, run 1

Run id `c4e3938a331d4d36`. 13 requirements, 24 obligations, zero open questions.

**Not accepted.** Two problems, one mine and one the tool's.

## Real, and caused by the task file (mine)

`task-01` was a scene-setting paragraph — "The review has already named... Until
now it has only predicted... It can now find out by trying" — and the decomposer
turned it into three obligations: `named-concrete-failure-modes`,
`test-coverage-prediction-only` and `can-find-out-by-trying`. The first two
describe behaviour that already exists; the third restates the paragraph without
content. None is a requirement of this change.

This is the failure `CLAUDE.md` warns about in *Task-file style: ticket grade* —
narrative that is not a requirement gets decomposed as though it were. Fixed in
run 2 by deleting the paragraph.

A second, smaller instance: `task-03` said the edit "stays inside the region the
defect already points at", which `constraint-01` also said. Only one survived.
That is the tool deduplicating a restatement I authored, not a defect. Fixed in
run 2 by dropping the restatement.

## Real, and a tool defect

`constraint-03` read "Nothing asks a model to confirm that the edit really breaks
the requirement." The decomposer emitted obligation `confirm-edit-breaks-
requirement`: *"A model confirms that the injected edit really breaks the
requirement"*, classed `human_review`. The prohibition was turned into the thing
it prohibits.

This is not the sanctioned positive reframing of a prohibition — that would
produce something like "validity is established without a model call". The
negation is simply gone, so an implementation that obeyed the constraint would be
judged as failing the obligation, and one that violated it would be judged as
meeting it.

Worked around in run 2 by stating the constraint positively ("Whether an edit is
valid is settled by mechanical checks alone"), which decomposed correctly. The
rewrite is not the report: the defect is queued in `docs/DEFERRED.md` and stands
on its own.

## Cost

$0.1980 recorded, 37 calls.

## Note on the log

`decompose` exited 0 and wrote a zero-byte `output.log` on the first attempt.
Re-running after `rm -f` produced the full 8.5 KB. The empty run still made and
recorded its model calls, which is why the re-run replayed everything at $0.
This is the failure `CLAUDE.md` documents; it recurred on all three runs.
