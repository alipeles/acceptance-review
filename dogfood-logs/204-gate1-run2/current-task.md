# Task
Obligation derivation issues one model call for the whole requirement registry.
At scale that call sheds work: an observed run over roughly 36 requirements, at
about 2.5k input tokens, produced no obligation for 9 of them. That is DR-164's
judgments-per-request failure, one stage earlier than the mapping stage where it
was first found and fixed.

The same call also links. It may attach a requirement to an obligation derived
from a different requirement, and that linking fails in both directions on one
task file under the same code, model and seed: seven scope exclusions declined
with reasons that stated the obligation, then all five over-merged onto another
requirement's obligation, with two Constraints absorbed into an obligation
stating neither. Absorbed content is gone, and the run still reports every
requirement as carrying a disposition, because that count reports dispositions
rather than coverage.

Partition obligation derivation by requirement batch, and stop derivation from
linking at all.

## Constraints
- Obligation derivation is partitioned by requirement batch, through the
  existing `partition.py` rather than a second partitioning mechanism.
- The whole task file appears in every derivation prompt. The batch scopes which
  requirements a call must answer for; it does not scope what the call may read.
- `RunConfig.decompose_batch_size` exists and is settable from the command line
  as `--decompose-batch-size`.
- The batch size is treated as a determinism control exactly as
  `mapping_batch_size` is: only the size enters the hashed request, and the batch
  index and batch count never do.
- A batch answers only for the requirements it was supplied. A returned
  requirement id that was not supplied to that call is recorded through
  `UnusableAnswerLog` rather than silently filtered.
- Obligation derivation performs no linking. A call may split one requirement
  into several obligations, or decline it with `no_obligation`, but it may not
  attach a requirement to an obligation derived from another requirement.
- Within one derivation response, each obligation id appears in exactly one
  requirement's disposition.
- A response naming one obligation from two requirements is recorded through
  `UnusableAnswerLog`, and neither affected requirement is treated as disposed.
- Merged results are ordered deterministically, so batch composition and merge
  order are pure functions of the input.
- A task file with N requirements produces ceil(N / size) derivation calls.
- Every requirement carries a disposition after the merge.
- Changing the decompose batch size invalidates recorded transcripts.
- Two runs over byte-identical task text produce byte-identical review state.
- `ReviewProvenance.request_partition_size` reports the size observed from the
  calls rather than the size read from configuration.
- Typed schemas are pydantic models, as the rest of the repository defines them.
- Tests issue no live model calls.

## Scope exclusions
- De-duplicating obligations, and attaching a requirement to an obligation
  derived from another requirement, which is #144 and lands immediately after
  this change.
- Scoring link precision, which is #211 and which measures #144's output rather
  than this pass.
- The wording of the decomposition prompt beyond what partitioning and the
  no-linking rule require, which is #205, #206 and #219.
- Whether an obligation needs test evidence at all, which is #148.
- Recovering the requirements a prior run dropped, or comparing obligation
  counts against recorded transcripts.
- Whether the de-duplication pass itself needs partitioning, which is a question
  #144 answers.

## Completion expectations
- Implementation
- A test asserts that a task file with N requirements produces ceil(N / size)
  derivation calls.
- A test asserts that every requirement carries a disposition after the merge.
- A test asserts that a returned requirement id the call was not supplied yields
  an `unusable_answer` finding, and that the requirement is not treated as
  disposed.
- A test asserts that a response naming one obligation from two requirements
  yields an `unusable_answer` finding, and disposes neither requirement.
- A test asserts that changing the decompose batch size changes the hashed
  request key, and that the batch index and batch count do not.
- A test asserts that two runs over byte-identical task text produce
  byte-identical review state.
- A test asserts that `ReviewProvenance.request_partition_size` reports the size
  observed from the calls.
- A task file stating one requirement in both Constraints and Completion
  expectations yields two obligations from this pass rather than one obligation
  carrying two requirement links.
