# DR-171 — turning a named plausible defect into a mutation at exact lines

**Issue:** #171 (the open decision on how a named plausible defect becomes an
actual mutation at actual lines), owned by M8.4 / #45 (targeted mutation, the
`defect-killed` evidence tier).
**Resolved:** 2026-09-02, in conversation, before the M8 sequence starts.
**Status:** resolved.

## What was open

The defect enumeration stage (`defects/enumeration.py`, DR-312's defect-first
shape) produces a named plausible defect as prose plus a list of `path#hunk`
labels. M8.4 has to turn that sentence into a real code edit at real lines, run
tests, and read red or green as discriminates or proven-weak. #171 left five
things unsettled: where the mutation descriptor is produced, how the sentence
resolves to an exact span, whether the vocabulary is a fixed operator set or
free-form, what makes a mutant valid, and what happens when no valid mutant can
be built.

It was filed as a decision that must land before M8 starts, because the answer
might have required the enumeration stage's output shape to change — an
already-shipped stage whose recordings a schema change would orphan.

**It does not.** That is the first decision below, and it is the reason this
record could be written without touching any code.

## Decision 1 — the mutation descriptor is produced at M8.4, and the enumeration output shape does not change

The enumeration stage keeps emitting prose plus `code_refs`. A separate stage,
inside M8.4, reads one `Defect` and the source at head and produces the
descriptor. The alternative — having the enumerator commit to something
executable at the moment it names the defect — is rejected on four grounds, the
first of which is the important one.

**It would thin the denominator toward what is mutable.** The enumerator is
deliberately blind to the tests, because a denominator chosen by something that
can see what is already covered drifts toward it, and a thinner enumeration then
earns a stronger rating. That is #252, and the mitigation is DR-312 decision 2.
Requiring the same call to also produce a working patch reintroduces the same
drift from a different direction: the stage would favour defects it can express
as an edit. The measured shape of what is hard to express — documentation
defects, defects in non-Python files, defects about absent behaviour — is
recorded in §"What injection cannot decide" below, and those are precisely the
ones that would go missing. A recall stage must not be scored on executability.

**The obligation set is not final when enumeration runs, and enumeration is not
the last thing that can add to it.** I verified this in
`pipeline.py::run_review`: `resolve_open_questions` runs, `derive_obligations`
turns the resolutions into further obligations, those are appended to the set,
and only then does `enumerate_defects` run over the combined set. Any mutation
work done earlier than the defect it belongs to would have to be redone for the
derived obligations anyway.

**Cost.** Enumeration runs on every review; mutation runs only where the
feasibility probe passes (§8.3, and #170, the open decision on what signals
declare a suite hermetic and fast enough). At #316's Gate 2 scale — 48 defects —
a call per defect is small beside the 992 calls the pair stage already spends.
Folding it into enumeration charges every review on every repository for
something most of them will never use.

**Recording cost.** CLAUDE.md records that changing a stage's response schema
invalidates that stage's recorded transcripts. Adding a field to the enumeration
response orphans every enumeration recording in the corpus. Adding a new stage
orphans nothing.

## Decision 2 — the descriptor is one contiguous span replacement, inside the defect's own region

Three fields: a file path, a line span at head, and the replacement text. The
stage is asked for the smallest edit that makes the named defect true.

**Rejected: a fixed operator vocabulary** (constant replacement, boundary flip,
branch removal, return-value substitution). It is cheaper to verify, but the
taxonomy has 21 defect types plus `other` (DR-313, the defect taxonomy), and
`not_wired`, `error_swallowed` and `explanation_states_wrong_cause` each need
their own operator. A menu long enough to cover the taxonomy is not meaningfully
more constrained than free text, and it fails closed on `other` by construction.

**Rejected: a free-form diff.** It can fail to apply, which adds a failure mode
that span replacement does not have.

A span replacement expresses everything an operator set expresses and applies by
construction. The cost is that the vocabulary is unconstrained, so validity has
to be checked rather than guaranteed — Decision 3.

**Left open deliberately:** whether to revisit a canonical operator form later,
with an escape for cases it cannot express, if measurement shows the free-form
call is slow, expensive or unreliable. Nothing in this record forecloses that;
the descriptor's three fields are the same either way, and only what produces the
replacement text would change.

## Decision 3 — validity is four mechanical checks and no confirming model call

A mutant is valid when all four hold:

1. **It applies** — true by construction for a span replacement.
2. **The mutated file parses** — `ast.parse` on the result. This is the
   compile check, and in Python it is free.
3. **The span lies inside a region one of that defect's `code_refs` names.**
   This is what stops a mutant wandering into unrelated code, which is #171's
   third validity concern.
4. **The edit is bounded in size**, by a recorded line count.

**Rejected: a second model call to confirm the mutant really violates the
obligation.** It would be judging its own output, it costs a call per defect,
and it produces a claim at the same tier as the thing it is checking. Instead the
mutant text is recorded in review state so that a person reading the finding can
see exactly what was injected and disagree with it. That is weaker than a proof
and is honest about being weaker.

## Decision 4 — a defect no candidate test executes is decided at the coverage tier, not by forcing execution

This is the answer to the case where a defect can only occur on one path through
the code — one arm of a conditional, one configuration, one input kind — and no
test drives that path.

The evidence ladder decomposes cleanly, and the mutation stage is only the last
rung of it:

- **No candidate test executes the defect's lines.** The defect is uncovered, and
  that is established at `COVERAGE_CONFIRMED` (§8.1 tier 3) without any mutation.
  Nothing needs to be injected: a test that never executes a line cannot fail on
  a mutation of it.
- **Some tests execute the lines.** Mutate, and run exactly those tests. A test
  goes red, the defect is killed; none does, the defect survives. Both are
  `DEFECT_KILLED` (tier 4).

So the switch-arm case answers itself one rung down. This also matches what the
code already does with the static prefilter: `defects/support.py` treats an
`UnjudgedCause.PREFILTERED` pair as a survival established statically rather than
as a missing judgement, on the reasoning that the filter's contract is to exclude
only what it can prove. Coverage under injection has that same contract, which
the coverage-prefilter experiment states directly: *"under injection the
exclusion becomes sound for runtime defects."*

**Rejected: forcing the code down the path, or substituting a test double so the
defect can be triggered.** Three reasons.

It answers a question nobody asked. The review's question is whether the tests
*the builder wrote* discriminate. "Would a test that drove this arm have caught
it?" is a different question, and its answer is almost always yes, so it carries
no information.

It is the tool doing the thing it is supposed to be prescribing. Constructing a
fixture that drives an arbitrary path is test authoring. M8.4's output when a
defect is uncovered is a recommendation that such a test be written; writing it
in order to then report that it passes is circular in the way §13.5 scenario 5
(circular expected result) exists to catch.

It breaks Decision 3's third check by definition. A double changes something
outside the defect's own region, so a red result no longer says the mapped test
would catch this defect in the delivered code — it says the test noticed that we
swapped a dependency.

**A recorded limit of this decision.** Line-level coverage is too coarse for a
defect that lives on an unexercised *branch* of a line that does execute — a
configuration threshold the tests never cross, for instance. The `coverage`
library supports branch coverage and M8.3 (#44, the coverage-confirmed tier)
should record whether it is enabled, because the case above is decided wrongly
under line coverage alone: the mutated line looks reached when the relevant
branch was not.

## Decision 5 — the ambiguous outcome is a surviving mutant on executed lines, and it stays a finding

#171's comment names the "no test failed" result as ambiguous between blind
tests and an injected edit that changed no behaviour. Decision 4 removes the
first half: blind tests are separated out one rung down, before anything is
injected. What is left is a mutant on lines that were executed, where no test
failed. That is either a genuinely weak test or a behaviour-preserving mutation,
and nothing mechanical separates them.

It is recorded as a survival and reported as one, at `DEFECT_KILLED` tier, with
the mutant text attached. Two reasons for taking the risk in that direction. The
survival is the direction that produces a finding against the builder, and an
unsound survival recreates the failure #312 exists to remove — recommending a
test that already exists (#250, #287). But suppressing survivals would inflate
the rating, which is the failure #252 exists to remove, and inflation is silent
where a wrong recommendation is visible and arguable. Recording the mutant text
is what makes it arguable.

## Decision 6 — one instrumented run of the selected tests at head, before any injection

It buys three things at once: the per-test baseline (a test already red at head
tells you nothing when it is red under mutation, so it is excluded from the
verdict with a recorded reason), the coverage map that Decision 4 selects with,
and a signal for #170's feasibility probe. The coverage-prefilter experiment
measured that run at 5m15s on this repository.

This is not the product grading the user's green suite, which §8.2's scope
boundary rules out. It is establishing the control for the experiment, and the
distinction is that nothing is reported about a test that is red at head except
that it was excluded.

## Decision 7 — one `PairVerdict` record carrying a tier, so the static path stays and the rating has one implementation

Injection does not replace the static pair judgement. It overwrites individual
verdicts with better-evidenced ones.

`PairVerdict` gains a tier field. A verdict the pair-judgement stage produces is
`STATIC`; one the mutation runner produces is `DEFECT_KILLED`.
`evidence_tier.py::authorize_tier` already enforces which component may produce
which tier, and `Component.MUTATION_RUNNER` is already the only one authorized
for `DEFECT_KILLED`, so nothing new is needed there.

I verified that `defects/support.py::derive_support` computes the rating by
collecting defects with at least one killing verdict and comparing that count to
the enumerated count, with no reference to a tier. That arithmetic is unchanged
by this decision. The single record is the point: a parallel record type for
executed verdicts would fork the rating logic, and the two copies would drift —
the failure CLAUDE.md records against the CLI and the benchmark, which had drifted
onto different pipelines before a test pinned them together.

`defects/support.py` currently hardcodes `EvidenceTier.STATIC` as the achieved
tier for every criterion. It becomes the weakest tier among the verdicts the
criterion's rating actually rests on.

The consequence worth stating plainly: a review is a mixture of verdicts at
different tiers, and a repository where the feasibility probe fails is just the
case where every verdict stays at `STATIC`. §8.3's graceful degradation is then
structural rather than a promise, in the same way that running enumeration before
test discovery makes its test-blindness structural.

## Decision 8 — every attempt is recorded with a typed outcome

Following `UnjudgedPair` and `UnjudgedCause`, which record pairs that got no
verdict rather than dropping them, because a pair nothing can see is
indistinguishable from a verdict of *survives*. Mutation needs the same:

| outcome | meaning | tier reached |
|---|---|---|
| `killed` | a selected test went red | `DEFECT_KILLED` |
| `survived` | selected tests executed the span and none went red | `DEFECT_KILLED` |
| `unreached` | no candidate test executes the span | `COVERAGE_CONFIRMED` |
| `not_mutable` | no valid mutant could be constructed (Decision 3) | `STATIC` |
| `not_attempted` | the feasibility probe failed, or the defect is in the class below | `STATIC` |

`not_mutable` and `not_attempted` must carry a reason, for the same reason
`DefectSet` requires one on an empty set: "looked and could not" and "did not
look" are different, and only one of them is a defect in the tool.

## What injection cannot decide, measured

The premise that injection eventually supersedes the static pair judgement — the
argument in #171's comment, that one injection plus one suite run answers for
every test at once, so the static stage's cost per pair cannot be defended
against a runnable suite — holds for the pairs injection can reach. It does not
reach all of them, and the shape of the remainder is measured rather than
assumed. From `docs/experiments/coverage-prefilter/FINDINGS.md`, over #316's
Gate 2 review at head `3e1d3a9` — 48 defects, 496 tests, 23,808 pairs, 268
recorded kills:

- **Nine of the 48 defects had no usable code region at all**: seven named
  module-level regions, one named a non-Python file, one named lines that never
  execute.
- **Tests that fail through file reads rather than execution.** Tests asserting
  on README and decision-record text kill documentation defects without
  executing the implicated code. Line coverage cannot see that channel, and
  neither can a line-level mutation.
- **Absence defects.** For `not_wired`, `documented_not_implemented` and
  `missing_case`, the implicated lines are where behaviour *should* be, and a
  test can fail on the absence through code that lives elsewhere.

Those three classes stay on the static judgement permanently, on any repository,
whatever the probe says. They are separate from the repositories where execution
is unavailable, which is §8.3's case and is handled by Decision 7. The division
of labour: injection decides the pairs it can reach, and the static prediction
covers what injection cannot express, cannot run, or is not worth a suite run for.

## Consequences

- **No change to `defects/enumeration.py` or its response schema**, so no
  enumeration recordings are orphaned by this decision.
- **`PairVerdict` gains a tier field** (Decision 7), which is a review-state
  schema change and orphans nothing, since it is additive with a default.
- **A new record type for mutation attempts** (Decision 8), holding the
  descriptor, the mutant text, the outcome and the reason.
- **#44 (M8.3, the coverage-confirmed tier) owns the coverage map and the
  baseline run** that Decisions 4 and 6 depend on, which confirms the sequencing
  already recorded: M8.3 before M8.4.
- **#170 (the open decision on what declares a suite hermetic and fast enough)
  is unaffected by this record** and still has to be resolved before #42 (M8.1,
  the feasibility probe) is implemented.
- **The pilot case list already exists.** The coverage-prefilter experiment
  leaves 43 pairs where coverage and the static judge disagree, plus three from
  `prefilter-committee/`. Adjudicating them by injection measures pair-verdict
  accuracy against ground truth for the first time; #315's human-reviewed labels
  are the only current proxy.
