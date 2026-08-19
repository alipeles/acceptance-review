# Task
Decomposition is re-derived from scratch on every run. `rerun.py` states the rule
it works under: a changed task invalidates everything, because obligations are a
function of the task text. One edited character therefore discards the whole
prior decomposition and asks the model for all of it again.

Measurement over three runs of one unchanged task file, differing only by seed,
found no obligation content lost — and 38 distinct criterion wordings across
three runs of roughly 20 criteria each, 8 of them appearing in all three runs and
23 in exactly one, with identifiers re-minted alongside the wordings. The
criterion text is itself the prompt for later stages, so that churn sets a floor
under every downstream stability figure. It is not model nondeterminism: an
identical prompt at temperature 0 with a fixed seed returned byte-identical
output three times. What moves is which request the model is given.

Make decomposition incremental over recorded state. A requirement whose text did
not change keeps the obligations already derived from it, without asking again.

## Constraints
- A requirement whose text is unchanged from the continued run causes no model
  call during decomposition.
- The obligations of an unchanged requirement are carried forward with their
  identifiers unchanged.
- The obligations of an unchanged requirement are carried forward with their
  descriptions unchanged.
- An edited requirement is re-derived in one model call carrying the previous
  text, the new text, and the obligations previously derived from that
  requirement.
- An obligation that persists across an edit to its requirement keeps the
  identifier it already had.
- A requirement present in the continued run and absent from the task file under
  review has its obligations dropped.
- The removal of such a requirement is reported.
- A requirement with no counterpart in the continued run is derived without
  reference to any previously derived obligation.
- Two requirements are the same requirement when their text matches exactly.
- Requirements left unmatched by exact text are matched to each other through
  `benchmark/alignment.py::align_obligations`, which distinguishes an edited
  requirement from a new one.
- A merge decision over two obligations that are both unchanged is carried
  forward without a model call.
- A merge decision over two obligations of which either changed is asked again.
- Carry-forward reads only the run named as the continued run.
- No obligation is carried forward when no continued run is named.
- The carried state of a task file decomposed without a named continued run is
  empty.
- A carried obligation's `source_quote` is an exact substring of its
  requirement's text in the task file under review.
- An obligation whose `source_quote` is not such a substring is re-derived rather
  than carried.
- An entry is carried only when re-deriving it would issue the same request key
  it was recorded under.
- Decomposition carries a stage-logic version identifying behaviour that changes
  its output without changing its request.
- An entry recorded under a different stage-logic version is not carried.
- Every run reports an identifier for itself.
- A run that continues a previous run records that run's identifier as its
  parent.
- A run identifier appears in no review state.
- A run identifier appears in no rendered report.
- Each run records its derivations in a ledger file of its own.
- A ledger file is appended to and never rewritten.
- No ledger file is written under `.acceptance/cache/`.
- A run's ledger records which requirements were carried, which were derived and
  which were revised.
- A run's ledger records the request key of each derivation it performed.
- A run's ledger records the stage-logic version it ran under.
- A run's ledger records how many model calls it issued.
- `review_state.py::RequirementDisposition` records whether its requirement was
  derived, carried or revised.
- A carried requirement's disposition records the content digest of the
  derivation it was carried from.
- A revised requirement's disposition records why it was revised.
- Each field added to `RequirementDisposition` has a default that preserves the
  meaning of dispositions written before this change.
- Review state records no wall-clock time.

## Scope exclusions
- Inferring that a task file continues a previous run without being told which
  run it continues.
- Any form of naming the continued run other than by its identifier.
- Prior-review selection for stages other than decomposition, which
  `rerun.py::find_prior_review` performs over git ancestry.
- Counting how many runs a decomposition took to settle.
- Deriving a requirement more than once within a single run.
- What the decomposer derives from a requirement it does derive fresh.
- The wording the decomposer chooses for an obligation it derives fresh.

## Completion expectations
- Implementation
- A run over an unchanged task file naming a continued run issues no decompose
  model call.
- A run over an unchanged task file naming a continued run produces byte-identical
  obligations, identifiers and descriptions.
- A decomposition run against ledger state recording a different task file
  produces the same obligations as one run against no ledger state at all.
- Editing one requirement re-derives that requirement and leaves the obligations
  of every other requirement unchanged.
- A tool change that leaves the decompose request unaltered carries every
  previously derived obligation.
- A change to the decompose prompt prevents carrying the obligations derived
  under the previous prompt.
- A change to the decompose response schema prevents carrying the obligations
  derived under the previous schema.
- A change to the model or the seed prevents carrying the obligations derived
  under the previous one.
- The decomposition movements recorded as correct in
  `tests/fixtures/decompose-stability/` are still produced when the task file
  genuinely changes.
- `tests/test_cli.py::test_two_runs_over_the_same_input_are_byte_identical`
  passes, over a task file and continued-run state that are both unchanged.
