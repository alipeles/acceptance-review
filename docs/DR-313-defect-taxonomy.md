# DR-313 — the defect taxonomy's per-obligation-type contents

**Issue:** #313 (defect records and the enumeration stage), sub-issue A of #312
(defect-first evidence).
**Resolved:** 2026-08-29, at #313's Gate 1, which
`docs/DR-312-defect-first-evidence.md` assigns this decision to.
**Status:** resolved.

## What was open

DR-312's resolved question 4 settles the taxonomy's *shape*: the enumerator
walks a per-obligation-type checklist of ways a change can fail an obligation,
and may return a defect typed `other` carrying a free description where nothing
fits. It explicitly leaves the contents open, and puts them ahead of any
M-B5a.2 label being written, because #315 (the benchmark sub-issue) types its
ground-truth labels against this vocabulary.

## Decision 1 — a shared core plus two entries per obligation type

Four entries are walked for every obligation type:

| type | means |
|---|---|
| `qualifier_ignored` | the behaviour is implemented but a stated qualifier — only, at most, when X — is not honoured |
| `condition_inverted` | a guard or comparison runs the wrong way |
| `scope_too_narrow` | the behaviour holds for some inputs the obligation covers, not all |
| `not_wired` | the logic exists but nothing on the delivered path calls it |

`not_wired` is in the core because it is this repo's own most repeated finding,
recorded in CLAUDE.md as *"a helper with a good unit test that the pipeline never
actually calls"*.

Then two entries per obligation type:

| obligation type | entries |
|---|---|
| `functional` | `wrong_output_shape`, `missing_case` |
| `boundary` | `boundary_wrong_side`, `boundary_unhandled` |
| `error_handling` | `error_swallowed`, `wrong_error_surfaced` |
| `invariant` | `established_not_maintained`, `unenforced_on_one_path` |
| `regression` | `prior_behavior_altered`, `prior_behavior_removed` |
| `compatibility` | `old_input_rejected`, `stored_form_unreadable` |
| `explanation_observability` | `explanation_absent`, `explanation_states_wrong_cause` |
| `docs_config` | `documented_not_implemented`, `default_disagrees_with_docs` |

Six entries per obligation, plus `other`. Short on purpose: DR-312 names
Procrustean fitting — odd defects forced into the nearest slot — as a failure
mode to watch, and a long checklist walked for every obligation dilutes the
prompt that is supposed to drive recall.

**Rejected: one flat vocabulary for every obligation type.** It is simpler to
score and it would remove the risk that a mistyped obligation is walked against
the wrong checklist, which #313's Gate 1 observed twice in one run. Rejected
because DR-312 decision 4 settled on per-type, and because a twenty-item list
walked for every obligation is exactly the dilution the checklist exists to
avoid. The mistyping risk is real and is recorded against #181, the
decomposition-quality umbrella; the answer is to fix the typing, not to make the
checklist insensitive to it.

## Decision 2 — two obligation types get no checklist

**`human_review`** exists because a machine cannot settle the question. A
reasoned empty set is the expected outcome, and that is a valid result under
DR-312's resolved question 3.

**`test_demand` obligations are excluded from enumeration entirely.** This
resolves a conflict inside DR-312 rather than merely filling in a list, so it is
the substantive half of this record.

DR-312 decision 2 says the enumerator sees the obligation and the changed code
and never the tests. That is the mitigation for #252: an enumerator that can see
what is already covered drifts its denominator toward it, and a thinner
enumeration then earns a stronger rating. But a `test_demand` obligation is
*about* a test — `ObligationType.TEST_DEMAND` exists precisely to carry the
difference between "X" and "a test asserts that X" (DR-232). Enumerating a way
of failing such an obligation requires looking at the thing the design forbids.

This is not hypothetical: #313's own mandate produced six `test_demand`
obligations out of twenty-eight.

Three ways out were considered.

1. **Exclude `test_demand` obligations from enumeration.** Chosen.
2. Enumerate them, permitting only the reasoned-empty-set outcome. Rejected: it
   spends a model call to produce a result that is known in advance, and a
   reasoned empty set is supposed to mean *this obligation has no plausible
   static defect*, not *this stage declines to look*.
3. Narrow test-blindness to mean the tests mapped to this obligation rather than
   all tests. Rejected: it weakens decision 2 from an absolute to a judgement
   call, and #252's drift is exactly the thing a judgement call would let back
   in.

Excluding them costs nothing #313 claims. Its Acceptance is stated over derived
criteria on the §9.1 floating-rate example and over #270's true-by-construction
obligation, none of which are `test_demand`. What it does mean is that a
`test_demand` obligation reaches the defect-first evidence path with no defect
set, so #314 (pair mapping in shadow) and #316 (the cutover) must both treat an
absent set as distinct from an empty one. That distinction is the reason this is
a Decision Record rather than a list.

## Consequence for #315

The benchmark sub-issue's ground-truth labels type against the vocabulary above,
with `other` allowed. DR-312 also asks for the `other` share as a standing
metric: a rising share is a taxonomy gap, and a near-zero share alongside poor
enumeration recall is Procrustean fitting. #315 has no labels to write for
`test_demand` or `human_review` obligations.
