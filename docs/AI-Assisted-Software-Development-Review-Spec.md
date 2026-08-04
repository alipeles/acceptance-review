# Spec: Independent Completion and Acceptance Review for AI-Assisted Software Development

*Working spec for the author and coding agents. Defines what the product is and why. Milestones, sequencing, and status live in the GitHub backlog (milestones + issues). Each concept is defined once in an authoritative section; other sections cross-reference rather than restate.*

---

## 1. Summary

AI coding agents interpret a task, choose an implementation, write the code, write the tests, run or report the tests, and summarize what they completed. The system doing the work also produces most of the evidence that the work was done — a **circular assurance problem**. A passing suite does not establish that every material instruction was addressed, that the requirement was interpreted correctly, that tests distinguish correct from incorrect behavior, that boundaries and failures were covered, that existing behavior was preserved, or that the completion summary matches the implementation.

This product is an **independent evidence reviewer**. Given a task and a proposed implementation, it determines whether the work appears complete, whether the tests meaningfully demonstrate the *requested* behavior, and what evidence is still needed before accepting the change. Its value is not generating more tests; it is judging whether existing tests are persuasive evidence for the specific behavior requested — and, where feasible, *proving* that judgment by execution rather than asserting it.

Two operating modes share one analysis engine:

- **Local Completion Check** — a lightweight developer tool used during implementation, before a PR exists. Works from a task file, Git revisions, source, tests, and an optional builder declaration. No GitHub App, CI access, or hosted service required. Question: *did the builder respond completely and plausibly to the task, and do the tests provide meaningful evidence?*
- **GitHub Acceptance Review** — a repository-native check when a PR is ready (GitHub is the first integration; other code repositories, CI/CD systems, and work-management tools are intended to follow — §5.2, §18). Adds the linked Issue, PR metadata, GitHub Actions results, and repo review policy to the same analysis. Question: *does the evidence justify accepting this PR against the linked requirement?*

The product is **coding-agent independent** (§4). Two commitments keep it honest, each defined in its own section: the reviewer is itself an AI and must be **measured against ground truth** (§3.5, §11), and **execution is offered wherever feasible** because running a test beats predicting its behavior (§8).

---

## 2. Problem

**2.1 Plausible but incomplete work.** Agents often implement the central feature while missing qualifiers: preserve existing behavior, handle an explicit failure, support indirect as well as direct references, keep backward compatibility, use a contractual rather than calendar date convention, expose traceability, avoid public-interface changes, update docs/config, or apply the behavior across all relevant code paths. The code looks substantial and tests pass while part of the mandate is unaddressed.

**2.2 Test presence ≠ behavioral evidence.** Tests may exist without establishing the criterion: assertions that only confirm a result returned; inputs that don't distinguish competing interpretations; missing boundary/negative cases; expected values derived from the same logic under test; mocks that bypass the critical behavior; unvalidated snapshots; tests covering a nearby behavior; tests written by the same agent that made the interpretation error. Coverage shows which code ran, not whether the requested behavior was demonstrated. (Analysis in §12; coded examples in §12.4.)

**2.3 Builder claims are not independent evidence.** A completion summary establishes only what the builder *believes* it was asked to do and did. It must be compared against the requirement, the diff, the tests, and CI. Disagreement among these is itself a finding.

**2.4 Review is hard for domain-oriented builders.** A domain owner directing an agent may not want to inspect every detail but still needs to know: was every important instruction addressed; did the agent misunderstand the requirement; are there meaningful tests per behavior; would they catch plausible wrong implementations; did the change add unrequested behavior; is the completion claim credible; what should go back to the agent next; is the PR acceptable. The product turns these into a structured, repeatable review.

**2.5 The reviewer is itself an AI — the defining constraint.** The core analysis is a model making semantic judgments about code and tests, which risks reproducing the exact failure it exposes: confident, plausible conclusions the user must take on trust. Credibility therefore cannot rest on "a second model looks at it." It rests on structural defenses: decomposition and evidence typing (no global verdicts); linkage of every conclusion to exact requirement/code/test; explicit uncertainty and inference labels; **executable confirmation where feasible** (§8); and **measured accuracy against ground truth** (§11). The product should name this openly to users.

**2.6 Manual review doesn't scale — and the industry is leaving it behind.** Thorough manual review of agent work is so time-consuming that it negates much of the benefit of automated coding: if checking the work costs as much as doing it by hand, the automation's value largely collapses. In practice most agent users won't be thorough, because careful review of machine-written code is unpleasant, low-status work that is easy to skip or rush. Even a diligent reviewer misses many of the pitfalls in §2.1–§2.3 — missed qualifiers and non-discriminating tests are exactly the failures human review is worst at catching. And the industry is visibly moving toward minimal human review (for example, autonomous "Ralph loop"-style agents that iterate with little oversight), which makes *automated* means of establishing high confidence a requirement rather than a convenience.

---

## 3. Principles

1. **Coding-agent independence.** Never require a particular agent; rely on stable artifacts — task text, Git revisions, source, tests, builder declarations, PRs, Issues, CI results. Agent-specific integrations may add convenience later but are never required. (§4)
2. **Evidence over trust.** Always report *which kind* of evidence supports a conclusion: builder claim < static inference < execution-confirmed < CI-confirmed (§8). None alone guarantees correctness.
3. **Requirements stay outside.** The product does not manage a backlog or replace Issues/Jira. It imports/snapshots the relevant requirement and converts it to obligations; the origin system remains source of truth.
4. **Tests stay inside the repo.** It evaluates repo-native tests and may recommend more, but does not maintain an external acceptance suite. The agent/developer implements recommended tests using project conventions.
5. **Execution is optional, scoped, and reuses the project's own harness.** It never provisions environments or reproduces app architecture. Where the project's tests already run hermetically, it reuses that command on a *targeted subset* and degrades gracefully to static analysis otherwise. Full definition in §8.
6. **CI owns full-suite execution.** The product's optional tier runs only small targeted subsets for confirmation; CI remains the authority on whether the project as a whole builds and passes.
7. **Honest confidence boundaries.** A local positive result means *no material gaps found at the achievable evidence tier* — not proof of correctness. A GitHub positive means *reviewed criteria have credible evidence and relevant checks passed for the reviewed commit.* Neither is a guarantee.
8. **The reviewer must be measurable.** Its own accuracy is a product property, validated against a benchmark and reported as gap-detection and false-alarm rates (§11).
9. **Improve test quality, not quantity.** Every recommendation ties to a specific obligation, a plausible defect, a discriminating setup, required assertions, and why it strengthens evidence. "Add more tests" is insufficient. Where execution is available, a recommended test is confirmed to detect its target defect before a gap counts as closed (§8.4).

---

## 4. Users and scope

**Local user:** a developer or technically capable domain builder using coding agents — independent developer, technical founder, domain expert building an analytical product, consultant, product-oriented engineer. Wants an independent check before trusting "task complete."

**GitHub user:** the same developer, a domain/product owner, a PR reviewer, team lead, fractional CTO, or QA owner. Wants to know whether a PR provides sufficient evidence for the linked requirement.

**Coding-agent independence** means the product must work with changes from Codex, Cursor, Aider, Claude Code, GitHub Copilot, other agents, human developers, or mixed workflows, using only the stable artifacts in §3.1. This list is not repeated elsewhere; "any coding agent" refers to it.

**Initial software categories** — best suited to behavior assessable through source and automated tests, and (notably) whose tests tend to run hermetically, which is what makes optional execution feasible: analytical engines, financial calculation systems, APIs, data-processing and document-processing apps, developer tools, workflow apps, AI-enabled domain apps, libraries, and backend services. Out of scope for the MVP: large distributed systems, heavily visual apps, and mobile interfaces.

---

## 5. Product structure

One analysis engine, two modes. Both use the evidence tiers of §8 and are validated by the benchmark of §11.

### 5.1 Mode A — Local Completion Check

Used during development, before/while preparing a PR.

**Inputs:** task file; base and current (or working-tree) revisions; source and test changes; relevant existing tests; optional builder declaration; optional project config (including the test command that enables execution).

**Outputs:** interpreted obligations; implementation-coverage classification; test-to-obligation mapping; test-evidence assessment *with evidence tier*; missing/weak obligations; potential unrequested changes; builder-declaration discrepancies; **recommended new tests (structured for automated pickup, §9.5)**; a next instruction, retrieved on demand per criterion rather than written to a file; explicit confidence limitations.

```
Developer writes task → agent implements → agent reports complete
    → Local Completion Check runs (static; optional targeted execution)
    → gaps returned to the agent → implementation revised → PR opened
```

Requires no GitHub App, linked Issue, CI access, hosted service, or agent chat history. Initially a local CLI. Execution tier (§8) is enabled only when the project supplies a runnable test command.

### 5.2 Mode B — GitHub Acceptance Review

Used when a PR is ready for formal review. **GitHub is the initial, reference integration; Mode B is fundamentally a *repository/PR acceptance review* intended to extend to other code repositories, CI/CD systems, and work-management tools (§18). Below, "GitHub Issue/Actions" denotes the first concrete implementation, not a permanent dependency.** **Adds:** linked Issue; PR title/description; PR commits and diff; builder declaration; GitHub Actions checks; individual test reports where available; repo review config; user-confirmed mandate interpretation where needed. **Adds outputs:** issue↔declaration comparison; criterion-level CI evidence; recommended new tests (as in Mode A, structured for automated pickup); PR check result; inline annotations; formal acceptance recommendation; review recorded against a specific commit; re-review after new commits.

```
Issue defines change → any agent/human workflow → PR opened
    → normal Actions run → Acceptance Review analyzes requirement, declaration, diff, tests, CI
    → GitHub shows result → developer addresses gaps → review reruns against new head
```

---

## 6. Core analysis model

The system compares four perspectives and reports both alignment and disagreement:

| Perspective | Represents |
|---|---|
| Task / requirement | What was requested |
| Builder declaration | What the builder believes was requested and completed |
| Repository changes | What was actually changed |
| Tests and CI | What behavior appears demonstrated |

Example disagreements: the requirement specifies an error condition the declaration omits; the declaration claims a regression was addressed but no test exists; the code changes public behavior outside the mandate; a test exists but can't distinguish required from likely-wrong behavior; CI passed but the relevant test was skipped; the agent claims completion while one explicit instruction has no implementation response.

Every conclusion carries an **evidence tier** (§8) so the user always knows whether it is a static inference or an executed confirmation.

---

## 7. Inputs: task, requirement, builder declaration

### 7.1 Local task file

`.acceptance/current-task.md` — task context for the current cycle, not a backlog. May be written by hand, copied from an issue, or generated by a harness.

```markdown
# Task
Add support for indirect circular references.

## Constraints
- Do not evaluate formulas involved in a cycle.
- Return the complete cycle path.
- Preserve current direct-cycle behavior.

## Completion expectations
- Implementation
- Unit tests
- Documentation update
```

### 7.2 GitHub requirement source

Default is the linked Issue: title, description, explicit acceptance criteria, clarifying comments, examples, linked specs, related issues. The product **snapshots** the material used so the basis of a decision stays inspectable if the issue later changes.

### 7.3 Requirement interpretation

Convert task/issue into discrete obligations, typed as: functional, boundary, error handling, invariant, regression, compatibility, explanation/observability, docs/config, or human-review. Distinguish **explicit** obligations (directly supported by source text), **reasonable inferred** obligations, and **open ambiguities** needing user judgment. Material inferred obligations are labeled and, where necessary, confirmed by the user.

### 7.4 Builder declaration

A structured end-of-cycle summary from the agent/developer: mandate as understood, implementation, scope exclusions, assumptions, changed components, tests added/relied-upon, regression evidence, known limitations, and any behavioral changes outside the mandate. It captures the builder's final understanding without needing prompt logs. It is **a claim, not proof** — evidence of interpretation and completion belief only.

**Optional by default in local mode:** the product produces a full review without it and flags its absence as a minor finding; teams may require it at PR time. Any agent can generate it as the final development step from a repo template; no API integration is required. Template:

```markdown
# Builder Declaration
## Mandate as understood
## Implementation summary
## Scope exclusions
## Assumptions
## Changed components
## Test evidence
## Regression evidence
## Known limitations
## Additional behavioral changes   # or "none"
```

Repositories may retain declarations by task/PR (e.g. `.acceptance/declarations/pr-128.md`).

---

## 8. Evidence tiers and optional execution

The product is explicit about *how strongly* each conclusion is supported and reaches for the highest tier feasible for a given repo and criterion.

**Scope boundary — the product does not police the user.** It assumes the repository's existing test suite passes (verifiable from the CI logs) and does not re-run or grade the user's green tests to check up on them. Execution exists only to produce evidence the existing tests do *not* already provide, specifically: (a) running relevant existing tests that the change did not trigger; (b) exercising novel or discriminating inputs the suite does not cover; and (c) injecting a targeted plausible defect to confirm a mapped test would actually catch it (§8.2). Establishing that the suite is green is the user's and CI's responsibility, not the reviewer's.

### 8.1 The evidence ladder (weakest → strongest)

1. **Builder claim** — the declaration asserts a behavior. A starting point, not evidence.
2. **Static inference** — the reviewer reads code/tests and judges, without execution, whether an obligation is addressed and whether a test would catch a plausible defect. Always available, but a prediction.
3. **Reaches the code (coverage-confirmed)** — the mapped test is run with coverage and observed to exercise the obligation's lines. Cheap; eliminates the common "the test never touches this path" case.
4. **Kills the defect (execution-confirmed)** — a targeted, hypothesis-driven mutant is injected at the obligation's implementation and the mapped tests are run. Go red → the test discriminates; stay green → the test is *proven* weak. Strongest tier the product itself produces.
5. **CI-confirmed** — the relevant test ran and passed against the reviewed commit in the project's own CI (Mode B).

The achieved tier is recorded per criterion; a static inference is never presented as execution-confirmed.

### 8.2 Surgical, hypothesis-driven mutation (not whole-suite)

Whole-suite mutation (mutate everything, re-run the full suite many times) is deliberately avoided. Instead, the reviewer has already named a **specific plausible defect** for a criterion (e.g. "uses calendar-month boundaries instead of the contractual 26th-to-25th accrual period"). The product injects *that one defect* at the exact lines, runs *only the handful of mapped tests*, and observes whether they fail. A few executions per criterion, not a combinatorial explosion — converting "this assertion looks non-discriminating" into "the branch was flipped and the mapped test stayed green."

### 8.3 Feasibility detection and graceful degradation

On init, probe whether the project defines a test command that runs the mapped tests quickly, in a sandbox, without network access or secrets. If yes, supporting criteria are elevated to tiers 3–4. If no (cloud deps, UI-bound behavior, live-service integration tests, excessive runtime), fall back silently to static inference plus recommendations — no capability lost, affected criteria simply carry a lower, clearly labeled tier. Execution runs in an isolated sandbox; for an individual on their own repo this is low-stakes, for a hosted product it is mandatory.

### 8.4 Closing the recommendation loop

A test the agent writes to satisfy a recommendation can itself be weak or circular — the assurance problem one level up. Where execution is available, after a recommended test is added the product injects the defect it claims to catch and confirms the new test fails. Only then is the gap *demonstrably* closed rather than nominally addressed.

---

## 9. Analysis: obligations, coverage, test evidence

### 9.1 Acceptance criteria

Convert the mandate into discrete, observable criteria. Example mandate: *"Add floating-rate bonds using an index curve plus contractual spread. Accrual periods run the 26th through the 25th. Missing rate observations must produce an explicit error. Existing fixed-rate behavior must not change."* Derived criteria: (1) coupons use index + contractual spread; (2) rate selection follows the 26th-to-25th period; (3) missing observations produce an explicit structured failure; (4) fixed-rate results unchanged; (5) outputs expose the selected observation and spread where the mandate requires. Each criterion retains: source text, type, importance, explicit/inferred flag, observable behavior, implementation areas, candidate tests, evidence assessment, and achieved tier.

### 9.2 Implementation-coverage review

Classify each obligation against the diff: **Addressed** (credible implementation response); **Partially addressed** (relevant behavior present but a qualifier/branch/condition missing); **Not addressed**; **Unclear** (may be indirect; static evidence insufficient); **Requires non-code evidence** (docs, visual behavior, deploy config, usability). This finds likely incompleteness before acceptance; it does not prove runtime correctness. It also flags likely **unrequested** behavior changes — diff regions that correspond to no obligation. Unrequested-change detection is the **dual** of gap detection: a gap is an obligation with no matching code (obligation → code); an unrequested change is code with no matching obligation (code → obligation). It is therefore obligation-*less* by construction and is scored on its own axis (§11.1), never folded into the gap metric.

Every unrequested-change finding carries a **disposition**: **in service** (a refactor/interface edit needed to deliver an obligation — accept, optionally note), **separable** (a coherent, possibly valuable, but distinct unit of work — recommend splitting into its own PR/backlog item), or **risky** (touches public surface, dependencies, or adjacent behavior in a way that could hide a regression — scrutinize). `separable` and `risky` are not exclusive, and separability is orthogonal to value: high-value extra work is still flagged when it does not belong in this change. The separability test reuses coverage — *would the task still be complete if this change were removed?* — sharpened by whether the change adds new self-contained public surface, ships its own tests, and lives in files disjoint from the obligation-mapped ones. Disposition thresholds are a **policy setting** (strict vs. loose scope expansion), since where the acceptable-expansion line sits is a shop norm; the strongest "own backlog item" phrasing sharpens once the backlog is available as an input (Mode B).

Because the tool sees a change with no obligation but not the author's *intent*, unrequested-change findings are **high importance, low certainty**: surfaced prominently but framed as advisory ("here is what changed that no obligation explains — your call"), not as defect claims. Detection is deliberately recall-forward — surface everything unexplained, let the user dismiss the incidental ones — which is safe precisely because the advisory framing makes false positives cheap. (Rationale and scoring in DR-081 / §11.1.)

### 9.3 Test-evidence analysis

Central question per testable criterion: **would the available tests fail if the implementation violated this criterion in a plausible way?** A test is not strong merely because its name resembles the requirement, it invokes changed code, it's in a passing suite, or it raises coverage. Where the execution tier is available, this is answered by observation, not prediction (§8).

The classifications are defined over the **plausible-violation space** — the set of plausible defects for the criterion, made concrete as the §8.2 mapped mutants. A single bright line separates real evidence from the rest: **does the mapped test catch at least one plausible violation?**

- **Strongly supported** — the mapped test would fail for *every* plausible violation of the criterion (discriminating inputs and assertions across its cases, boundaries, and qualifiers). *Executed criterion: kills all mapped mutants.*
- **Partially supported** — the test genuinely discriminates the criterion but only across *part* of its plausible-violation space: it would fail for some plausible violations and pass for others (e.g. the happy path is covered but boundaries/negative/failure cases are not, or an assertion checks the result but not every required qualifier). *Executed criterion: kills at least one, but not all, mapped mutants.*
- **Nominally supported** — a mapped test is present and *looks* like evidence (named for the criterion, in the changed code, or lifts coverage) but has **zero discriminating power**: it passes regardless of whether the criterion is met. Two mechanisms: (a) it never constrains the behavior (trivially-true assertions, or assertions that don't reference the required result); (b) it targets the criterion but is structurally unfailable (behavior mocked out, expected value derived from the code under test / circular, or an assertion that cannot fail). *Executed criterion: a mapped test exists but survives all mapped mutants.* Nominal **requires** a present, relevant-looking test — with none, the criterion is Unsupported.
- **Unsupported** — no mapped test is relevant to the criterion at all.
- **Requires other evidence** — the criterion needs non-test evidence (docs, visual behavior, deploy config).
- **Indeterminate** — the mapped test cannot be run, or its outcome cannot be decided statically (complexity, dynamic behavior, framework indirection, or missing context).

Decision procedure:

| Situation | Classification |
|---|---|
| no mapped criterion-relevant test | Unsupported |
| mapped test catches every plausible defect | Strongly supported |
| catches some, misses some | Partially supported |
| catches none, but looks like evidence | Nominally supported |
| cannot run / cannot decide statically | Indeterminate |
| needs non-test evidence | Requires other evidence |

Without the execution tier these are **static predictions** of which mutants a mapped test would kill; where execution is available (§8.2) they are confirmed by observation. The predictions are validated against that executed ground truth — which is exactly what §11.1's evidence-classification-agreement measures.

Assess whether: inputs distinguish competing interpretations; boundaries are exercised; negative behavior is tested; assertions target the required result; expected values have independent provenance; mocks bypass the behavior; a test can pass under a plausible defect; qualifiers are omitted; regression behavior is constrained; the test reaches the relevant path; execution/CI confirms the result against the reviewed commit.

### 9.4 Examples of weak evidence

```python
# Non-discriminating: establishes only that a value returned
result = calculate_coupon(input); assert result is not None

# Circular: expected value produced by the same production logic
expected = calculate_coupon(input); assert calculate_coupon(input) == expected

# Incomplete error assertion: doesn't establish error type / missing-observation / content
with pytest.raises(Exception):
    calculate_coupon(input_with_missing_rate)
```

Also: **requirement not exercised** — a contractual-accrual test using calendar-aligned dates, so correct and incorrect implementations produce the same result; **critical behavior mocked out** — mocking the rate-selection component while claiming to establish correct rate selection; **unvalidated snapshot** — confirming output is unchanged with no evidence the stored output was correct.

### 9.5 Recommendations for additional evidence

When evidence is missing/weak, prescribe a test obligation: the criterion; required input characteristics; boundary/negative conditions; expected output or relationship; required assertions; the plausible defect it should detect; relevant repo conventions/fixtures. Example:

> Add a case where calendar-month and contractual-period logic select different index observations: accrual period Jan 26 → Feb 25. Assert both the selected fixing date and the resulting coupon. This test should fail if the implementation uses calendar-month boundaries.

Recommendations are emitted in a **structured, machine-readable form** — each tied to a criterion, with the fields above as discrete data — so a coding agent or harness can pick them up and add the test directly, and each is complete enough that the gap can typically be closed in a **single iteration**. The product recommends rather than modifies code; the recommendation is retrieved on demand per criterion (`acceptance recommendation --criterion <id>`) and may surface in the CLI, the coding agent, a PR comment, or the GitHub check. It is never written to a file that outlives the run that produced it. Where execution is available, a subsequently added test is confirmed via §8.4 before its gap counts as closed.

---

## 10. Workflows

### 10.1 Local Completion Check

1. Capture the task file. 2. Coding work occurs (any agent/human). 3. Optional builder declaration produced. 4. Checker reads task, base revision, diff, relevant source/tests, and declaration if present. 5. Decompose into obligations; flag material ambiguities. 6. Implementation-coverage review (§9.2). 7. Test-evidence review (§9.3). 8. **Execution confirmation where feasible** — run mapped tests with coverage and targeted mutation to elevate tiers (§8); otherwise proceed statically. 9. Identify additional/unrequested changes. 10. Compare builder declaration against requirement/code/tests. 11. Produce completion result: *no material gaps / incomplete / needs clarification / needs non-code review / unable to determine.* 12. Make the next instruction available when gaps exist — pulled per criterion via `acceptance recommendation --criterion <id>`, never pushed to a file that outlives the run that wrote it, e.g.:

> Apply active filters to CSV exports and add explicit handling for exports over 100,000 rows. Add tests that distinguish filtered from unfiltered output, verify displayed column order, and assert the row-limit error. Update the builder declaration after the changes.

### 10.2 GitHub Acceptance Review

1. PR opened/ready; App or workflow identifies it. 2. Retrieve linked Issue and references; snapshot. 3. Retrieve builder declaration if present. 4. Analyze PR description, commit range, source/test diffs, relevant existing tests, config/dependency changes. 5. Establish mandate by comparing Issue, PR description, and declaration; propose interpretation; flag ambiguity/inconsistency. 6. Generate acceptance criteria with source references. 7. Assess test evidence (§9.3), using execution where feasible. 8. Incorporate CI evidence: did relevant workflows run, against the PR head commit, and did tests pass/fail/skip; distinguish individual results from aggregate status. 9. Produce findings: missing coverage, weak assertions, missing boundaries, circular expected results, unrequested changes, requirement misunderstandings, declaration inconsistencies, stale/incomplete CI. 10. Publish check: mandate summary, criterion-to-evidence map, critical findings, recommended tests, CI status, acceptance recommendation, evidence limitations. 11. Re-review against the new head commit on new commits or CI reruns.

### 10.3 CI/CD integration

Runs after ordinary test workflows because it uses their results:

```
Issue → PR → normal build/test workflows → Acceptance Evidence review → advisory or required PR check
```

Check outcomes: **Success** (all mandatory criteria credible, relevant CI passed); **Neutral** (completed, but a criterion needs human judgment); **Failure** (a mandatory criterion lacks evidence, relevant tests failed, or requirement/implementation materially conflict); **Action required** (linked issue, declaration, or required artifact missing/incomplete). **Advisory by default** for the MVP. Optional later blocking conditions: no linked Issue; missing declaration; unsupported critical criterion; relevant tests failed; relevant tests didn't run against the head commit; an unresolved critical limitation; an unresolved material requirement conflict.

---

## 11. Validating the reviewer

Because the reviewer is itself an AI (§2.5), its credibility depends on measured accuracy against ground truth. This is a first-class product property, not a testing afterthought, and the same benchmark is the primary evidence that the product works.

### 11.1 What is measured

Against a labeled set of changes with known gaps: **gap detection (recall)** — of known material gaps, how many are found; **false-alarm rate (precision)** — of reported gaps, how many are spurious (a noisy reviewer is ignored, so this matters as much as recall); **obligation-decomposition accuracy** vs. a human-verified decomposition; **test-to-obligation mapping accuracy**; **evidence-classification agreement** with executed ground truth where execution is available. Because the review has two axes, gap detection (obligation → code) is complemented by **unrequested-change detection — precision and recall** — on the code → obligation axis: obligation-less findings scored against obligation-less ground-truth changes, a separate metric rather than part of the gap number. Precision matters here (legitimate incidental edits are the false positives) but detection is tuned recall-forward and kept advisory; this is scored on the hand-built archetype layer in Stage 1, with real-change scoring deferred because labeling a change "unrequested" is a judgment about intent (see DR-081).

### 11.2 Sourcing the benchmark without fabrication

Layered by source, from real changes:

- **Ready-made labeled instances** — public benchmarks pairing real GitHub issues with gold patches and explicit pass/fail test sets (the SWE-bench family and curated subsets; Python bug datasets such as BugsInPy) give task→implementation→test-evidence tuples from real projects. Base layer. *Exact dataset selection, subset sizing, and licenses are resolved in `docs/DR-168-benchmark-dataset-selection.md`.*
- **Real merged PRs** — mining Python repos for PRs that close linked issues and add/modify tests yields abundant real (issue→diff→tests→CI) tuples. Reverted or follow-up-"fix" PRs give natural **missed-obligation** labels — the follow-up documents what the first change missed.
- **Offline mutants for objective test-strength labels** — inject a mutant into real code with a real passing test; if the test still passes, that is ground-truth "weak evidence," built from real code and a real test with no fabrication. Uses mutation offline to *generate labels*, independent of whether execution ships in the product.
- **Real agent output (on-thesis layer)** — run actual coding agents on real issues; label their implementations against the known gold patch and tests. Most representative data available, since the product reviews agent work.
- **A thin hand-curated archetype set** — the demonstration scenarios (§13.4) for interpretability and readability checks only; not the basis for accuracy claims.

### 11.3 Learning from users

Beyond external data, the product improves from its own use. Signals include: a user editing the suggested acceptance criteria or obligation decomposition (a correction to interpretation); a user overriding a finding as a **false positive** (a reported gap that wasn't real), or flagging a **false negative** (a real gap the tool missed); and acceptance or rejection of recommended tests. Each correction is captured as a labeled case — the same shape as a benchmark case (§15) — and feeds calibration and, over time, per-project and cross-project tuning. This gives the product a ground-truth source that grows with adoption rather than depending solely on external datasets.

### 11.4 How validation feeds the product

Results tune obligation decomposition and evidence classification, set defensible default confidence language, decide which criterion types the reviewer handles reliably enough to report on, and produce the headline accuracy figures the product stands behind.

---

## 12. Agentic behavior

The system pursues an explicit goal — *determine whether the visible implementation and available evidence are sufficient for the requested task* — and is genuinely agentic rather than a fixed pipeline.

**Autonomous evidence gathering.** It navigates the repository under its own direction — searching definitions and call sites, reading source/tests, following imports and dependencies, locating relevant existing tests — to assemble what a given obligation requires, deciding which files matter rather than relying on a fixed input set.

**Tool use, including execution.** Beyond reading, it acts: run a mapped test, run it under coverage to confirm it reaches the code, inject a targeted mutant to confirm it discriminates (§8). This gives a real observe–act loop rather than a single-pass judgment.

**Structured review state.** It maintains explicit, inspectable state — obligations, mappings, findings, evidence tiers, open questions — rather than an unstructured conversation. This is what lets conclusions link to evidence, uncertainty be tracked, and the review re-run incrementally against new commits.

Concretely it decides: what the task requires; which instructions are material; explicit vs. inferred requirements; whether the builder's interpretation matches the mandate; which code changes correspond to each obligation; which tests are relevant; whether they discriminate (predicted statically, confirmed by execution where feasible); which plausible defects would escape current tests; whether unexpected changes need review; which missing evidence is most informative; whether evidence supports a recommendation; and when user judgment is required.

---

## 13. MVP

### 13.1 Objective

Show the system can independently identify meaningful completion and test-evidence gaps in AI-assisted changes without depending on a particular coding agent — with **measured accuracy against a real-change benchmark**, not merely plausible output. Complete MVP = a **local completion checker** (static, with optional execution for hermetic repos) + a **validation benchmark and harness** (§11) + a **GitHub-native acceptance review** applying the same analysis. The local checker and its benchmark are the first milestone and independently useful; GitHub completes the product experience. *(Ordering/effort: the GitHub backlog.)*

### 13.2 Scope

**Environment:** Python; pytest; Git; GitHub repos, Issues, PRs, Actions; JUnit XML / pytest-compatible reports where available; Markdown task files and declarations. **Optional execution tier** enabled where the pytest suite runs hermetically in a sandbox within a short time budget; otherwise static (§8). **Coding-agent independent** per §4; no direct agent integration required.

### 13.3 Stage 1 — Local Completion Checker

Capabilities: **task ingestion** (read `current-task.md`; extract behavior/constraints/exclusions/expectations; flag ambiguity; produce structured obligations); **Git change analysis** (base↔head; read changed source/tests; config/dependency changes; retrieve surrounding code); **builder-declaration ingestion, optional** (compare declared mandate/implementation/tests/exclusions/assumptions/limitations with task and diff); **implementation-coverage analysis** (§9.2, incl. unrequested-change detection); **test discovery** (added/modified and relevant existing; map to obligations); **test semantic analysis** (per candidate test: what's exercised/asserted, fixtures/mocks, input discrimination, expected-value provenance, undetected plausible defects, strength classification); **optional execution tier** (§8: coverage + targeted mutation; confirm recommended tests); **completion result** (obligation findings, test-evidence findings with tiers, declaration discrepancies, confidence limitations, overall result, next instruction retrieved on demand).

*Stage 1 non-goals:* GitHub access; agent sessions; modifying code; writing production-ready tests; managing tasks; provisioning environments; proving runtime correctness. Running the project's *own hermetic tests* for targeted confirmation is in scope (§8); standing up environments the project doesn't already support is not.

### 13.4 Stage 2 — GitHub Acceptance Review

Capabilities: **GitHub App** (auth; read issues/PRs/code/tests/checks/workflows; create a check; post findings/annotations); **requirement retrieval** (linked Issue text/comments; snapshot; compare issue/PR/declaration); **PR analysis** (base/head commits; source/test diffs; reuse Stage 1; detect new commits and rerun); **CI evidence ingestion** (workflow status; confirm commit; parse individual results where available; distinguish passed/failed/skipped/missing/stale; label aggregate-only clearly); **acceptance review** (criteria from the Issue; map tests and CI per criterion; identify unsupported/weak criteria and requirement/declaration conflicts; acceptance recommendation); **check output** (mandate summary, declaration comparison, criterion-to-evidence table, critical findings, recommended tests, CI status, acceptance result, evidence limitations). Default: run on PR updates, advisory, never merge/modify; narrow blocking rules configurable later.

### 13.5 Demonstration scenarios

Each verifies a capability and seeds the archetype benchmark layer (§11.2):

1. **Missed obligation** — 4 instructions, 3 implemented; checker finds the omission.
2. **Qualifier missed** — feature present, but backward-compat/structured-error not addressed.
3. **Superficial test** — asserts only that a result exists; classified nominal with explanation.
4. **Non-discriminating input** — correct and incorrect implementations produce the same output; recommend a distinguishing input.
5. **Circular expected result** — expected value from the same production logic; assessment lowered.
6. **Critical behavior mocked out** — mocks the component whose behavior it claims to establish.
7. **Declaration mismatch** — claims an error condition implemented; no code path/test found.
8. **Unrequested change** — diff changes a public interface/dependency/adjacent behavior unmentioned; flagged with a disposition (in-service / separable / risky) and scored on the unrequested-change axis (§11.1). Sibling archetypes cover a separable extra feature and an in-service refactor.
9. **Local revision cycle** — checker's next instruction is addressed; checker reruns and updates.
10. **Issue mismatch** — Issue specifies a contractual date convention; PR/declaration/tests use calendar.
11. **CI-confirmed evidence** — a relevant test identified; Actions confirms it passed against head.
12. **Stale/incomplete CI** — passed against an earlier commit, relevant tests skipped, or only an unrelated workflow ran.
13. **GitHub review cycle** — check finds a missing test obligation; developer adds it; CI passes; criterion updates unsupported → strongly supported.
14. **Execution-confirmed weak test** — for a hermetic repo, a targeted mutant survives the mapped test, upgrading a static "looks weak" judgment to a proven "does not discriminate" finding.

### 13.6 Success criteria

**Local quality:** decomposition materially accurate to the developer; important omissions found in selected real agent changes; mappings substantially correct; classifications understandable and defensible; recommended tests specific enough to implement; next-instruction output materially improves the next agent iteration. **Measured accuracy:** reportable gap-detection and false-alarm rates on the benchmark, with static classifications agreeing with executed ground truth at a defensible rate (§11). **GitHub quality:** adoptable without changing agents; existing Issues/PRs/tests/Actions suffice; check runs against the correct commit; output useful directly in the PR; static / execution-confirmed / CI-confirmed evidence distinguished; no duplicate requirements entry; declaration light enough to stay optional locally. **Trustworthiness:** findings link to requirement/code/test; inferences labeled; evidence tiers explicit; positive results don't overstate correctness; users can see why a criterion was classified as it was.

### 13.7 MVP non-goals

Will not: require/privilege a specific agent; read full agent prompt histories; replace Issues; manage a backlog; provision environments the project doesn't already support; run arbitrary or non-hermetic suites; operate the deployment pipeline; modify source; auto-generate/commit tests; support arbitrary languages or CI providers; do browser/mobile testing; analyze production telemetry; provide formal verification; or guarantee defect-free software. The optional execution tier runs only the project's own hermetic tests in a sandbox for targeted confirmation — deliberately narrower than "executing arbitrary applications."

---

## 14. Product boundary

**Owns:** requirement interpretation for the reviewed change; obligation/criteria generation; implementation-coverage analysis; test discovery, mapping, and evidence assessment; targeted opt-in execution of the project's own tests for confirmation; builder-declaration comparison; CI-evidence interpretation; evidence-gap identification; additional-test recommendations; completion/acceptance recommendations; review provenance, evidence tiers, and confidence limitations; and its own benchmark validation.

**Does not own:** requirements or backlog management; agent selection or prompt history; source authoring; test implementation; full-suite execution and CI orchestration; provisioning environments the project doesn't already support; build/deploy pipelines; automatic PR merging; comprehensive UI testing; production monitoring; formal verification; guarantees of correctness.

---

## 15. Conceptual data model

- **Project** — repo; default branch; test framework; source/test locations; **test command and execution feasibility**; review policy; GitHub config.
- **Task source** — local file or Issue; identifier; snapshot; text; references/attachments.
- **Mandate interpretation** — interpreted outcome; constraints; explicit/inferred obligations; ambiguities; user confirmations.
- **Builder declaration** — the nine template sections (§7.4).
- **Change set** — base/head revisions; changed files; source/test diffs; config/dependency changes.
- **Obligation / criterion** — description; type; source text; importance; explicit/inferred; observable behavior; **achieved evidence tier**; test evidence.
- **Test evidence** — identifier; location; inputs; fixtures; assertions; expected-value provenance; mocks; relevant path; mapped obligations; static assessment.
- **Execution evidence** — run id; command; result (pass/fail/skip); coverage of the obligation's lines; mutation descriptor (injected defect); outcome (killed/survived); reviewed revision.
- **CI evidence** — workflow; run id; commit; result; status; timestamp; report artifact.
- **Finding** — type; severity; related obligation (*absent for unrequested-change findings — obligation-less by construction, §9.2*); disposition (*unrequested-change findings only: in-service / separable / risky*); description; supporting evidence; evidence tier; uncertainty; recommended action.
- **Review** — mode; mandate; declaration; change set; obligation map; findings; evidence tiers; limitations; recommendation; reviewed revision.
- **Benchmark case** — source (dataset / real PR / mutant / agent run / archetype); inputs; ground-truth labels; reviewer output; scored result.

---

## 16. Interfaces

**Local CLI** — first interface, findings inspectable and linked to files/lines, each conclusion labeled with its evidence tier:

```
acceptance check --task .acceptance/current-task.md --base main --head HEAD
```
Output is organized **by obligation**, so a criterion's two axes — code evidence (§9.2) and test evidence (§9.3) — sit together rather than in separate lists the reader must join by eye. Status is stated in words, and every item is numbered (`1.`, `1.1`, …) so a reader can refer to one precisely. Numbering is positional within a report; the durable per-entity ids live in the data model (§15).

```
Task completion: INCOMPLETE

2 obligation(s) not fully implemented; 1 with non-discriminating test evidence.

Obligations:

  1. CSV generation implemented
       code evidence: addressed
         1.1  export/csv.py#@@ -12,6 +12,28 @@
       test evidence: strongly supported  [tier: execution-confirmed]
         1.2  tests/test_export.py::test_generates_csv
         1.3  tests/test_export.py::test_escaping

  2. Active filters applied to the export
       code evidence: not addressed
         (no corresponding change)
       test evidence: unsupported  [tier: static]
         (no mapped test)

  3. Displayed column order preserved
       code evidence: unclear
         3.1  export/csv.py#@@ -40,3 +40,7 @@
       test evidence: nominally supported  [tier: static]
         3.2  tests/test_export.py::test_columns

Unrequested changes:
  1. [separable] Export filename behavior changed
       export/naming.py#@@ -5,2 +5,6 @@

Next: retrieve a criterion's full recommendation with
  acceptance recommendation --criterion <id>
```

**GitHub PR** — primary team interface: Checks, PR comments, file/line annotations, links to issue text and tests. No separate web app required for routine review. **Optional web app (later)** — installation/config, review-policy settings, historical reviews, user corrections, evidence exploration, cross-PR analysis, usage/quality reporting; secondary to CLI and GitHub-native.

---

## 17. Key risks and mitigations

- **Requirement ambiguity.** Preserve source text; separate explicit/inferred; ask targeted questions; don't silently invent obligations; allow correction.
- **Incorrect code/test interpretation.** Start with Python/pytest; link to exact code; express uncertainty; allow indeterminate; **elevate to executable confirmation where feasible** (§8); add language support incrementally.
- **Reviewer accuracy — the defining risk (§2.5).** Validate against a benchmark and report measured accuracy (§11); prefer execution-confirmed over prediction; tie conclusions to inspectable artifacts; label inferences and tiers; bound confidence language.
- **False confidence.** State the evidence type/tier; distinguish static / execution-confirmed / CI-confirmed; state the full app was not independently executed; bounded language; expose limitations.
- **Declaration gaming/omission.** Treat as a claim; compare independently with task/diff/tests; require structured sections when used; flag omissions/contradictions; never treat completeness as proof.
- **Generic recommendations.** Tie each to a criterion and plausible defect; specify inputs/assertions; use repo context; confirm the recommended test detects the defect where feasible; measure whether agents can implement it.
- **Execution safety/cost.** Sandbox with no network/secrets; targeted subsets only, never full suite; time budget; skip when feasibility checks fail.
- **Adoption friction.** Local mode usable with a task file and Git; declaration optional locally; agent-independent; reuse existing Issues/PRs/Actions; version-controlled config; advisory by default; no dashboard for routine use.
- **Cost/latency of deep analysis.** Changed and semantically relevant files first; repo maps and dependency info; cache stable analysis; reuse across commits; fast preliminary vs. deep review; show partial findings.

---

## 18. Expansion path

**P2 deeper test/CI analysis** — detailed reports; skipped/quarantined detection; test↔workflow association; coverage-change analysis; flaky detection; cross-commit comparison. **P3 more languages** — TS/JS, Java, C#, more Python frameworks, language-specific test semantics and execution/mutation. **P4 optional agent integrations** — agent-specific declaration commands and convenience adapters; one-click finding transfer; harness integration after completion claims (all optional). **P5 more repositories, CI/CD, and work-management systems** — other code repositories and CI/CD providers (GitLab, Azure DevOps, Bitbucket, Jenkins/CircleCI, etc.) and work-management/requirement sources (Jira, Linear, Markdown specs, Confluence/Notion), so Mode B is no longer GitHub-specific (§5.2). **P6 controlled test generation** — repo-native drafts; separate test branches; test-only PRs run by the project's own CI. **P7 persistent assurance history** — reuse criteria across changes; track evidence across PRs; detect stale evidence; maintain regression obligations; compare agent performance over time. **P8 broader evidence** — manual demonstrations, browser automation, API probes, model-eval results, production incidents, user corrections, observability/trace data. **P9 technical-quality criteria** — extend obligations beyond *behavior* to *how* the change is written: enforce a configurable mix of general best practices, organization/project technical guidelines, and task-specific technical specifications. Targets common agent failure modes developers report — failing to reuse available shared libraries and utilities, overly verbose or sprawling changes, hard-coded values that belong in configuration, needless duplication, and violations of project conventions — surfaced as findings with the same evidence discipline as behavioral criteria.

---

## 19. Strategic framing (brief)

The **Local Completion Check** is the low-friction wedge — usable immediately with no GitHub App, agent change, CI access, requirements platform, or hosted repo access — proving the core capability: `task → obligations → implementation correspondence → test semantics → completion gaps`. The **GitHub Acceptance Review** adds stronger evidence and a team workflow: `Issue → criteria → PR implementation → repo tests → Actions evidence → acceptance recommendation`.

Note on defensibility: the space is exposed — GitHub, CI vendors, and agent makers could each fold in a version of this, and any long-term "structured-relationship" moat is aspirational. The near-term strengths are real regardless: a genuinely useful low-setup tool, measured evidence that it works, and depth on a hard problem (persuasive test evidence, confirmed by execution) that generic tools don't address well. Strategy: win on depth and measured credibility on the wedge, not on assumed lock-in. Begin as an independent completion checker with a validation benchmark and a GitHub acceptance layer — not a requirements platform, agent framework, or universal test runner.
