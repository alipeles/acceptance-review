# Task
`decompose` returns a flat list of obligations plus a flat list of open
questions. A response covering 20 of a task file's 29 requirements is exactly as
well-formed as one covering all 29, so nothing downstream can notice that nine
requirements produced nothing. Gate 1 for #195 lost 4 of 15 Completion
expectations and 5 of 8 Scope exclusions this way, and the review reported no
gap.

Make decomposition return a mapping from requirement to obligation, so that a
requirement producing nothing is a recorded fact rather than an absence.

Separately, and independent of that defect: a reader auditing a breakdown cannot
see which requirement each obligation came from. `Obligation.source_spans` points
at a character offset, so the trace runs one way and only to text, never to an
identified requirement.

This change is representational. It alters the shape of what decomposition
returns, not the obligations it derives.

## Constraints
- A requirement registry is derived from `requirement/task_file.py::parse_task_file`.
- Requirement ids are assigned by the code, never by the model.
- A requirement id is its section and its ordinal within that section, in parse
  order.
- Each registry entry carries the `TextSpan` of the requirement it identifies.
- The requirement-to-obligation relation is many-to-many.
- An obligation serving two requirements is linked to both.
- An obligation is never duplicated so that each requirement can hold its own
  copy.
- Every requirement carries exactly one disposition.
- The dispositions are: yielded obligations; deliberately yields none, with a
  reason; raised an open question instead.
- The mapping is persisted in the structured review state that
  `review_state.py` and `review_store.py` already define.
- The mapping is rendered in the §16 report.
- `requirement/obligations.py::_user_prompt` passes typed, identified fields.
- `_user_prompt` does not pass `parsed.source`.
- The decomposer receives no `ChangeSet`.
- The decomposer receives no repository path.
- The decomposer receives no head revision.
- Typed schemas are pydantic models, as the rest of the repository defines them.
- Tests issue no live model calls.
- Recorded transcripts invalidated by the changed prompt are re-recorded once.

## Scope exclusions
- Changing which obligations a task file decomposes into. The obligation content
  is held fixed; only its representation changes.
- Partitioning obligation derivation by requirement batch, which is #204.
- Assigning obligation types in a separate pass, which is #205.
- Requiring an open question to cite where the task file fails to answer it,
  which is #206.
- Reading the base revision during open-question resolution, which is #207.
- Deciding whether the decomposer receives base-revision code context, which is
  #208.
- De-duplicating semantically duplicate obligations, which is #144.
- Aligning requirement ids across two versions of a task file, which is #209.
- Rebuilding #195's regression suite to bind its labels to the mapping.
- Measuring whether decomposition recall improves as a result of this change.

## Completion expectations
- Implementation
- A task file whose every requirement yields an obligation produces a mapping in
  which no requirement is undisposed.
- A requirement that yields no obligation appears in the mapping carrying its
  reason.
- A requirement that yields no obligation is visible in the rendered report.
- A requirement stated twice in different sections yields one obligation linked
  to both requirements.
- That same case yields one obligation rather than two.
- Requirement ids are identical across two runs over byte-identical task text.
- A test pins that the decomposer cannot reach a diff.
- A test pins that the decomposer cannot reach a head revision.
- A test pins that the pipeline persists the mapping rather than discarding it.
- The regression suite #195 delivered runs unchanged against the new output.
- No case in that suite flips its result.
- `docs/DR-202-decomposition-requirement-mapping.md` records the resolved
  requirement-id decision in place of listing it as open.
- The decomposition-accuracy figure is marked non-comparable across this change
  where a reader meets it.
