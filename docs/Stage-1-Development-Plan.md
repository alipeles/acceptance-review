# Stage 1 Development Plan — Local Completion Checker + Validation Benchmark

*Companion to the spec (`AI-Assisted-Software-Development-Review-Spec.md`). The spec defines **what** the product is and **why**; this plan defines **how Stage 1 gets built** — sequencing, milestone breakdown, agent-ready tasks, and exit criteria. Section references (§) point at the spec. Where the spec defers a decision to "the development plan," this document resolves it.*

*Date: 2026-07-17 · Stage: 1 of 2 (MVP) · Status: not started*

---

## 1. Scope of Stage 1

Stage 1 delivers the **first milestone of the MVP**: a working **Local Completion Checker** (§13.3) *and* the **validation benchmark and harness** (§11) that measures whether the checker actually works. Per §13.1 the checker and its benchmark are one milestone, independently useful, and the primary evidence the product does what it claims. GitHub Acceptance Review (Stage 2, §13.4) is explicitly out of scope here.

**In scope**

- Local Completion Checker end to end: task ingestion → obligation decomposition → Git change analysis → implementation-coverage analysis → test discovery/mapping → test-semantic analysis → optional builder-declaration comparison → completion result with structured recommendations and a next instruction (§13.3, §9, §10.1, §16).
- The **optional execution tier** (§8): feasibility detection, sandboxed coverage-confirmation, targeted hypothesis-driven mutation, and closing the recommendation loop — enabled only where the project's pytest suite runs hermetically, degrading silently to static otherwise (§8.3).
- The **validation benchmark + harness** (§11): case schema, scoring metrics, dataset ingestion across the layered sources (§11.2), and a reproducible accuracy report.
- The **local demonstration scenarios** (§13.5, items 1–9, plus 14 where execution ships) as both capability tests and the archetype benchmark layer (§11.2).

**Out of scope (Stage 1 non-goals, from §13.3 / §13.7)**

GitHub access; agent-session integration; modifying code or writing production-ready tests; managing tasks/backlog; provisioning environments the project doesn't already support; running arbitrary or non-hermetic suites; proving runtime correctness or formal verification. Running the project's *own* hermetic tests for targeted confirmation **is** in scope; standing up new environments is not.

---

## 2. Definition of done (Stage 1)

Stage 1 is complete when all of the following hold. These operationalize §13.6 (local quality, measured accuracy, trustworthiness).

1. **Runs from stable artifacts only.** `acceptance check --task … --base … --head …` produces a structured, inspectable review from a task file + Git revisions + repo source/tests, with no GitHub App, hosted service, CI access, or agent history (§3.1, §5.1).
2. **Every conclusion is typed and linked.** Each finding carries an evidence tier (§8.1) and links to exact requirement text, code lines, and/or test locations. Inferred obligations and static predictions are labeled as such (§2.5, §13.6 trustworthiness).
3. **The nine local demo scenarios pass** (§13.5 #1–9): the checker produces the expected, defensible finding for each, with explanations a developer accepts.
4. **Measured accuracy is reportable.** The benchmark harness emits gap-detection (recall) and false-alarm (precision) rates, decomposition accuracy, and test-to-obligation mapping accuracy over a real-change dataset, plus static-vs-executed classification agreement where execution is available (§11.1). Figures are reproducible from a single command.
5. **Execution tier works where feasible and degrades silently where not** (§8.3), and a recommended test is confirmed to kill its target defect before its gap is marked closed (§8.4).
6. **Confidence is honestly bounded.** A positive local result is presented as "no material gaps found at the achievable evidence tier," never as proof of correctness (§3.7).

---

## 3. Guiding constraints and key decisions

Per the chosen tech depth, this plan fixes **constraints and the decisions each milestone must resolve**, not specific libraries.

### 3.1 Fixed constraints

- **Language/runtime under review:** Python; test framework pytest; VCS Git; requirement input as Markdown task files and (optional) Markdown builder declarations (§13.2). The *tool itself* may be written in any language, but Python is the pragmatic default given it must parse Python ASTs and drive pytest.
- **Coding-agent independence (§3.1, §4):** the checker consumes only task text, Git revisions, source, tests, and an optional declaration. No dependency on any specific agent, prompt history, or hosted service.
- **Evidence discipline (§8):** every conclusion records its achieved tier; a static inference is never rendered as execution-confirmed. This is a data-model invariant, not a presentation choice.
- **Structured, inspectable review state (§12):** obligations, mappings, findings, tiers, and open questions are explicit persisted state — not an unstructured model conversation — so conclusions link to evidence and reviews re-run incrementally.
- **Execution safety (§8.3, §17):** any execution runs in an isolated sandbox with no network or secrets, on targeted test subsets only, within a short time budget, skipped when feasibility checks fail.
- **Reproducibility of measurement (§11):** benchmark runs are deterministic enough to report stable accuracy figures; model nondeterminism must be controlled or averaged and disclosed.
- **Cost/latency awareness (§17):** analyze changed and semantically relevant files first; cache stable analysis; support a fast preliminary pass before deep review.

### 3.2 Key decisions to resolve (owned by the milestone noted)

- **LLM orchestration boundary** — which judgments are model calls vs. deterministic code, and how model I/O is schema-constrained and recorded for replay. *(M0)*
- **Determinism strategy** — fixed seeds/temperature, cached transcripts, or N-sample majority with disclosed variance. *(M0 / benchmark M-B0)*
- **Obligation schema** — the concrete typed fields (§7.3, §9.1, §15) and how explicit/inferred/ambiguous is represented. *(M1)*
- **Code-context retrieval** — how much surrounding code and which cross-references are pulled per obligation, and the budget that bounds it (§12 autonomous gathering vs. §17 cost). *(M2/M3)*
- **Test-strength rubric** — the concrete criteria list from §9.3 turned into a scored, explainable classification. *(M5)*
- **Mutation targeting** — how a named plausible defect maps to exact lines and a concrete code mutation (§8.2). *(M8)*
- **Feasibility probe** — what signals declare a suite "hermetic and fast enough" (§8.3). *(M8)*
- **Benchmark dataset selection & licensing** — *resolved; see §10.* Primary base layer is **SWE-bench Verified** (500 human-validated instances); **BugsInPy** (~500 reproducible bugs) backs the offline-mutant and execution layers. Remaining action is confirming per-repo licenses and BugsInPy's licensing status before any redistribution. *(M-B1)*
- **Unrequested-change scoring & disposition** — *resolved; see DR-081.* Score unrequested-change detection as its own precision/recall axis (not folded into the gap metric), on the archetype layer in Stage 1 with real-change scoring deferred; model an explicit disposition (in-service / separable / risky) with a strict/loose policy knob; present findings as advisory. *(M3.5; the advisory presentation itself lands with M7.6.)*

---

## 4. Architecture at a glance (constraint level)

A single analysis engine (§5) with an inspectable review-state store at its center. Components map directly to §13.3 capabilities and the §15 data model.

```
                       ┌───────────────────────────┐
  task file  ───────▶  │  Requirement interpreter  │──▶ Obligations
  (§7.1)               │        (M1, §7.3/§9.1)    │    (typed, explicit/inferred)
                       └───────────────────────────┘
  git base/head ─────▶  Change analyzer (M2, §13.3) ──▶ Change set (diffs, config)
  source/tests
                       ┌───────────────────────────┐
                       │  Coverage analyzer (M3)   │──▶ Obligation×diff classification
                       │  Test discovery/map (M4)  │──▶ Test↔obligation map      + unrequested changes
                       │  Test semantic anlys (M5) │──▶ Evidence classifications
                       └───────────────────────────┘
  declaration ──────▶   Declaration comparator (M6) ──▶ Discrepancy findings
  (optional, §7.4)
                       ┌───────────────────────────┐
                       │  Execution tier (M8, §8)  │──▶ coverage-confirmed / defect-killed tiers
                       │   feasibility→sandbox→     │
                       │   coverage→mutation        │
                       └───────────────────────────┘
                                   │
                                   ▼
             Review-state store  ──▶  Completion result + recommendations + next instruction
             (obligations, mappings, findings, tiers, open Qs — §12, §15)   (M7, §9.5, §16)

  ┌──────────────────────────────────────────────────────────────────────┐
  │  Validation benchmark & harness (M-B*, §11): case schema, dataset      │
  │  ingestion, checker-under-test runner, scoring, accuracy report        │
  └──────────────────────────────────────────────────────────────────────┘
```

The **review-state store** implements the §15 conceptual data model (Project, Task source, Mandate interpretation, Builder declaration, Change set, Obligation/criterion, Test evidence, Execution evidence, Finding, Review, Benchmark case). Building it first (M0) is what lets every later component write typed, linked, tiered findings rather than free text.

---

## 5. Milestone sequence and rationale

Two tracks — the **Checker (M)** and the **Benchmark (M-B)** — are interleaved, not sequential. The benchmark must exist early enough to drive checker development against ground truth, but needs a minimal checker to score. The archetype scenarios (§13.5) are the bridge: they are cheap, hand-built ground truth that also serve as the checker's first acceptance tests.

| Order | Milestone | Depends on | Why here |
|---|---|---|---|
| 1 | **M0** Foundations & walking skeleton | — | Review-state store + evidence-tier primitives + LLM-orchestration harness must precede all typed findings. |
| 2 | **M-B0** Benchmark harness & case schema | M0 | Same data shapes as the checker; define scoring before building capabilities so each is measured as it lands. |
| 3 | **M-B5a** Archetype scenarios #1–9 (fixtures) | M-B0 | Hand-built ground truth to drive M1–M7 test-first; seeds the §11.2 archetype layer. |
| 4 | **M1** Requirement interpretation | M0 | First real capability; obligations are the spine everything maps to. |
| 5 | **M2** Git change analysis | M0 | Provides the diff/source context M3–M5 consume. |
| 6 | **M3** Implementation-coverage analysis | M1, M2 | Needs obligations + change set. |
| 6.5 | **M3.5** Unrequested-change scoring & disposition | M3, #81 | Dogfood follow-up (DR-081); pre-M4 cleanup — scores the unrequested-change axis and adds dispositions before M4/M5 build on the state model. |
| 7 | **M4** Test discovery & mapping | M2, M1 | Needs change set + obligations. |
| 8 | **M5** Test-semantic analysis | M4 | The core hard capability; consumes the test↔obligation map. |
| 9 | **M6** Builder-declaration comparison (optional input) | M1, M3, M5 | Compares declaration against obligations/diff/tests. |
| 10 | **M7** Completion result, recommendations, CLI output | M3, M5, M6 | Assembles the static pipeline into a usable result. **Static checker feature-complete here.** |
| 11 | **M-B1–B4** Real-change benchmark datasets + accuracy report | M7, M-B0 | Needs the full static pipeline to score; produces headline accuracy figures. |
| 12 | **M8** Optional execution tier | M5, M7 | Elevates tiers; can only confirm what the static pipeline already maps. |
| 13 | **M-B5b + M-B6** Execution demo #14 + user-correction capture | M8 | Execution-confirmed archetype; capture corrections as labeled cases (§11.3). |
| 14 | **M9** Hardening & Stage-1 exit | all | Meet the §13.6 bar; gate to Stage 2. |

Rationale for the two most load-bearing ordering choices: (a) **benchmark-before-capabilities** (M-B0 before M1) means no capability is built without a way to score it, directly serving the §2.5 "the reviewer must be measurable" constraint; (b) **execution after the static pipeline** (M8 late) reflects §8 — execution *confirms* judgments the static tiers already produce, so it has nothing to elevate until M5/M7 exist.

### Demonstration-scenario coverage matrix (§13.5)

| # | Scenario | Proven by |
|---|---|---|
| 1 | Missed obligation | M1 + M3 |
| 2 | Qualifier missed | M3 |
| 3 | Superficial test (asserts existence) | M5 |
| 4 | Non-discriminating input | M5 (+ M8 to confirm) |
| 5 | Circular expected result | M5 |
| 6 | Critical behavior mocked out | M5 |
| 7 | Declaration mismatch | M6 |
| 8 | Unrequested change | M3 + M3.5 + M7 (M7.6 advisory presentation) |
| 9 | Local revision cycle (rerun) | M7 (incremental re-run over M0 state) |
| 14 | Execution-confirmed weak test | M8 |

Scenarios 10–13 depend on GitHub/CI and are Stage 2.

---

## 6. Milestones as agent-ready tasks

Each task lists **inputs → deliverable → acceptance check**. Tasks within a milestone are ordered; cross-milestone dependencies are noted. Acceptance checks are written to be verifiable by a coding agent without human judgment wherever possible; where human judgment is required it is marked `[human]`.

### M0 — Foundations & walking skeleton

- **M0.1 Repo scaffold & CLI entrypoint.** *Inputs:* none. *Deliverable:* project scaffold with an `acceptance` CLI exposing `check --task --base --head` that parses args and exits cleanly. *Acceptance:* invoking the CLI with a fixture task and two Git revisions returns exit code 0 and an empty structured review object.
- **M0.2 Review-state data model.** *Inputs:* §15 model. *Deliverable:* typed schemas for Project, Task source, Mandate interpretation, Builder declaration, Change set, Obligation, Test evidence, Execution evidence, Finding, Review (Benchmark case added in M-B0). *Acceptance:* each schema round-trips to/from persisted form; a Finding cannot be constructed without an evidence tier and at least one link target (invariant enforced by a failing constructor test).
- **M0.3 Evidence-tier primitives.** *Inputs:* §8.1 ladder. *Deliverable:* an evidence-tier enum (builder-claim < static < coverage-confirmed < defect-killed < CI-confirmed) with an ordering and a rule that a tier can only be raised by the component authorized to produce it. *Acceptance:* attempting to set `defect-killed` from the static analyzer raises; ordering comparisons match §8.1.
- **M0.4 LLM-orchestration harness.** *Inputs:* decision 3.2 "LLM orchestration boundary." *Deliverable:* a thin layer that issues schema-constrained model calls, validates responses against the target schema, and records every prompt/response for replay. *Acceptance:* a recorded transcript replays a full run with zero live model calls; a malformed model response is rejected with a typed error, not silently accepted.
- **M0.5 Determinism controls.** *Inputs:* decision 3.2 "determinism strategy." *Deliverable:* configurable seed/temperature and a replay/record mode. *Acceptance:* two consecutive recorded runs over the same input produce byte-identical review state.
- **M0.6 Walking skeleton.** *Inputs:* M0.1–M0.5. *Deliverable:* end-to-end no-op pipeline: ingest task + diff → write an empty but well-formed Review to the state store → render an empty CLI report. *Acceptance:* the §16 CLI shell renders with all sections present and empty; no unhandled exceptions.

### M-B0 — Benchmark harness & case schema

- **M-B0.1 Benchmark-case schema.** *Inputs:* §15 Benchmark case, §11.1 metrics. *Deliverable:* a case type carrying source (dataset/PR/mutant/agent/archetype), inputs, ground-truth labels (gaps, decomposition, mappings, evidence classes), and slots for reviewer output + score. *Acceptance:* a case serializes/deserializes; a case missing ground-truth labels fails validation.
- **M-B0.2 Checker-under-test runner.** *Inputs:* M0.6, M-B0.1. *Deliverable:* a runner that feeds a case's inputs through the current checker and captures its Review output against the case. *Acceptance:* running the empty skeleton over an archetype case yields a scored (all-miss) result without error.
- **M-B0.3 Scoring & report.** *Inputs:* §11.1. *Deliverable:* scorers for gap-detection (recall), false-alarm (precision), obligation-decomposition accuracy, test-to-obligation mapping accuracy, and evidence-classification agreement; a single-command report over a case set. *Acceptance:* on a synthetic set with known labels, computed metrics match hand-calculated expected values.
- **M-B0.4 Variance disclosure.** *Inputs:* M0.5. *Deliverable:* report records determinism mode and, if sampling, variance across N runs. *Acceptance:* report output includes the determinism mode and (when sampled) a spread figure per metric.

### M-B5a — Archetype scenarios #1–9

- **M-B5a.1 Fixture repos.** *Inputs:* §13.5 #1–9. *Deliverable:* nine minimal Git fixture repos, each a real task file + base/head diff + tests reproducing the archetype (missed obligation, qualifier missed, superficial test, non-discriminating input, circular expected result, mocked-out behavior, declaration mismatch, unrequested change, revision cycle). *Acceptance:* each fixture builds; `git diff base head` is non-empty; pytest runs (pass/fail as the archetype intends).
- **M-B5a.2 Ground-truth labels.** *Inputs:* M-B5a.1, M-B0.1. *Deliverable:* a labeled benchmark case per fixture with the expected finding(s) and expected obligation decomposition. *Acceptance:* each case validates; labels reviewed for correctness `[human]`.

### M1 — Requirement interpretation (task → obligations)

- **M1.1 Task-file ingestion.** *Inputs:* §7.1 format. *Deliverable:* parse `current-task.md` into behavior, constraints, exclusions, completion expectations, preserving source text spans. *Acceptance:* on the §7.1 example, extracted fields match expected; every extracted item retains a source-text reference.
- **M1.2 Obligation decomposition.** *Inputs:* §7.3, §9.1, decision "obligation schema." *Deliverable:* convert task into discrete typed obligations (functional, boundary, error-handling, invariant, regression, compatibility, explanation/observability, docs/config, human-review). *Acceptance:* on the §9.1 floating-rate example the five derived criteria are produced with correct types; on archetype #1 the omitted-instruction obligation is present.
- **M1.3 Explicit / inferred / ambiguous labeling.** *Inputs:* §7.3. *Deliverable:* each obligation flagged explicit vs. reasonable-inferred; material ambiguities surfaced as open questions rather than silently resolved. *Acceptance:* a task with an underspecified qualifier yields an open-question entry, not an invented obligation.
- **M1.4 Decomposition scoring hook.** *Inputs:* M-B0.3. *Deliverable:* wire decomposition output into the benchmark's decomposition-accuracy metric. *Acceptance:* archetype cases report a decomposition-accuracy number.

### M2 — Git change analysis

- **M2.1 Revision & diff extraction.** *Inputs:* base/head (or working tree). *Deliverable:* changed files, source vs. test partition, hunk-level diffs, and config/dependency-file changes. *Acceptance:* on a fixture with a source edit, a test edit, and a dependency bump, all three are correctly categorized.
- **M2.2 Surrounding-code retrieval.** *Inputs:* decision "code-context retrieval," §12. *Deliverable:* for each changed region, retrieve enclosing definitions and direct call sites within a bounded budget. *Acceptance:* for a changed function, its definition and at least its in-repo callers are retrieved; retrieval respects the configured budget cap.
- **M2.3 Working-tree mode.** *Inputs:* §5.1 (works before a PR exists). *Deliverable:* analyze uncommitted working-tree changes against a base. *Acceptance:* a dirty working tree produces the same change-set shape as a committed diff.

### M3 — Implementation-coverage analysis

- **M3.1 Obligation-to-diff classification.** *Inputs:* M1 obligations, M2 change set, §9.2. *Deliverable:* classify each obligation Addressed / Partially addressed / Not addressed / Unclear / Requires-non-code-evidence, each linked to specific diff regions or explicitly none. *Acceptance:* archetype #1 → the missing instruction classified Not addressed; #2 → the missing qualifier classified Partially addressed; both link to exact code or record "no corresponding change."
- **M3.2 Unrequested-change detection.** *Inputs:* M2 change set, M1 obligations, §9.2. *Deliverable:* flag diff regions with no corresponding obligation as candidate unrequested changes, especially public-interface/dependency/adjacent-behavior changes. *Acceptance:* archetype #8 → the unmentioned public-interface change is flagged.
- **M3.3 Coverage scoring hook.** *Inputs:* M-B0.3. *Deliverable:* feed classifications into gap-detection/false-alarm scoring. *Acceptance:* archetypes #1, #2, #8 contribute to recall/precision figures.

### M3.5 — Unrequested-change scoring & disposition (dogfood follow-up)

*Resolves #81 and the DR-081 decisions; runs as the pre-M4 cleanup pass. Surfaced by the M3.3 dogfood run (`acceptance classify`) flagging the scoring hook as only partially addressed. Deferred to Stage 2 (tracked separately): per-disposition scoring accuracy, real-change unrequested-change labeling, and the strongest "own backlog item" finding (needs PR↔issue linkage).*

- **M3.5.1 Unrequested-change scoring metric.** *Inputs:* #81, §11.1, `scoring.py`, M3.2/M3.3. *Deliverable:* an `unrequested_precision` / `unrequested_recall` pair matching obligation-less findings against obligation-less ground-truth changes, reported separately from the gap metric; archetype #8 ground truth updated. *Acceptance:* archetype #8's unrequested-change detection contributes a precision/recall number that does **not** route through its leave-existing obligation's coverage classification.
- **M3.5.2 Disposition on the Finding schema.** *Inputs:* §9.2, §15, DR-081. *Deliverable:* a `disposition` field on unrequested-change findings (in-service / separable / risky), obligation-less by construction; a strict/loose scope-expansion policy setting. *Acceptance:* an unrequested-change finding round-trips with a disposition and no `related_obligation`; the finding invariant permits obligation-less findings only for this type.
- **M3.5.3 Separability classification.** *Inputs:* M3.5.2, M3.1 coverage, §9.2. *Deliverable:* classify each unrequested change via the removability litmus (would the task still be complete without it?) plus signals (new public surface, own tests, disjoint modules); emit an advisory "consider splitting into its own PR/backlog item" recommendation for `separable`. *Acceptance:* a planted separable feature → `separable` with the split recommendation; an in-service refactor an obligation depends on → `in_service`.
- **M3.5.4 Archetype expansion.** *Inputs:* M-B5a, §13.5 #8. *Deliverable:* unrequested-change archetypes beyond #8 — a separable extra feature, an in-service refactor, and a risky adjacent-behavior change — with ground-truth dispositions. *Acceptance:* each new fixture builds and its disposition label validates `[human]`.
- **M3.5.5 Spec + plan documentation.** ✅ *Inputs:* DR-081. *Deliverable:* §9.2, §9.3, §11.1, §15 updated with the two-axis frame, disposition taxonomy, and confidence-vs-importance framing. *Acceptance:* `[human]` review confirms the two axes and disposition model are recorded. *Delivered in #90.*

*M3.5's original "advisory presentation" sub-task moved to §M7 as **M7.6** — it lands with M7's CLI output, not before.*

### M4 — Test discovery & mapping

- **M4.1 Test discovery.** *Inputs:* M2 change set. *Deliverable:* collect added/modified tests plus relevant existing tests (by touched symbols, imports, naming, and call graph). *Acceptance:* on a fixture where an existing untouched test covers a changed function, that test is discovered.
- **M4.2 Test-to-obligation mapping.** *Inputs:* M1 obligations, M4.1, §9.1. *Deliverable:* map each candidate test to the obligation(s) it purports to evidence; obligations with no mapped test flagged. *Acceptance:* on the §9.1 example, each derived criterion is either mapped to a test or flagged unmapped; mapping-accuracy metric reports a number vs. archetype labels.

### M5 — Test-semantic analysis (core)

- **M5.1 Per-test structural extraction.** *Inputs:* M4 mapped tests, §9.3. *Deliverable:* per test — what code is exercised, what is asserted, fixtures/mocks used, input values, and expected-value provenance. *Acceptance:* for archetype #5, the analyzer identifies that the expected value is produced by the same production function (circular provenance).
- **M5.2 Discrimination judgment.** *Inputs:* M5.1, §9.3 central question. *Deliverable:* per criterion, judge whether the mapped tests would fail under a *named plausible defect* — i.e. do inputs distinguish competing interpretations, boundaries/negatives exist, assertions target the required result. Output includes the named plausible defect. *Acceptance:* archetype #4 → input judged non-discriminating with the specific reason; a genuinely strong fixture → judged discriminating.
- **M5.3 Strength classification.** *Inputs:* M5.2, §9.3 categories. *Deliverable:* classify each criterion's evidence Strongly / Partially / Nominally / Unsupported / Requires-other-evidence / Indeterminate, at the `static` tier, with a linked explanation. *Acceptance:* archetype #3 → Nominal; #6 (mocked-out behavior) → Unsupported or Nominal with the mock cited; each classification links to exact test lines.
- **M5.4 Weak-evidence detectors.** *Inputs:* §9.4 patterns. *Deliverable:* detectors for the named anti-patterns — assert-not-none / result-exists, circular expected value, incomplete error assertion, requirement-not-exercised, critical-behavior-mocked, unvalidated snapshot. *Acceptance:* each §9.4 code example is correctly flagged with the matching pattern name.
- **M5.5 Semantic scoring hook.** *Inputs:* M-B0.3. *Deliverable:* feed classifications into evidence-classification-agreement metric. *Acceptance:* archetype set reports a classification-agreement figure.

### M6 — Builder-declaration comparison (optional input)

- **M6.1 Declaration ingestion.** *Inputs:* §7.4 template. *Deliverable:* parse the nine-section declaration when present; when absent, record a minor finding and proceed with a full review (§7.4 optional-by-default). *Acceptance:* a run without a declaration completes and emits the "declaration absent" minor finding; a run with one populates the declaration state.
- **M6.2 Declaration-vs-evidence comparison.** *Inputs:* M1 obligations, M2 diff, M5 tests, §2.3/§6. *Deliverable:* compare declared mandate/implementation/tests/exclusions/assumptions/limitations against obligations, diff, and tests; emit discrepancies as findings treated as claims, never proof. *Acceptance:* archetype #7 → "declares an error condition implemented; no code path or test found" produced as a discrepancy finding.

### M7 — Completion result, recommendations, CLI output

- **M7.1 Structured recommendations.** *Inputs:* M3/M5 gaps, §9.5. *Deliverable:* for each missing/weak criterion, a machine-readable recommendation with criterion, required input characteristics, boundary/negative conditions, expected output/relationship, required assertions, the plausible defect it should detect, and relevant repo conventions/fixtures. *Acceptance:* the §9.5 contractual-accrual recommendation is reproduced from its archetype with all fields populated; output validates against the recommendation schema.
- **M7.2 Completion verdict.** *Inputs:* all findings, §10.1 step 11. *Deliverable:* an overall result — no-material-gaps / incomplete / needs-clarification / needs-non-code-review / unable-to-determine — derived from findings with stated confidence limitations. *Acceptance:* each archetype yields the expected verdict; a positive verdict renders the §3.7 "no material gaps at the achievable tier" caveat.
- **M7.3 Next-instruction generator.** *Inputs:* gaps + recommendations, §10.1 example. *Deliverable:* a `.acceptance/next-instruction.md` that tells the agent what to implement and which discriminating tests to add. *Acceptance:* on a multi-gap archetype, the next instruction names each gap and its distinguishing test, matching the §10.1 style.
- **M7.4 CLI report.** *Inputs:* §16 format. *Deliverable:* the §16 CLI output — obligation coverage, test evidence with per-line tier tags, unrequested changes, recommended-next-instruction pointer. *Acceptance:* rendered output matches the §16 layout; every test-evidence line shows its evidence tier.
- **M7.5 Incremental re-run.** *Inputs:* M0 state store, §13.5 #9. *Deliverable:* re-run against a new head, updating only affected obligations/findings and reflecting closed gaps. *Acceptance:* archetype #9 → after the fix, the previously failing obligation flips to addressed and the verdict updates.
- **M7.6 Advisory presentation of unrequested-change findings.** *Inputs:* §16, DR-081, §9.2. *Deliverable:* render unrequested-change findings prominently but as advisory, separating certainty from importance; no defect-claim language; show the disposition per finding. *Acceptance:* CLI shows unrequested changes with disposition, framed "no obligation explains this — your call." *(Specified in M3.5/DR-081; lands here with the rest of M7's CLI output.)*

### M-B1…M-B4 — Real-change benchmark datasets + accuracy report

- **M-B1 Ready-made labeled instances.** *Inputs:* §11.2 base layer; §10 dataset selection. *Deliverable:* an ingester mapping **SWE-bench Verified** instances (`problem_statement` → obligations input; `patch` → gold implementation; `test_patch` + `FAIL_TO_PASS`/`PASS_TO_PASS` → test-evidence ground truth) into benchmark cases; start with a stratified subset of ~100 across the `difficulty` field, scalable to the full 500. *Acceptance:* ≥ 100 Verified cases ingested and scored end-to-end; the FAIL_TO_PASS/PASS_TO_PASS split is preserved as gap-vs-regression labels; per-repo licenses recorded per instance `[human: confirm redistribution posture]`.
- **M-B2 Real merged PRs + follow-up-fix labels.** *Inputs:* §11.2; §10. *Deliverable:* a miner selecting Python PRs that close a linked issue and add/modify tests; reverted / follow-up-"fix" PRs mined to auto-label missed obligations. Concentrate mining on the ~12 repos SWE-bench already environment-configures (astropy, django, sympy, matplotlib, flask, requests, scikit-learn, etc.) so the SWE-bench harness's per-repo setup is reused rather than rebuilt. *Acceptance:* a sample of mined missed-obligation labels is spot-checked as valid `[human]`.
- **M-B3 Offline mutants for test-strength labels.** *Inputs:* §11.2, §8.2 concept; §10. *Deliverable:* inject a mutant into real code with a real passing test; surviving mutant → ground-truth "weak evidence" label. Built on **BugsInPy**, whose per-bug reproducible checkout + `test`/`coverage`/`mutation` commands give real code, a real relevant test, and a ready mutation harness; SWE-bench `PASS_TO_PASS` tests are a secondary source. Uses mutation offline for *labeling*, independent of the product's execution tier. *Acceptance:* generated weak-evidence labels reproduce on re-run; a killed mutant is not mislabeled as weak.
- **M-B4 Real agent-output layer.** *Inputs:* §11.2 on-thesis layer; §10. *Deliverable:* run real coding agents on the **SWE-bench Verified** issues and label each agent output against that instance's gold `patch` and `FAIL_TO_PASS` tests — the gold solution and its test oracle are already provided, so labeling is comparison, not re-derivation. *Acceptance:* ≥ 30 agent-generated cases scored; label provenance (agent, model, gold instance) recorded.
- **M-B*.report Accuracy report.** *Inputs:* M-B0.3, M-B1–4. *Deliverable:* a single-command report of recall, precision, decomposition accuracy, mapping accuracy, and (post-M8) static-vs-executed agreement, with variance disclosed. *Acceptance:* report runs to completion and emits all headline figures reproducibly.

### M8 — Optional execution tier

- **M8.1 Feasibility probe.** *Inputs:* §8.3, decision "feasibility probe." *Deliverable:* detect whether the project defines a test command that runs mapped tests quickly, in a sandbox, without network/secrets; record the decision per project. *Acceptance:* a hermetic fixture → feasible; a fixture with a network-bound test → not feasible, and the run degrades silently to static with a labeled lower tier.
- **M8.2 Sandbox runner.** *Inputs:* §8.3, §17 execution safety. *Deliverable:* run a targeted subset of mapped tests in an isolated sandbox with no network/secrets and a time budget. *Acceptance:* network access from within a test is blocked; exceeding the time budget aborts cleanly and falls back to static.
- **M8.3 Coverage-confirmed tier.** *Inputs:* §8.1 tier 3. *Deliverable:* run mapped tests under coverage; if the obligation's lines are exercised, raise that criterion to coverage-confirmed. *Acceptance:* a test that never touches the obligation's lines is not raised; one that does is raised — verified on a purpose-built fixture.
- **M8.4 Targeted mutation (defect-killed tier).** *Inputs:* §8.2, decision "mutation targeting." *Deliverable:* inject the *named* plausible defect at the exact lines, run only the mapped tests; red → discriminates (raise to defect-killed), green → proven weak. *Acceptance:* archetype #14 → the mutant survives the mapped test, upgrading a static "looks weak" to "does not discriminate."
- **M8.5 Close-the-loop confirmation.** *Inputs:* §8.4. *Deliverable:* after a recommended test is added, inject the defect it claims to catch and confirm the new test fails before marking the gap closed. *Acceptance:* a recommended test that fails to kill its defect leaves the gap open with an explanatory finding.

### M-B5b + M-B6 — Execution archetype + user-correction capture

- **M-B5b Execution-confirmed archetype.** *Inputs:* M8, §13.5 #14. *Deliverable:* the #14 fixture wired so the harness records the static→executed tier upgrade. *Acceptance:* the case scores an evidence-classification-agreement data point between static prediction and executed ground truth.
- **M-B6 User-correction capture.** *Inputs:* §11.3. *Deliverable:* capture user edits to criteria/decomposition, false-positive overrides, false-negative flags, and test-recommendation accept/reject as new labeled cases in the §15 benchmark shape. *Acceptance:* a simulated correction produces a valid benchmark case that the harness can subsequently score against.

### M9 — Hardening & Stage-1 exit

- **M9.1 Cost/latency pass.** *Inputs:* §17. *Deliverable:* changed-and-relevant-files-first ordering, caching of stable analysis, and a fast-preliminary vs. deep mode. *Acceptance:* a repeat run on unchanged inputs reuses cache and completes materially faster; partial findings can be shown before deep analysis finishes.
- **M9.2 Confidence-language audit.** *Inputs:* §3.7, §13.6 trustworthiness. *Deliverable:* review every user-facing verdict/string so positives never overstate correctness and tiers/inferences are explicit. *Acceptance:* `[human]` audit finds no unqualified correctness claim; automated check confirms every finding renders a tier.
- **M9.3 Demo-scenario acceptance run.** *Inputs:* §13.5 #1–9 (+14). *Deliverable:* a single suite asserting each scenario yields its expected finding/verdict. *Acceptance:* all nine local scenarios pass; #14 passes where execution is enabled.
- **M9.4 Headline accuracy sign-off.** *Inputs:* M-B report, §13.6 measured-accuracy. *Deliverable:* recorded recall/precision/decomposition/mapping/agreement figures with variance, and defensible default confidence language derived from them (§11.4). *Acceptance:* figures reproduce from one command; `[human]` sign-off that they clear the "defensible" bar for the wedge.

---

## 7. Cross-cutting concerns (apply to every milestone)

- **Tiering is enforced, not remembered.** The M0.3 primitives mean no component can emit a finding above its authorized tier; this is checked in every capability's tests, not just at the end.
- **Provenance on every conclusion.** Findings link to requirement text / code lines / test locations (§13.6). Tasks that produce findings include a link-completeness assertion.
- **Uncertainty is first-class.** Indeterminate and open-question outputs are valid, expected results (§9.3, §7.3) — a milestone is not "done" only when it emits confident verdicts.
- **Measure as you build.** Every capability milestone ends with a scoring hook into M-B0 so accuracy is tracked continuously, not discovered at the end (§2.5, §11).
- **Replay-first development.** Recorded transcripts (M0.4) let capability tests run without live model calls, keeping the demo suite deterministic and cheap.

---

## 8. Stage-1 build risks and mitigations

These are execution risks for *building Stage 1*, complementing the product risks in §17.

- **The reviewer is itself an AI (§2.5) — the defining risk.** Mitigation is structural and front-loaded: M-B0 before M1 so nothing ships unmeasured; benchmark tracks precision as hard as recall (a noisy reviewer is ignored); execution-confirmed tiers (M8) replace prediction where feasible.
- **Test-semantic analysis (M5) is the hardest capability and may under-deliver.** Mitigation: drive it test-first against archetypes #3–6 before real data; keep Indeterminate as a first-class output so the tool degrades honestly rather than guessing; treat M5 as the milestone most likely to need iteration and schedule slack there.
- **Benchmark fabrication / label validity.** Mitigation: prefer real-change sources (§11.2) with human spot-checks on mined labels (M-B2); use offline mutants (M-B3) only for objective test-strength labels; keep the hand-curated archetype set for interpretability only, never as the basis for accuracy claims (§11.2 last bullet).
- **Execution scope creep beyond hermetic tests.** Mitigation: the feasibility probe (M8.1) and sandbox constraints (M8.2) are acceptance-gated to refuse non-hermetic suites; "standing up environments the project doesn't support" stays a hard non-goal (§13.7).
- **Model cost/latency during iteration.** Mitigation: replay-first development (M0.4), changed-files-first ordering and caching (M9.1), fast-preliminary mode.
- **Dataset licensing uncertainty.** Mitigation: the §11.2-flagged decision (dataset selection/licenses) is an explicit M-B1 gate with human confirmation before adoption.

---

## 9. Stage-1 exit criteria (gate to Stage 2)

Proceed to Stage 2 (GitHub Acceptance Review) only when:

1. The §2 definition-of-done items 1–6 all hold.
2. The nine local demonstration scenarios pass in the M9.3 suite (plus #14 where execution is enabled).
3. The accuracy report (M9.4) produces reproducible recall / precision / decomposition / mapping / agreement figures over a real-change dataset, with disclosed variance, and default confidence language is derived from them.
4. The static pipeline runs on at least one real external Python repo with agent-made changes and produces findings a developer judges materially accurate and defensible `[human]` (§13.6 local quality).
5. The review-state model (§15) and evidence-tier discipline are stable enough that Stage 2 can add Issue/PR/CI inputs by extension, not rework — validated by a design check that Mode B inputs (§13.4) map onto existing state types.

Stage 2 then reuses this engine wholesale (§13.4 "reuse Stage 1"), adding the GitHub App, requirement retrieval, CI-evidence ingestion, and the acceptance check — without revisiting the core analysis built here.

---

## 10. Benchmark dataset selection (resolves M-B1)

This resolves the §3.2 decision the spec flagged in §11.2 ("exact dataset selection, subset sizing, and licenses are confirmed in the development plan before adoption"). Two datasets cover all five benchmark layers; each is chosen because its native structure already matches the tuples the reviewer needs.

### 10.1 Primary: SWE-bench Verified

**What it is.** A 500-instance, human-validated subset of the SWE-bench test set — real GitHub issue → gold pull-request patch → the PR's own test changes — drawn from 12 popular Python repositories (astropy, django, sympy, matplotlib, flask, requests, scikit-learn, and similar). Validated by professional annotators as genuinely solvable, which strips out the mislabeled/underspecified instances that add noise to accuracy figures.

**Why it fits this product almost exactly.** Each instance already carries the fields the checker consumes and the ground truth the benchmark scores against:

| SWE-bench field | Role in our benchmark |
|---|---|
| `problem_statement` (issue title + body) | Task input → obligation decomposition (M1) |
| `patch` (gold PR patch, test code removed) | Gold implementation for coverage/agent-output labels (M-B4) |
| `test_patch` (tests the PR added) | The test evidence the semantic analyzer judges (M5) |
| `FAIL_TO_PASS` (tests tied to the fix) | Ground-truth "the behavior the change must demonstrate" — gap labels |
| `PASS_TO_PASS` (tests green before and after) | Ground-truth regression/compatibility set — feeds mutant labels (M-B3) |
| `difficulty` (Verified only) | Stratification variable for subset sampling |

The `FAIL_TO_PASS` / `PASS_TO_PASS` split is the single most valuable feature: it is a ready-made, human-checked partition of "tests that evidence the requested behavior" vs. "tests that guard existing behavior" — precisely the distinction §9.2/§9.3 ask the reviewer to make.

**Sizing.** Start with a **stratified ~100-instance subset** across the `difficulty` field for fast iteration during M1–M7; scale to the full 500 for the M9.4 headline figures. Full SWE-bench (2,294) and SWE-bench Lite (300) are available if more volume is wanted, but Verified's human validation makes it the better accuracy base. **Excluded:** SWE-bench Multimodal (100 visual/UI instances — out of scope per §4) and SWE-bench Multilingual (non-Python — out of Stage-1 scope §13.2).

### 10.2 Secondary: BugsInPy

**What it is.** ~500 hand-curated, reproducible real bugs from 17 Python projects (pandas, keras, matplotlib, scrapy, ansible, youtube-dl, and others), each isolated with a buggy version, a fixed version, and the relevant failing test. Its CLI ships `checkout`, `compile`, `test`, `coverage`, and **`mutation`** commands over a Docker image.

**Why it earns a place alongside SWE-bench.** It is the natural backbone for the **offline-mutant test-strength layer (M-B3)**: a per-bug reproducible checkout plus a built-in mutation and coverage harness is exactly the "inject a mutant into real code with a real passing test; if it survives, that's a ground-truth weak-evidence label" recipe (§11.2, §8.2) — without our having to build a mutation runner just to *generate labels*. It also doubles as ready-made fixtures for exercising the M8 execution tier against genuinely hermetic Python suites.

### 10.3 Layer-to-dataset mapping (§11.2)

| §11.2 layer | Dataset | Notes |
|---|---|---|
| Ready-made labeled instances (base) | **SWE-bench Verified** | Human-validated; FAIL_TO_PASS/PASS_TO_PASS as gap/regression labels. |
| Real merged PRs + follow-up-fix labels | Mined from SWE-bench's 12 configured repos | Reuse existing per-repo environment setup (M-B2). |
| Offline mutants for test-strength labels | **BugsInPy** (primary), SWE-bench PASS_TO_PASS (secondary) | BugsInPy's `mutation`/`coverage` commands generate labels directly (M-B3). |
| Real agent output (on-thesis) | Agents run on **SWE-bench Verified** | Label vs. gold `patch` + `FAIL_TO_PASS` (M-B4). |
| Hand-curated archetypes | Built in-house (M-B5a) | Interpretability only; never the basis for accuracy claims (§11.2). |

### 10.4 Licensing posture

- **SWE-bench harness/code** — MIT. Safe to build tooling on and to vendor.
- **SWE-bench dataset instances** — no single dataset-wide license; **each instance carries the license of its source repo at that commit**, and the included repos permit at least non-commercial use (most of the 12 — astropy, django, sympy, flask, requests, scikit-learn — are permissive BSD/Apache/PSF). Using the data to *measure* the reviewer internally is standard, low-risk research use. **Redistributing** a derived dataset, or shipping any repo's code inside the commercial product, requires a per-repo license check first — the ingester therefore records each instance's repo license as a field (M-B1 acceptance).
- **BugsInPy** — the repository **declares no license file**, which defaults to "all rights reserved." Academic/internal benchmarking use is the norm and low-risk, but treat it as **confirm-before-redistribution**: do not bundle BugsInPy content into the product or a public derived dataset without contacting the authors (soarsmu). Because BugsInPy is used only to *generate labels offline* (not shipped), this constraint does not block Stage 1.

**Net for the commercial goal:** neither dataset needs to ship inside the product. Both are used behind the scenes to validate accuracy, so the licensing constraints bear on *publishing a derived benchmark*, not on selling the reviewer. The one hard gate is recording per-instance repo licenses (SWE-bench) and not redistributing BugsInPy content (M-B1 / M-B3 acceptance checks).

### 10.5 Residual actions (kept in M-B1)

1. Confirm the exact SWE-bench Verified snapshot/version pin and record it for reproducibility.
2. Record each ingested instance's source-repo license as a case field; flag any copyleft repo for the redistribution decision.
3. Confirm BugsInPy's usage terms with the authors before any derived-dataset release; internal label generation may proceed meanwhile.

*Sources for this section are listed in the chat message accompanying this plan.*
