# Judgement — #232/#219/#230 bundle, Gate 1, run 1

Run at `eb182de`, task file as committed alongside. `decompose` recorded, then
replayed to capture. 24 requirements, 23 with obligations, 1 deliberately none.
**No open questions raised.**

**Gate 1 does not pass. The breakdown is not defensible.** Three classes of
finding, below.

## A. Every Completion expectation merged into its Constraint twin — #232, live

All five "A test asserts that …" expectations were derived as the behaviour and
then linked to the Constraint stating that same behaviour:

| Completion | merged into | obligation |
|---|---|---|
| `completion-02` | `constraint-01` | `acceptance-test-demand-is-test` |
| `completion-03` | `constraint-02` | `behaviour-and-test-not-same-requirement` |
| `completion-04` | `constraint-04` | `sibling-exclusions-same-disposition` |
| `completion-05` | `constraint-05` | `no-preserve-property-reason` |
| `completion-06` | `constraint-07` | `byte-identical-task-text-byte-identical-review-state` |

The resulting obligation set contains **no obligation that any test exist**. This
is #232 exactly — the defect firing on the task file written to fix it, five
times, and it is why the merge cannot be corrected in #144's linking prompt.

**Disposition:** attributed to #232, which is in this bundle's scope. Recorded as
evidence on the issue rather than filed anew.

**Consequence for the gate:** this task file cannot reach a clean Gate 1 while
the defect is unfixed, because every Completion expectation in this repo's
convention uses the framing the defect drops. Noted for the human; not worked
around.

## B. Four of six scope exclusions were inverted into obligations to do the excluded work

Six sibling bullets, one heading, all the same shape (`X, which is #N`):

| | disposition |
|---|---|
| `exclusion-01` (#148) | `human_review` — "remains outside the scope of this change" ✓ |
| `exclusion-02` (#205) | `human_review` — "remains a separate concern" ✓ |
| `exclusion-03` (#206) | `human_review` — **"Raise open questions only for materially underspecified requirements, and include what each question cites."** |
| `exclusion-04` (#117) | `invariant` — **"Split a single requirement into obligations at the level of distinct computations …"** |
| `exclusion-05` (#231) | `compatibility` — **"Keep obligation identifiers stable across task-file edits."** |
| `exclusion-06` (#211) | `explanation_observability` — **"Measure how accurate the decomposition is."** |

The last four are not merely inconsistent with their siblings, which is what
**#230** records. Their **sense is inverted**: "Whether obligation identifiers
are stable across task-file edits, which is #231" became an obligation to make
them stable — the work the bullet exists to exclude. Four different types across
six identically-shaped siblings.

This is strictly worse than #230 as filed. #230's two reframed exclusions became
*"Preserve the scope exclusion that X is out of scope"*, which at least preserves
the sense; these assert the excluded work as a requirement of this change.

**Disposition:** tool defect, in this bundle's scope (#230). Filing queued to
widen #230 with this run.

## C. The problem statement derived an obligation to implement the defect

`task-02` — prose describing the bug — yielded:

> `test-assertion-derives-behaviour-obligation` — "Derive an obligation stating
> the asserted behaviour from an acceptance criterion phrased as a test
> assertion, **without carrying forward the demand for a test**."

That is an obligation to perform the defect, and it directly contradicts
`constraint-01`/`acceptance-test-demand-is-test` in the same set. `task-01` and
`task-04` likewise became unsupportable generalities
(`mis-shape-two-text-kinds`, `predictable-derivation-for-both-text-kinds`) — the
same shape that left #144's Gate 2 with four unsupported obligations.

**Disposition:** split cause. The tool half is **#212** (context becomes a
requirement), filing queued. The other half is my wording: a Task section that
narrates a defect invites exactly this. Sanctioned rewrite proposed — state the
required behaviour, not the current misbehaviour.

## What is correct

`#144`'s linking pass behaved as designed throughout — the merges in A are
correct for the text it was shown, which is #232's point. `completion-01`
("Implementation") was declined with an accurate reason. `constraint-01..08`
each derived a faithful obligation.
