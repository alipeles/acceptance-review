# Decision Record 312 — Defect-first evidence

*Relates to issue #312, which supersedes #191 and replaces the premise of #173
(closed 2026-08-21 — the findings record is `DR-173-mapping-twin-splitting.md`).
Status: **all six decisions settled 2026-08-21 — 1, 2 and 5 ratified in
conversation; 3, 4 and 6 are #312's own Design section and settled with it.
The five post-filing questions below are resolved except two narrow residues
(taxonomy contents, #67 phrasing), each owned by a sub-issue. Nothing
implemented.** Drafted from the measurements in DR-173 and the code as of
`main` post-#265 (`908319b`). Track: checker. Stage: 1.*

---

## Context — the workflow's shape, not any stage's precision, is the defect

The evidence pipeline runs: map tests to obligations (`evidence/mapping.py`),
then per obligation-with-mapped-tests invent plausible defects and judge
whether the mapped tests would catch them (`evidence/discrimination.py`), then
reduce those verdicts to an evidence class (`evidence/strength.py`). Three
consequences, each with a measured instance:

1. **The mapping question is unanswerable as posed.** The mapping prompt's
   rubric — *"would this test be expected to FAIL if that obligation's behavior
   were missing or wrong?"* — is a defect counterfactual with no defect in
   hand. Read strictly it rejects on-point tests (#173's original instance);
   *"or wrong"* read loosely admits anything nearby (the eleven disposition
   tests mapped to the foreign-id-filter obligation). The module's own
   docstring assigns strength judgement to M5 and the prompt asks a
   strength-shaped question anyway. DR-173 then showed the deeper problem:
   even where the model answers this question well (80% of draws on the
   disputed pairing), the pipeline stores one draw as the finding.
2. **A mapping miss is unrecoverable.** Discrimination never sees a test that
   mapping dropped, so the recommendation stage prescribes tests that already
   exist (#250, #287); #293 shipped with Gate 2 deliberately not clean because
   no honest change could satisfy such a finding.
3. **The strength denominator is self-serving.** `strongly_supported` is
   `caught == total` over defects the same call enumerated (#252), so
   enumerating fewer defects earns a stronger rating. Adjacent: a prescribed
   test's target defect need not violate the obligation (#283), and an
   obligation true by construction earns a defect that cannot exist (#270).

DR-173 closed the door on fixing this inside the current shape: prompt wording
is a well-powered null (1,472 calls), the obligation id carries no weight, and
the one structural variant piloted (a forced per-obligation verdict) cut
splits by destroying 59% of correct mappings.

## The shape after the change

```
before:  obligations ──► map tests→obligations ──► invent+judge defects ──► reduce
after:   obligations ──► enumerate defects ──► map tests→defects ──► derive support
```

Defects stop being a transient artifact of one call and become persisted,
identified review state, created before any test is looked at. The question
asked about a test becomes concrete and existential — *would this test fail if
the implementation contained this defect?* — and obligation support becomes a
join over data rather than a judgement.

## Decisions

**1. Defect enumeration is an independent, persisted stage.** *(Ratified.)*
Per obligation, the enumerator produces typed, identified defect records: id,
obligation id, description, implicated code region. They persist in review
state exactly as obligations do, and every downstream consumer — pair mapping,
support derivation, recommendations, M8.4 mutation — references them by id.
An empty enumeration is a valid output for an obligation with no plausible
static defect (#270), recorded with its reason rather than forced.

**2. The enumerator sees the obligation and the changed code, never the
tests.** *(Ratified.)* Sighting the code is what makes each defect concrete
enough to name lines — the precondition for serving as an M8.4 mutation spec
(#171, spec §8.2) and for the reachability prefilter in decision 3.
Test-blindness is the #252 mitigation: an enumerator that can see what is
already covered drifts its denominator toward it, and the gaming the rating
invites moves from "enumerate fewer" to "enumerate what's caught" — same
defect, new door.

*Rejected: fully blind enumeration* (obligation text only). It maximizes
independence but yields defects too generic to anchor to lines, which forfeits
both the prefilter and the mutation-spec reuse, and it invites defects about
code that does not exist. The independence that matters is from the *tests*,
and decision 2 keeps exactly that.

**3. Tests are mapped to defects, per (defect, test) pair.** *(Settled —
#312's Design section.)* The
test-to-obligation mapping stage is retired; *"purports to evidence"* retires
with it. Each judged pair answers the kill question above. Pairs are
prefiltered by reachability — a test that cannot reach a defect's implicated
region is not judged, and the exclusion is recorded, not silent (the lesson of
DR-164's silent id filter; the linking stage's pair prefilter, DR-259, is the
in-repo precedent for judging only pairs that pass a cheap gate). Batching
respects DR-164's shedding limit of roughly a thousand judgements per call.

Two DR-173 findings are binding constraints here, not background:

- **The recall guard.** The per-obligation-verdict pilot improved its headline
  number by answering *no* more often, losing 91 of 153 correct mappings.
  Asked in isolation, the model defaults to no. Any pilot of the pair shape is
  scored on recall as well as its headline metric, with a guard metric (mean
  predicted kills per defect, the analogue of DR-173's mean ids per test), and
  rejected if recall falls below the control.
- **The response must not grow.** The caching discount is input-only; the
  failed pilot's 2.5× output growth never amortized. The pair verdict's
  response carries the minimum — pair id and verdict, a short reason — and any
  richer explanation belongs to a later, per-finding call, not the sweep.

*Rejected: the recall-preserving second pass* (DR-173's one design left
standing — keep the list-shaped call, then offer the model the obligations it
did not map and union what it accepts). It is monotone and cheap, but it
patches the split symptom while leaving everything this DR exists to fix:
the unanswerable question, the unrecoverable miss, the self-serving
denominator, and a mapping with no carry unit. It remains available as a
stopgap on the old shape if #312 stalls; it is not the destination.

**4. Obligation support is a derived join with a disclosed denominator.**
*(Settled — #312's Design section.)* An
obligation's evidence class reduces over its own defects: every enumerated
defect predicted killed by some reachable test → strongly supported at the
static tier; some → partially; none, with tests present → nominally; and the
existing classes for no-test and indeterminate cases. The report always shows
the denominator — *"3 of 5 enumerated defects"* — never a bare class, and the
class name never claims more than the enumeration supports (wording owned by
#67). Test-to-obligation linkage survives for the report as a derived edge
(test → defect → obligation), which also keeps DR-173's label-free
`twin_splitting` metric computable over the derived edges as a regression
check. A recommendation is literally an uncovered defect — the §9.5 payload
falls out of the data model — which makes #283's shape unrepresentable: every
recommendation cites a defect record whose violation links to its obligation's
text.

**5. A changed obligation re-enumerates its defect set wholesale.**
*(Ratified.)* No partial patching of a defect set against an edited
obligation: carrying pair verdicts over a moved denominator is #269's mistake
— judgements carried over a re-derived, re-identified set — in new clothes.

**6. All three steps implement the carry contract (#286) from birth,**
*(settled — #312's Design section)* in the
DR-293 pattern: content-level comparison, per-unit digests stored by the run
that judged them, conservative on absence. The units:

| carried thing | carries while | invalidated by |
|---|---|---|
| an obligation's defect set | its obligation and the contents of its implicated code region are unchanged | any edit to either; re-enumerates wholesale (decision 5) |
| a (defect, test) pair verdict | the defect and the test's source digest are unchanged | either moving; per-test digests, never per-file (DR-293) |
| the derived support class | always recomputed — it is free arithmetic over carried parts | n/a |

The carry keys exclude neighbouring context, per DR-269: a pair's key must not
move because an unrelated pair entered the same batch. The headline behavior,
which is an acceptance check on #312: **a user who adds one test between two
`--continue`d runs pays for judging the new test's pairs against the open
defects — nothing else.** This is also the honest response to DR-173's
1-in-5 draw variance: carry confines fresh variance to judgements actually
being made for the first time, and #150 remains the issue for what variance
survives that.

## What this dissolves, and what it does not

Dissolved structurally: the necessary/sufficient ambiguity in the mapping
question; the unrecoverable mapping miss; recommendations that restate their
own evidence (#250, #287); recommendations targeting non-violations (#283).

Not fixed, stated so nobody expects it: twin obligations (#304) still reach
the enumerator unmerged and will enumerate overlapping defect sets — whether
twins should *share* defect identity, which would make the twin-split
harmless, is open below. Provider variance on any single fresh judgement
remains (#150). #252 is mitigated — separation, test-blindness, disclosure,
and a benchmark that scores enumeration recall against labelled defect sets
separately from pair-verdict accuracy — not eliminated; the enumerator is
still a model producing its own denominator.

## Costs, stated up front

- **Every touched stage's transcripts orphan.** #265 already orphaned the
  whole corpus at `908319b`, so the marginal cost right now is zero — this
  window is an argument for sequencing #312 before new recordings accumulate.
  Benchmark figures will not span the change; mapping-accuracy and
  evidence-classification figures measure different questions after it, the
  same disclosure DR-164 made.
- **More judgements.** Pairs (defects × tests within reach) outnumber the old
  test-per-call judgements. The prefilter and DR-164-bounded batching are the
  controls; a pilot reports cost per review alongside recall.
- **Benchmark labelling grows.** M-B5a.2's ground truth extends to expected
  defect sets per archetype fixture, human-reviewed. That is the price of
  separating "the enumerator missed the defect" from "the judge missed the
  kill" — the two failures the current design cannot tell apart.

## The five post-filing questions, resolved 2026-08-21

All five were open when #312 was filed (the issue lists three; taxonomy and
migration surfaced while drafting this DR). Resolved by the human in
conversation, recorded here; the issue comment points at this section.

1. **Defect identity: strictly per-obligation; duplicates allowed, for now.**
   De-duplication of obligations has been thorny and incompletely effective
   (#242 — one spurious link blocks a whole merge; #304 — twins silently
   unmerged; the linking stage generally), and a second dedup mechanism is
   not wanted on the critical path. Twin obligations therefore enumerate
   duplicate defects and pay duplicate pair judgements — an accepted,
   bounded cost, watched by the `twin_splitting` metric over the derived
   test→obligation edges. Revisit only if #304 lands an upstream merge.
2. **Prefilter: no exclusion without proof — and no reachability build
   inside B.** *(Amended 2026-08-21. The original text claimed the prefilter
   could reuse M4.1 discovery's "call graph". A code check found
   `discovery.py` is one-hop name and import overlap — it can report a
   positive match, it cannot prove a static path absent. The claim was taken
   from the module's docstring without verifying the implementation; the
   amendment records what is actually there.)*
   The rule stands: include unless a static path is provably absent;
   indeterminate includes; every exclusion records defect id, test id and
   reason. Its consequence is now stated plainly — under today's machinery
   almost nothing is provably absent, so the prefilter excludes almost
   nothing and tractability rests on batching plus the pilot's measured cost
   figure. That is accepted, for the failure-asymmetry reason: a wrong
   exclusion silently un-covers a defect and re-creates the
   prescribe-a-test-that-already-exists failure (#250/#287, #173's
   gate-unreachable shape) — the exact thing #312 exists to kill — while a
   missing prefilter only costs money, which the pilot measures. Building
   real reachability (name resolution, transitive edges) is deliberately
   **not** part of B: it is a known tar pit in Python (dynamic dispatch,
   fixtures, pytest indirection), it would put an unvalidated component in
   front of the judge, and M8.3's coverage tier audits reachability honestly
   when execution arrives — an excluded pair observed covered is a prefilter
   defect, surfaced rather than silent. If B's pilot shows unacceptable
   cost, reachability becomes its own issue, justified by that figure.
   Coverage-signal prefiltering stays rejected for Stage 1 (execution is
   optional and probe-gated, §8.3).
   **B's Gate 1 question is therefore not "build a graph?" but the response
   shape.** Sparse — each test lists the defects it would kill; absence
   means survives; output stays small and it is the list shape the model
   handles today — but shedding is invisible, and a shed judgement reads as
   *survives*, which un-covers a defect silently (DR-164's trap). Dense — a
   verdict per offered defect; shedding is visible through the
   unanswered-id machinery `mapping.py` already has — but it is the shape
   that lost 59% of correct mappings in DR-173's pilot, and it grows
   output, which never amortizes. Pilot both arms; score recall, shedding
   visibility and cost; the guard metric decides. Armchair-resolving this
   one is what DR-173 exists to forbid.
3. **Rating wording: keep the §9.3 class names, bind every rendering to the
   denominator, no numeric floor.** The class names are spec vocabulary and
   churn would cost every consumer at once. Every rendering carries the
   denominator — *"strongly supported — kills 5 of 5 enumerated defects
   (static prediction)"* — including the honest thin case, *"1 of 1"*. A
   minimum-enumeration floor for `strongly_supported` is rejected: any
   threshold is arbitrary, invites gaming in the opposite direction, and the
   disclosed denominator lets the reader weigh a thin enumeration
   themselves. A reasoned-empty enumeration gets its own terminal state —
   never `strongly_supported`, never `unsupported` — rendered as *"no
   plausible static defect enumerated; test evidence is not obtainable at
   this tier"*. Final phrasing folds into #67's rubric work.
4. **The defect taxonomy is hybrid: checklist-guided with a free-text
   escape.** The shape
   is settled: the enumerator walks a per-obligation-type defect checklist
   (qualifier ignored, boundary wrong-side, condition inverted, error
   swallowed, …) and may return a defect typed `other` with a free
   description where nothing fits. The checklist is where a taxonomy earns
   its keep — walked in the prompt, it drives enumeration recall the way any
   checklist does — while the escape stops odd defects being forced into the
   nearest slot. Every defect's *description* is free text regardless; the
   type is classification only, and nothing downstream (prefilter, pair
   mapping, M8.4 mutation) depends on it, so the escape costs nothing but
   per-type scoring granularity on the defects that use it. Still open, and
   still ahead of label-writing: the taxonomy's contents per obligation
   type (owned by the enumeration sub-issue's Gate 1, ahead of any M-B5a.2
   label being written); how M-B5a.2 labels and scores `other`-typed defects
   (the benchmark's alignment scoring of free-text items is the in-repo
   precedent); and the `other` share as a standing metric — a rising share
   is a taxonomy gap, a near-zero share alongside poor enumeration recall is
   Procrustean fitting.
5. **Migration is staged.** The carry-reuse argument that decided it: the
   new stages adopt a live, tested mechanism
   (DR-293's per-unit digests and keys, #269's ledger), and carry
   correctness is only checkable by counterfactual runs — edit one input,
   assert exactly what re-derives. Those assertions are only *attributable*
   while the surrounding pipeline is fixed. Land pair mapping in shadow
   behind the old support derivation and a carry defect shows up as a
   discrepancy against a stable baseline; land everything at once and an
   unexpected rating move has three candidate causes — new question, new
   denominator, carry wiring — with nothing to attribute it to, which is
   #149's untraceable-conclusion problem arriving inside our own migration.
   Staged also fits one-issue-per-PR: each carry unit is a small diff
   against a working mechanism. The counter-argument stands: each landing
   after the first moves request keys again and orphans recordings again —
   #265 makes the first landing free, not the later ones — and was accepted
   as the price of attributability. The cost is likely smaller than it
   reads: shadow-mode recordings may survive the flip, since if cutting over
   changes nothing in the new stages' own requests, their corpus replays and
   only the retired stages' recordings die with them. **Verifying that is
   the first task of the cutover sub-issue**, and the cutover is sequenced
   to touch the new stages' requests as little as possible for exactly this
   reason. The sub-issue seams implementing this decision are the split
   below.

## Remaining open

Two residues, each with an owner: the taxonomy's per-obligation-type
contents (the enumeration sub-issue's Gate 1, before M-B5a.2 labels exist),
and the final rating phrasing under the disclosed denominator (#67).

## The sub-issue split

Four issues, deliberately large per the human's preference (2026-08-21),
implementing decision 5's staged migration. **None are filed as of this
writing.** The Claude Code session that files them should also post the
resolutions comment on #312 (pointing at "The five post-filing questions"
above) and fix #312's body, where the DR filename reads
`DR--defect-first-evidence.md` — a `<this issue>` placeholder GitHub
swallowed as a tag. Sub-issue attachment to #312 happens at filing.

| | issue | labels | blocked by |
|---|---|---|---|
| A | Defect records and the enumeration stage | `track:checker` | — |
| B | Pair mapping in shadow, with the reachability prefilter | `track:checker` | A |
| C | Cutover: derived support, recommendations from uncovered defects, retirement of the old stages | `track:checker` | B |
| D | Benchmark: defect-set ground truth and scoring | `track:benchmark`, `human-gate` | A's Gate 1 (taxonomy) |

D runs parallel to B and **should land before C**: the cutover decision
deserves to see the scored pilot, not just the shadow comparison. C carries
an internal seam — (C1) flip the verdict source, (C2) retire the old stages
— to be split **only if** it cannot reach Gate 2 in one session; do not
pre-split it.

### A — Defect records and the enumeration stage

*Inputs:* this DR (decisions 1, 2, 5, 6; resolved questions 1, 4); the
obligation model in `review_state.py` as the pattern for persisted,
identified records; the carry contract (#286) as built in DR-293/DR-269.

*Deliverable:* the `Defect` model — id, obligation id, type (taxonomy or
`other`), free-text description, implicated code region — persisted in
review state. The enumeration stage: per obligation, sees the obligation and
the changed code, never the tests; walks the per-obligation-type checklist
in the prompt with the `other` escape; a reasoned empty set is a valid
output. Defect-set carry: a set carries while its obligation text and
implicated-region contents are unchanged; a changed obligation re-enumerates
wholesale. Ledger integration so `--continue` carries defect sets. A report
section rendering enumerated defects, advisory only — the verdict is
unchanged by this issue. **The taxonomy's per-obligation-type contents are
decided at this issue's Gate 1**, ahead of any M-B5a.2 label being written.

*Acceptance:*
- On the §9.1 floating-rate example, each derived criterion enumerates ≥1
  typed defect or records a reasoned empty set; archetype #4's
  non-discriminating-input defect appears in its criterion's set.
- An obligation true by construction (#270's shape) yields a reasoned empty
  set, not an invented defect.
- On two `--continue`d runs with one obligation reworded, only that
  obligation's set re-enumerates (transcript count asserted).
- Two recorded runs over the same input are byte-identical; existing report
  output is unchanged except the new advisory section.

### B — Pair mapping in shadow, with the reachability prefilter

*Inputs:* defect records from A; `discovery.py`'s symbol and import
overlap — one-hop, not a call graph; it reports positive matches and cannot
prove path absence (resolved question 2's amendment); the DR-164 shedding
limit; DR-173's recall guard ruling.

*Deliverable:* the static reachability prefilter — per (defect, test) pair,
include unless a static path is provably absent, indeterminate includes,
every exclusion recorded (defect id, test id, reason). The pair-mapping
stage: per surviving pair, *would this test fail if the implementation
contained this defect?* — batched under the shedding limit, minimal response
shape (verdict plus short reason; no per-pair prose). Pair-verdict carry: a
verdict carries while the defect and the test's source digest are unchanged
(per-test digests, DR-293). **Shadow mode:** the stage runs and records but
nothing consumes it — the existing mapping/discrimination/strength chain
still produces the verdict. A comparison report: support derived from pairs
vs. the current ratings, per obligation, discrepancies listed. Pilot
figures: recall against the current stage's shared-mapping count, mean
predicted kills per defect (the guard), cost per review.

*Acceptance:*
- Adding one test between two `--continue`d runs issues new judgements only
  for pairs involving that test (transcript count asserted).
- Prefilter exclusions are recorded and rendered; a fixture with an
  unreachable test shows the exclusion, not a judged pair.
- The pilot report includes recall, guard and cost; recall below the current
  stage's control is a stop per DR-173 — reported, not negotiated.
- Two recorded runs byte-identical; the review's verdict is untouched.

### C — Cutover: derived support, recommendations from uncovered defects, retirement of the old stages

*Inputs:* A and B live; this DR (decision 4; resolved questions 3, 5); the
#292/DR-293 anchoring machinery; D's scored pilot where available.

**First task, before any code: verify shadow-corpus survival** — that
flipping the consumer changes nothing in the new stages' own requests, so
their recorded corpus replays across the flip (resolved question 5). If it
does not hold, stop and re-present the migration cost.

*Deliverable:* evidence class as a deterministic join over pair verdicts
with the disclosed denominator ("kills 3 of 5 enumerated defects"), the
reasoned-empty terminal state, and the honest "1 of 1" rendering.
Recommendations become uncovered defects — the §9.5 structured payload
emitted from defect records. Retirement of the test→obligation mapping stage
and the discrimination stage; #292's anchored re-judgement re-scoped or
retired (pair-digest carry may subsume it — decide and record here in
DR-312). Report and verdict rewiring; the carried-recommendations pathway
moves to the defect axis.

*Acceptance:*
- Archetype #4: the criterion cannot reach strongly-supported while its
  on-point defect's pair verdict is *survives*.
- #283's shape is unrepresentable: every recommendation cites a defect
  record whose violation links to its obligation's text; #250/#287's shape
  (a recommendation restating cited evidence) has a regression test.
- Every rated criterion renders its denominator; reasoned-empty renders its
  own state, never strongly or unsupported.
- Two recorded runs byte-identical; the benchmark-comparability disclosure
  (figures do not span the cutover) is recorded where the numbers render.

### D — Benchmark: defect-set ground truth and scoring

*Inputs:* the taxonomy from A's Gate 1; the archetype fixtures (M-B5a.1);
the benchmark's alignment scoring as the precedent for matching free-text
items to labels. Extends M-B5a.2. `human-gate`: labels need review.

*Deliverable:* a label format for expected defect sets per archetype case,
typed against the taxonomy with `other` allowed; human-reviewed labels for
the §13.5 cases; metrics: enumeration recall (per type), pair-verdict
accuracy against labelled kills, the `other` share, and `twin_splitting`
recomputed over the derived test→obligation edges as the regression check.

*Acceptance:*
- Each archetype case carries a reviewed defect-set label that validates.
- Scoring runs off recorded transcripts, no live calls; on a synthetic set
  with known labels, computed metrics match hand-calculated values.
- Enumeration recall and pair-verdict accuracy report as separate figures —
  the separation is the point (#252).

## Related

- `DR-173-mapping-twin-splitting.md` — the measurements this design answers;
  its §3 rulings (prompt wording, id weight, forced verdicts) are treated as
  settled here.
- `DR-164-mapping-stage-request-partitioning.md` — shedding limit, silent
  filter lesson, partitioning cost model.
- `DR-293-per-axis-carry.md`, `DR-269-carry-key-excludes-registry-context.md`
  — the carry pattern and key discipline decision 6 adopts.
- `DR-259-obligation-pair-prefilter.md` — precedent for prefiltered pair
  judgement.
- Issues: #312 (this design), #191 (superseded), #182/#183 (umbrellas),
  #286 (carry contract), #150 (stability), #304 (twins), #171 (mutation
  specs), #252/#283/#270 (denominator family), #67 (severity wording).
