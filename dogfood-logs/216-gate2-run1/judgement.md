# Gate 2, run 1 — #216 at `2ae0fed`

`INCOMPLETE`. Three obligations below strongly-supported. **Two were real gaps
in my work; one is a tool defect.** Mapping was checked before reading the
verdict (DR-164): the new tests were mapped densely and accurately — every
`region_coverage` test reached between one and five obligations, and the
`obligation_ids` that came back empty were unrelated pre-existing tests, which
is correct. This run is not half-blind.

## 1. `obligation-region-level-coverage-assertion` — partially supported — REAL

> The coverage test asserts total coverage directly over source regions rather
> than over requirement counts.

The recommendation: *a parser that produces the right requirement count but
leaves nested source regions unaccounted for would still pass.*

Correct, and I had missed it. Every existing test exercised parses that were
right or wrong on both axes at once, so nothing demonstrated the assertion sees
a loss a count cannot — which is the entire reason the assertion is phrased over
characters. I had verified it by hand against a worktree of the old parser and
left that verification outside the suite.

**Addressed** in `77ae7cb`: `uncovered_regions` takes the parse as an argument,
and a test feeds it a parse whose count is exactly right and one of whose spans
stops short.

## 2. `obligation-decision-recorded-in-repository` — nominally supported — REAL

> The nested-as-requirement versus nested-as-unread decision is recorded in the
> repository.

Mapped to `test_roundtrips_through_persistence` and two `requirement_map` tests,
none of which has anything to do with recording a decision — they pass whether
or not DR-216 says anything. That is the inverted-evidence shape session-state
records against #218 and #217.

But the finding underneath is real: the decision lived in `docs/DR-216` with
nothing holding it there. Nothing in the parser distinguishes *this is the
policy* from *this is how it happens to behave*, so the record is the only place
the choice survives an edit — and the repo already has the pattern for pinning
one, in `tests/test_decision_records.py` for DR-202.

**Addressed** in `77ae7cb`: three tests pin the decision, its scope over fences
and tables as well as bullets, its lossy-versus-noisy ground, and decision 5's
vacuity argument.

## 3. `obligation-region-level-total-coverage-tests` — unsupported — TOOL DEFECT

> A test asserts region-level total coverage over the repository's committed
> task files and over the decompose-stability corpus.
>
> requirements: **constraint-11, constraint-12**, completion-05, completion-06

Two separate defects in one obligation.

**It is a duplicate.** Obligations 7 and 8 already state these two corpora
separately, from constraint-07 and constraint-08, and both are strongly
supported by `test_the_repositorys_own_task_files_are_fully_covered` and
`test_the_decompose_stability_corpus_is_fully_covered`. The mapper assigned
those tests to 7 and 8 — correctly — leaving this duplicate with `(no mapped
test)`. Its `unsupported` rating is manufactured by the duplication. There is
nothing to build: any test mapped here would be one of the two already mapped.

**It absorbs two constraints it does not state.** `constraint-11` is *"Typed
schemas are pydantic models"* and `constraint-12` is *"Tests issue no live model
calls"*. This obligation states neither. Both are true of the change — the parse
model was already a pydantic `PersistableModel` and the new tests make no model
calls — but no obligation in the set says so, so the tool cannot confirm either,
and `28 of 29 requirements yielded obligations` counts both as read.

This is **#223 exactly**, and it is now reproduced with a stronger claim than
#223 currently holds: the absorbing obligation carries **the same id**,
`obligation-region-level-total-coverage-tests`, as in the #216 Gate 1 run 2
decompose. Same two constraints, same destination id, different stage,
different SHA. That is a deterministic defect, not run-to-run noise.

**Attributed to #223.** Comment drafted and awaiting human review before filing.

## Read the obligation text, not the arrow

Nothing in this run is unlinked and nothing is unaccounted for. `constraint-11`
and `constraint-12` both carry an arrow to a real, plausible-looking obligation.
The defect is visible only by reading that obligation's text against the
constraint's.
