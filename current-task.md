# Task
Produce a `.acceptance/next-instruction.md` that tells the coding agent what to implement and which discriminating tests to add, so a review with gaps hands back an actionable next step rather than stopping at a findings report.

## Constraints
- Produce the instruction only when gaps exist. A review with no material gaps has nothing to instruct and must write no file.
- Derive the instruction entirely from findings and recommendations the review already produced; make no new judgment and no additional model call, so every line traces to something already established.
- Key the decision to produce an instruction off the computed completion verdict rather than re-deriving what counts as a material gap, so there is only one definition of materiality.
- Select rather than restate: the instruction is addressed to the coding agent, so it omits satisfied obligations, advisory unrequested changes, and evidence limitations, which belong in the human-facing report.
- Writing the file is a command-line side effect, not part of the shared review pipeline, so that scoring the same review over fixture repositories never writes into them.
- Unresolved open questions come first, because a review blocked on an ambiguity cannot be closed by writing code.

## Completion expectations
- Implementation
- On a review with several gaps, the instruction names each gap and the discriminating test that closes it, including the plausible defect that test must fail on.
- The instruction closes by asking for the builder declaration to be updated.
- A review with no material gaps produces no instruction and no file.
- The rendered report points at the written instruction file instead of reporting none.
