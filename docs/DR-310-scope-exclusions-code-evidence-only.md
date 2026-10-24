# DR-310 — a scope exclusion is owed code evidence only, and the coverage stage is told which obligations are exclusions

**Issue:** #310 (a scope exclusion sometimes yields a positive obligation, and
the coverage stage then reports it not addressed).
**Resolved:** 2026-10-24, in conversation with the owner, before implementation.
**Status:** resolved. Reverses #266's per-bullet evidence judgement for the
Scope exclusions section only; leaves it standing for every other section.

## What was wrong

At #302's Gate 2, five of six scope exclusions became obligations of the form
"The change does not …". The sixth, "Model calls issued by the measurement
harness, which is not part of a review run.", became "The change **excludes**
model calls issued by the measurement harness from the review run scope" —
work to do. The coverage stage looked for a change doing that, found none, and
reported it `not addressed`, while three siblings with the identical evidence
("none breaches this boundary") were `addressed`. #338's Gate 1 reproduced it on
two more wordings.

The decomposer's wording was the visible fault, but it was not the whole cause.
`coverage/prompt.py::obligations_block` rendered each obligation as id, type
and description only. The coverage stage was never told that an obligation came
from a scope exclusion, although `Obligation.satisfied_by_absence` has recorded
that from the parse since #153. It could recognise a boundary only by its
wording, so one mis-worded obligation was enough to flip the verdict.

## Decision 1 — a scope exclusion is owed code evidence only, set from the heading

Every obligation derived from a `## Scope exclusions` bullet has
`required_evidence = code_only`, with a fixed reason, set in
`requirement/obligations.py` from the parsed section. The model's answer for
that field is overridden. This is the same move `satisfied_by_absence` already
makes, and for the same reason: a distinction the parse already knows is not
re-asked of the model.

**Reversed: #266's per-bullet judgement for exclusions.** #266 let the model
decide, bullet by bullet, whether an exclusion was owed a test, on the
reasoning that a bullet excluding a change to *behaviour* ("this does not alter
how pagination works") names something a regression test asserts directly. The
owner ruled that a scope exclusion is a genuine obligation but is satisfied by
code evidence alone. A reviewer confirms it by seeing that the diff does not do
the excluded work; asking for a test of something the change was told not to
touch induces work the mandate never asked for.

**Kept: `satisfied_by_absence` and `required_evidence` stay separate fields.**
Every exclusion is now `code_only`, but not every `code_only` obligation is an
exclusion — a version pin is code-only and is satisfied by code that is
present. Merging them would strip a pin's citations (#266's original reason).

**Kept: the per-obligation judgement everywhere else.** Outside the exclusion
heading, which evidence is owed remains the model's call, guarded by
`test_the_ordinary_requirements_still_require_test_evidence`.

## Decision 2 — the coverage stage is told which obligations are exclusions

`obligations_block` marks every `satisfied_by_absence` obligation
`(scope exclusion: '<bullet text>')`, and the coverage prompt says to judge such
an obligation against the quoted bullet, however its description is worded.
This makes identical evidence give an identical status across a run's
exclusions without depending on the decomposer's wording.

Measured before the change, against Sonnet 5.5: three exclusions over archetype
01's diff, one deliberately worded as work to do ("The change excludes refund
receipts from `format_line`, so that a refund is handed to the returns service
instead of being formatted"). The pre-change code reported that one
`not_addressed` and the other two `addressed` — #310 exactly. With the mark it
is `addressed` with its siblings (`tests/prompts/test_coverage_prompt.py`).

**Rejected: a code check that an exclusion's description is in the negative
form** (e.g. that it contains "does not"). It would be a judgement over English
text, the shape the markdown-never-as-interchange invariant exists to avoid, and
it is unnecessary once the coverage stage reads the parse's own mark.

**Cost.** `obligations_block` is shared by coverage classification,
unrequested-change detection and disposition. The mark changes only requests
that carry an exclusion obligation, so recordings of those stages over
obligation sets without one keep replaying.

## Decision 3 — a trailing explanatory clause is an aside

The decomposition prompt now states that a clause explaining why work is
excluded ("which is not part of a review run") is never work of its own, with
#302's bullet as the worked example. On Sonnet 5.5 the defect did not reproduce
on #338's task file or a #302-shaped one (0 of 2) even before this edit, so the
prompt change is not shown to be what fixes it; Decision 2 is the guarantee.
The regression case is `exclusion-05` in `tests/prompts/test_decomposition_prompt.py`.
