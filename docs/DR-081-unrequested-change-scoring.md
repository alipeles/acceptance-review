# Decision Record 081 — Scoring and disposition for unrequested-change findings

*Resolves issue #81 ("Unrequested-change findings have no scoring metric (§11.1)"). Status: accepted. Track: benchmark + checker. Stage: 1, with two items explicitly deferred to Stage 2.*

---

## Context

M3.2 detects **unrequested changes** — diff regions that correspond to no obligation (§9.2). M3.3 wires findings into `Review.findings` for benchmark scoring. The M3.3 dogfood run (`acceptance classify`) correctly flagged the scoring hook as only *partially addressed*, which surfaced the gap: every §11.1 metric is anchored on the obligation (a gap **is** an obligation with no matching code, so it carries `related_obligation`), but an unrequested change is by design obligation-*less* — it is code with no matching requirement. So `unrequested_change` findings are emitted but are structurally invisible to every existing metric. Archetype #8 still produces a gap_recall/precision number, but via its leave-existing obligation's coverage classification, **not** via the unrequested-change detection itself — which masks that the detector is unmeasured.

Working through the fix surfaced two further dimensions hidden inside what looked like a single boolean finding. This record captures all three.

## The core insight: the review has two axes, not one

The reviewer does two different jobs that look like one:

- **Obligation → code** ("is every requirement delivered?"). A **gap** lives here: an obligation with no matching code. Scored today.
- **Code → obligation** ("does every change trace to a requirement?"). An **unrequested change** lives here: code with no matching obligation. Unscored.

These are duals, not the same task. The positive being detected is a different *kind* of object, so folding unrequested changes into the gap metric (issue #81, option 2) would average two distinct error types into one number and destroy the ability to say anything true about either. **Two axes require two scores.**

## Decisions

### 1. Score unrequested-change detection as its own precision/recall pair

Add an `unrequested_precision` / `unrequested_recall` metric to `scoring.py`, a sibling of the gap metric on the code→obligation axis:

- **Recall** — of the changes that genuinely shouldn't be in this change set, how many did the tool flag?
- **Precision** — of the changes the tool flagged, how many were genuinely unrequested (vs. legitimate incidental edits)?

Ground truth is the set of diff regions **not** explained by any obligation. Match obligation-less findings against obligation-less ground-truth changes; do not attempt to link them to obligations.

### 2. Score on the archetype layer now; defer real-change scoring for Stage 1 (documented)

The metric is trivial; the **ground truth is the hard part**. On hand-built archetypes (#8 and siblings) the label is unambiguous — we planted the change. On real data (SWE-bench), a gold PR is "all requested" relative to the issue *except* for the incidental refactors and drive-by edits real PRs always contain, which aren't in the issue text but aren't defects either. Labeling those as "unrequested" is a judgment about **intent**, which can't be auto-derived.

Therefore: score unrequested-change detection on the **archetype layer only** in Stage 1. Real-change scoring is **explicitly deferred** (not silently dropped), because honest labeling requires human judgment and, in its strongest form, the PR↔backlog linkage that only arrives in Stage 2 (Mode B). This is a conscious Stage-1 boundary with rationale, satisfying #81's "documented decision" acceptance.

### 3. Detection is recall-forward; precision is reported, not optimized against

Because the tool cannot see intent, it should **bias toward recall** — surface every change nothing asked for and let the user dismiss the fine ones — rather than cleverly suppressing "probably okay" changes and risking silently dropping a real one. This is deliberate: silent, unrelated changes are a signature failure mode of coding agents and one of the tool's differentiated value props, precisely because tests don't catch them (early or additive changes have no prior behavior to regress). High recall is only safe if false positives are cheap to dismiss — which is what decision 5 (framing) buys. Precision is still **measured and reported** (we want to know the false-alarm rate), it just isn't the axis the product's behavior is tuned around.

### 4. Model an explicit disposition on every unrequested-change finding

"Unrequested change" is not a verdict; it's a bucket that needs a **disposition**:

- **`in_service`** — a refactor/interface tweak made to deliver an obligation. Accept, optionally note.
- **`separable`** — coherent, possibly valuable, but a distinct unit of work. → *"Split into its own PR / backlog item."* (This is the disciplined-manager pushback: high value does not excuse bundling separate work into an unrelated PR.)
- **`risky`** — touches public surface, dependencies, or adjacent behavior in a way that could hide a regression. → *"Scrutinize."*

`separable` and `risky` are not exclusive, and `separable` is orthogonal to `value`.

**Separability litmus (derivable from existing machinery):** *Would the task still be complete if this change were removed?* We already compute obligation→code coverage, so a changed region that no obligation depends on is removable without affecting completion → `separable`; a region some obligation's coverage relies on → `in_service`. Sharpen with cheap signals: introduces new self-contained public surface (function/class/module) vs. edits code on an obligation's path; ships its own distinct tests; lives in files disjoint from the obligation-mapped ones.

Where the acceptable-expansion line sits is a **shop norm**, so disposition thresholds are a **policy knob** (strict vs. loose), not a hardcoded verdict. The strongest "should be its own backlog item" phrasing wants the backlog as an input; in Stage 1 (task file only) the finding reads "separable from the mandate — consider splitting," sharpening to "own backlog item" in Stage 2.

### 5. Present unrequested-change findings as advisory — high importance, low certainty

Separate two things the "evidence tier" concept previously blurred: **how sure** the tool is, and **how much the user should care**. Unrequested changes are **low certainty** (the tool sees a change with no obligation, not the author's intent) but **high importance** (silent scope creep is exactly what slips past tests and reviewers). So surface them prominently but framed as *"here's what changed that no obligation explains — your call,"* not *"this is wrong."* Honest framing is what makes aggressive recall (decision 3) safe: cheap-to-dismiss false positives don't erode trust.

## Consequences / scope

**In Stage 1 (resolve now, in the pre-M4 cleanup pass):** the metric (decision 1, archetype layer), the disposition field + separability classification (decision 4), expanded unrequested-change archetypes, the advisory presentation (decision 5, lands with M7 CLI output), and the spec/plan updates recording the two-axis frame.

**Deferred to Stage 2 / benchmark backlog:** per-disposition scoring accuracy; real-change unrequested-change labeling; the "own backlog item" finding in its strongest form (needs PR↔issue linkage).

## Meta-lesson (worth recording in the spec)

The tool found a genuine asymmetry in its own conceptual model — obligation-anchored scoring cannot see code-without-obligation — and each pass at the fix uncovered another hidden dimension (measurement → confidence-vs-importance → disposition). Two takeaways: (a) the review has **two axes**, and any future capability should be checked against both; (b) this validates **dogfooding as a design practice**, not just QA. The benchmark's difficulty labeling "unrequested" is the *same* difficulty the user faces triaging the flags — a reason to keep this finding type advisory.
