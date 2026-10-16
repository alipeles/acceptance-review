# Spec: Independent Completion and Acceptance Review for AI-Assisted Software Development

*Working spec for the author and coding agents. Defines what the product is and why. Milestones, sequencing, and status live in the GitHub backlog (milestones + issues). Each concept is defined once in an authoritative section; other sections cross-reference rather than restate.*

*Revised 2026-10-16 to match the design as built and decided through DR-379. Where a section describes behavior that exists in code it says so; where it describes intent that has no code yet, or a tier that is built but gated off, it says that too. Decision Records in `docs/` are authoritative for the reasoning behind each change; this document carries the result. Measured figures are collected in §11.5.*

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

**2.2 Test presence ≠ behavioral evidence.** Tests may exist without establishing the criterion: assertions that only confirm a result returned; inputs that don't distinguish competing interpretations; missing boundary/negative cases; expected values derived from the same logic under test; mocks that bypass the critical behavior; unvalidated snapshots; tests covering a nearby behavior; tests written by the same agent that made the interpretation error. Coverage shows which code ran, not whether the requested behavior was demonstrated. (Analysis in §9.3; coded examples in §9.4.)

**2.3 Builder claims are not independent evidence.** A completion summary establishes only what the builder *believes* it was asked to do and did. It must be compared against the requirement, the diff, the tests, and CI. Disagreement among these is itself a finding.

**2.4 Review is hard for domain-oriented builders.** A domain owner directing an agent may not want to inspect every detail but still needs to know: was every important instruction addressed; did the agent misunderstand the requirement; are there meaningful tests per behavior; would they catch plausible wrong implementations; did the change add unrequested behavior; is the completion claim credible; what should go back to the agent next; is the PR acceptable. The product turns these into a structured, repeatable review.

**2.5 The reviewer is itself an AI — the defining constraint.** The core analysis is a model making semantic judgments about code and tests, which risks reproducing the exact failure it exposes: confident, plausible conclusions the user must take on trust. Credibility therefore cannot rest on "a second model looks at it." It rests on structural defenses: decomposition and evidence typing (no global verdicts); linkage of every conclusion to exact requirement/code/test; explicit uncertainty and inference labels; **executable confirmation where feasible** (§8); and **measured accuracy against ground truth** (§11). The product should name this openly to users.

Two things learned building it sharpen this. First, the model's judgments are unstable across identical inputs (§11.5), and the instability runs toward "looks fine": where ratings moved on an unchanged task, the lower rating was the correct one in 7 of 8 cases. So every stage that could be arithmetic over recorded facts is arithmetic, not a judgment: the evidence class (§9.3), the completion verdict (§10.1), mandate coverage (§7.3). Model calls are confined to questions with a fixed answer shape, run at temperature 0 with a seed, and recorded so a review replays byte-identically (§12). Second, the one remaining per-pair judgment, "would this test fail under this defect," is the weakest link measured so far (66% on held-out cases), and DR-379 adopts a second vendor's model (TypeSafe's Jev) to decide it first, with the general model asked only where Jev is unsure. Jev returns a probability and no reasoning, so findings it decides keep the static tier and must be marked as carrying no reasoning. That is a deliberate trade of explainability for accuracy on one question, recorded here so it is not mistaken for the whole design.

**2.6 Manual review doesn't scale — and the industry is leaving it behind.** Thorough manual review of agent work is so time-consuming that it negates much of the benefit of automated coding: if checking the work costs as much as doing it by hand, the automation's value largely collapses. In practice most agent users won't be thorough, because careful review of machine-written code is unpleasant, low-status work that is easy to skip or rush. Even a diligent reviewer misses many of the pitfalls in §2.1–§2.3 — missed qualifiers and non-discriminating tests are exactly the failures human review is worst at catching. And the industry is visibly moving toward minimal human review (for example, autonomous "Ralph loop"-style agents that iterate with little oversight), which makes *automated* means of establishing high confidence a requirement rather than a convenience.

---

## 3. Principles

1. **Coding-agent independence.** Never require a particular agent; rely on stable artifacts — task text, Git revisions, source, tests, builder declarations, PRs, Issues, CI results. Agent-specific integrations may add convenience later but are never required. (§4)
2. **Evidence over trust.** Always report *which kind* of evidence supports a conclusion: builder claim < static inference < execution-confirmed < CI-confirmed (§8). None alone guarantees correctness.
3. **Requirements stay outside.** The product does not manage a backlog or replace Issues/Jira. It imports/snapshots the relevant requirement and converts it to obligations; the origin system remains source of truth.
4. **Tests stay inside the repo.** It evaluates repo-native tests and may recommend more, but does not maintain an external acceptance suite. The agent/developer implements recommended tests using project conventions.
5. **Execution is optional, scoped, and reuses the project's own harness.** It never provisions environments or reproduces app architecture. It runs the project's own pytest on a *targeted subset* of candidate tests and degrades to static analysis where that produces nothing. Full definition in §8.
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

**Outputs:** interpreted obligations with their requirement links and mandate coverage; implementation-coverage classification; enumerated defects per obligation; test-to-defect verdicts and unjudged pairs; test-evidence assessment *with its denominator and evidence tier*; missing/weak obligations; potential unrequested changes; builder-declaration discrepancies; **recommended new tests (structured for automated pickup, §9.5)**; a next instruction, retrieved on demand per criterion rather than written to a file; explicit confidence limitations.

```
Developer writes task → agent implements → agent reports complete
    → Local Completion Check runs (static; optional targeted execution)
    → gaps returned to the agent → implementation revised → PR opened
```

Requires no GitHub App, linked Issue, CI access, hosted service, or agent chat history. Initially a local CLI. The execution tier (§8.2) runs when the review decides a run would be consumed; there is no test-command setting, and pytest under the configured interpreter is assumed.

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

Convert task/issue into discrete obligations, typed as: functional, boundary, error handling, invariant, regression, compatibility, explanation/observability, docs/config, human-review, or **test-demand**. Distinguish **explicit** obligations (directly supported by source text), **reasonable inferred** obligations, and **open questions** the text leaves unresolved.

**As built (DR-202, DR-204, DR-216, DR-144, DR-259).** The parser carves the task file into a deterministic registry of leaf blocks, each with a positional id (`task-01`, `constraint-03`); every non-heading block is inside exactly one registry span or is recorded as unread source, which counts against mandate coverage. Derivation is run one requirement per call with the whole file shown as context, is blind to the code, and may split one requirement into several obligations or decline it, but may not attach a requirement to an obligation derived from another requirement: every derived obligation is named by exactly one requirement, enforced by the response shape. Every requirement carries an explicit **disposition**: yielded obligations, yielded none with a stated reason, or raised an open question. A response that leaves a requirement without one is rejected at parse rather than recorded as a soft finding. A separate **linking** pass then asks, per pair of obligations, whether they state the same requirement, and merges a cluster only when every pair in it was confirmed; pairs are prefiltered by embedding distance (cosine distance 0.10 on `voyage-3.5-lite`), erring toward under-merging because a wrong merge destroys a requirement silently. **Open questions are resolved against the diff by the model**, and a question the diff settles yields a derived obligation that is judged like any other. There is no user-confirmation step in the local checker; a question the diff leaves open produces nothing, and that requirement is reported as unjudged. **Mandate coverage**, the count of requirements that yielded something judgeable, is derived from dispositions and bounds the verdict (§10.1): a review that could not judge part of the mandate cannot report no material gaps.

**test-demand** is the obligation a mandate states when it asks for a *test* rather than for a behavior — "a test asserts that X", "add a test covering X". It is not the same obligation as X, and the difference is not stylistic: an implementation that already exhibits X, with nobody having written the test, satisfies the obligation to deliver X and violates the demand for the test. Adding the behavior and adding its test are separate pieces of work. The type exists so that difference survives decomposition; without it the two collapse into one statement, and the review reports the behavior delivered while the demanded test was never written (DR-232).

A consequence of the defect-first design (§9.3): `test-demand` and `human-review` obligations get no defect set, because enumerating ways to fail "a test asserts X" would require the enumerator to look at the tests, which it is forbidden to do (DR-313). A `test-demand` obligation that requires test evidence therefore reaches the evidence stage with no defects and is reported `indeterminate` (observed on both #372 Gate 2 runs). That is a known gap, filed, not a design intent.

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

**Scope boundary — the product does not police the user.** It assumes the repository's existing test suite passes (verifiable from the CI logs) and does not re-run or grade the user's green tests to check up on them. Execution exists only to produce evidence the existing tests do *not* already provide: injecting a named plausible defect into a copy of the code and observing which candidate tests fail under it (§8.2). The one exception is a control run of the candidate tests at head, whose failures are set aside and never reported as findings. Establishing that the suite is green is the user's and CI's responsibility, not the reviewer's.

### 8.1 The evidence ladder (weakest → strongest)

1. **Builder claim** — the declaration asserts a behavior. A starting point, not evidence.
2. **Static inference** — the reviewer reads code/tests and judges, without execution, whether an obligation is addressed and whether a test would fail under a named defect. Always available, but a prediction.
3. **Reaches the code (coverage-confirmed)** — a test is run with coverage and observed to exercise the defect's lines. *Defined, not built.* Nothing produces this tier today, and DR-171 withdrew coverage as a selector after it was measured to miss 43 of 268 recorded kills (tests that detect a defect through a file read, or through the absence of code elsewhere).
4. **Kills the defect (execution-confirmed)** — a named defect is injected at its implicated lines and the candidate tests are run. Some test goes red: the defect is killed and those tests discriminate. None goes red: the defect survives and every candidate test is observed not to discriminate for it. Strongest tier the product itself produces. *Built, gated off:* see §8.2 for why no criterion currently reaches it.
5. **CI-confirmed** — the relevant test ran and passed against the reviewed commit in the project's own CI (Mode B). *Not built; Stage 2.*

The achieved tier is recorded per criterion: each covered defect takes the strongest tier among the verdicts that kill it, and the criterion takes the weakest across its defects; a static inference is never presented as execution-confirmed. `evidence_tier.py` enforces which component may produce which tier.

### 8.2 Surgical, hypothesis-driven mutation (not whole-suite)

Whole-suite mutation (mutate everything, re-run the full suite many times) is deliberately avoided. Instead, the enumeration stage (§9.3) has already named **specific plausible defects** for each criterion, each with the code region it implicates (e.g. "uses calendar-month boundaries instead of the contractual 26th-to-25th accrual period"). The execution tier injects *one defect at a time* at those lines and observes which candidate tests go red, converting "this assertion looks non-discriminating" into "the branch was flipped and the test stayed green."

What is surgical is the **mutant**, not the test set: one defect, one contiguous span replacement inside the region that defect names, never a sweep of mutation operators across a file. The mutant is run against every **candidate test** test discovery selected for the change, and never against the full suite (§3 principle 6, §17). Which candidate tests go red *is* the test-to-defect mapping; there is no cheaper prior mapping to narrow the set with, since the static per-pair judgment that could supply one is the cost execution exists to avoid (DR-171, revision of 2026-09-14).

**How an edit is built, as of #338.** The edit is written by a model shown the defect's two behaviors (what the code must do, what it would do instead) and the implicated region with its enclosing definition and callers, tests withheld. Up to three candidate edits are asked for per defect, each later request showing the earlier refusals; a configured headless coding agent may be asked for one more, confined to a copy of the project with the tests deleted (DR-338, off by default). Five text checks run before a candidate is injected: it applies; the file still parses where it has a parser; the span lies inside a region the defect names; the edit is bounded in size; and it differs from the text it replaces once comments and whitespace are removed. Two gates run after: no kill is counted when every failing test failed on a missing name or a module that no longer imports, and the edit is set aside when it fails more than 7.5% of candidate tests and more than ten of them. A decline ends the loop and is recorded with its reason; a claim that the code already has the defect ends it and is reported as needing human review. Every attempt is recorded with a typed outcome (`killed`, `survived`, `not_mutable`, `not_a_code_property`, `no_usable_edit`, `not_attempted`, `already_present`) and the mutant text, so a reader can see what was injected and disagree with it.

**Why tier 4 is gated off today.** An injection result is evidence about a defect only if the edit actually made that defect true. Measured by hand over eleven audits of one review (`docs/audit-protocol.md`, DR-171), about half of the edits did not: 25 of 48 passing edits on `gpt-5.4` put the named defect into the code, 31 of 52 after the several-candidates change. The rest repaired a defect the code already had, changed something other than the defect, or broke far more than it; 8% changed no behavior at all, and three of those four "survived," which is a false accusation against the tests. A verifier that asks a model whether the edit matches its defect refuses 76 to 77% of bad edits against an adoption bar of 80%, and wrongly refuses 16 to 26% of good ones against a bar under 10%. So `verify_edits` defaults to off, and with it off no observed result is **settled**: none reaches `defect-killed`, every defect still goes to the static judge, and a test pins that nothing derives a rating from an unverified attempt. The tier begins to earn when a verifier clears its bar.

**What execution earns in the shipped configuration.** Routing. The pair judgment was 80 to 90% of a review's cost before similarity-ordered judging ($10.09 of $11.59 on #45 Gate 2 run 3) and is 25 to 70% on reviews since #348, and an observed edit, verified or not, tells the review which pairs are not worth a model call: if some candidate test went red under the edit, the tests that stayed green need not be asked about. That is recorded as an unjudged pair with its cause, never as a verdict, because a red test under an unverified edit proves the edit changed behavior, not that the named defect was injected. The review decides for itself whether running the tests is worth doing, from whether anything consumes the result; there is no operator flag (`decide_execution`, ruling of 2026-09-18).

**What injection cannot express.** A defect of absence (`not_wired`, `missing_case`, `documented_not_implemented`) has no span to replace when the code is already correct; such defects stay on the static judge on any repository, as does any defect whose region has no text at head. Markdown and other non-Python files can be mutated, which is how tests that read a document prove themselves.

### 8.3 Feasibility detection and graceful degradation

The feasibility probe described in DR-170 (feasibility earned by observation, declined by the project's own declarations, thresholds as configuration with conservative defaults) is decided but **not built**. What exists: a sandbox with a network block and time budgets (`execution/sandbox.py`); pytest collection of the candidate ids as a per-project gate (DR-170 decision 5); a baseline run of the candidate tests at head, where a candidate test already failing is set aside with a recorded reason rather than halting the review (a later ruling reversed DR-171 decision 6; recorded in `mutation/baseline.py`, not yet in the DR); and the worth-doing decision above. The test interpreter is configuration, never inferred from the project. Degradation is structural rather than a special case: a repository where no edit can be built or run is one where every pair goes to the static judge and every verdict stays at tier 2, which, with verification off, is also the current behavior everywhere.

### 8.4 Closing the recommendation loop

A test the agent writes to satisfy a recommendation can itself be weak or circular — the assurance problem one level up. The intended answer is that, where execution is available, after a recommended test is added the product injects the defect it claims to catch and confirms the new test fails, and only then is the gap *demonstrably* closed. **Not built.** Recommendations are emitted (§9.5); confirming a newly added test is not a stage, and depends on tier 4 earning its keep first.

---

## 9. Analysis: obligations, coverage, test evidence

### 9.1 Acceptance criteria

Convert the mandate into discrete, observable criteria. Example mandate: *"Add floating-rate bonds using an index curve plus contractual spread. Accrual periods run the 26th through the 25th. Missing rate observations must produce an explicit error. Existing fixed-rate behavior must not change."* Derived criteria: (1) coupons use index + contractual spread; (2) rate selection follows the 26th-to-25th period; (3) missing observations produce an explicit structured failure; (4) fixed-rate results unchanged; (5) outputs expose the selected observation and spread where the mandate requires. Each criterion retains: source text, the requirement ids it was derived from, type, importance, explicit/inferred flag, observable behavior, implementation areas, its enumerated defect set (§9.3), the tests that would fail on each defect, evidence assessment with its denominator, and achieved tier.

### 9.2 Implementation-coverage review

Classify each obligation against the diff: **Addressed** (credible implementation response); **Partially addressed** (relevant behavior present but a qualifier/branch/condition missing); **Not addressed**; **Unclear** (may be indirect; static evidence insufficient); **Requires non-code evidence** (docs, visual behavior, deploy config, usability). This finds likely incompleteness before acceptance; it does not prove runtime correctness. It also flags likely **unrequested** behavior changes — diff regions that correspond to no obligation. Unrequested-change detection is the **dual** of gap detection: a gap is an obligation with no matching code (obligation → code); an unrequested change is code with no matching obligation (code → obligation). It is therefore obligation-*less* by construction and is scored on its own axis (§11.1), never folded into the gap metric.

Every unrequested-change finding carries a **disposition**: **in service** (a refactor/interface edit needed to deliver an obligation — accept, optionally note), **separable** (a coherent, possibly valuable, but distinct unit of work — recommend splitting into its own PR/backlog item), or **risky** (touches public surface, dependencies, or adjacent behavior in a way that could hide a regression — scrutinize). `separable` and `risky` are not exclusive, and separability is orthogonal to value: high-value extra work is still flagged when it does not belong in this change. The separability test reuses coverage — *would the task still be complete if this change were removed?* — sharpened by whether the change adds new self-contained public surface, ships its own tests, and lives in files disjoint from the obligation-mapped ones. Disposition thresholds are a **policy setting** (strict vs. loose scope expansion), since where the acceptable-expansion line sits is a shop norm; the strongest "own backlog item" phrasing sharpens once the backlog is available as an input (Mode B).

Because the tool sees a change with no obligation but not the author's *intent*, unrequested-change findings are **high importance, low certainty**: surfaced prominently but framed as advisory ("here is what changed that no obligation explains — your call"), not as defect claims. Detection is deliberately recall-forward — surface everything unexplained, let the user dismiss the incidental ones — which is safe precisely because the advisory framing makes false positives cheap. (Rationale and scoring in DR-081 / §11.1.)

### 9.3 Test-evidence analysis

Central question per testable criterion: **would the available tests fail if the implementation violated this criterion in a plausible way?** A test is not strong merely because its name resembles the requirement, it invokes changed code, it's in a passing suite, or it raises coverage. Where a verified injection exists this is answered by observation; today it is always a prediction (§8.2).

**Defect first (DR-312, DR-313, DR-314; cut over 2026-08-31).** The engine does not map tests to obligations and then judge them. It runs three stages in this order:

1. **Enumerate defects.** For each obligation of an enumerable type (everything except `test-demand` and `human-review`, including obligations owed no test), a model produces a persisted set of typed defect records: id, type, free-text description, the two behaviors (expected and defective), and the code region implicated. The enumerator sees the obligation and the changed code and **never the tests**; it runs before test discovery so that blindness is structural rather than promised. Types come from a short checklist walked per obligation type (four shared: `qualifier_ignored`, `condition_inverted`, `scope_too_narrow`, `not_wired`; two per obligation type, such as `boundary_wrong_side` or `error_swallowed`; plus `other` with a free description). A reasoned empty set is a valid output for an obligation with no plausible static defect.
2. **Judge pairs.** Every (defect, test) pair that a reachability prefilter cannot prove unreachable (in practice it excludes almost nothing) is a candidate for one question with a fixed answer shape: **would this test fail if the implementation contained this defect?** Tests are judged in order of similarity to the defect description and judging stops once a defect is covered (#348). Every pair not judged is recorded as unjudged with its cause (prefiltered, unanswered, passed under an edit, defect already covered); it is never read as a verdict. Where execution is on, injection decides pairs first and the static judge takes the remainder (§8.2).
3. **Derive support.** The evidence class is arithmetic over the recorded facts, with no model call: each defect is *covered* (some verdict says a test would fail on it), *uncovered* (no verdict does), or *unknown* (it has an unanswered pair).

| Defects | Class |
|---|---|
| all covered | Strongly supported |
| some covered, with or without unknowns | Partially supported |
| none covered, none unknown | Unsupported |
| none covered, some unknown | Indeterminate |
| reasoned empty enumeration | No plausible defect (terminal: test evidence is not obtainable at this tier) |
| criterion needs non-test evidence | Routed to non-code review: `required_evidence = neither`, decided at decomposition and read by the verdict. The `requires_other_evidence` class name is retained but not produced. |

**The denominator is always disclosed.** Every rendering carries the count it reduced over: *"strongly supported — kills 3 of 3 enumerated defects (static prediction)"*, including the honest thin case, *"1 of 1"*. There is no minimum-enumeration floor for a strong rating; any threshold is arbitrary and invites gaming from the other side, and the disclosed count lets the reader weigh a thin enumeration themselves. This is the mitigation, not a cure, for the fact that the enumerator is a model producing its own denominator; §11.1 scores enumeration recall separately from pair-verdict accuracy so the two failures can be told apart.

**`nominally_supported` is defined and not produced.** The earlier vocabulary distinguished a present, relevant-looking test that catches nothing from no relevant test at all. The pair question answers yes or no, so both come back identical, and when injection replaces prediction the distinction becomes unmeasurable in principle: an injected defect either fails a test or it does not. A criterion no test would fail on is `unsupported`. The name remains in the data model for compatibility with older ground-truth labels.

**Why a derived class.** Three measured defects of the judged design forced this (DR-173, DR-180, DR-164): the mapping question ("would this test fail if the obligation's behavior were missing or wrong") had no defect in hand and was answered inconsistently (23 distinct answers in 25 draws at temperature 0); a mapping miss was unrecoverable, so the review prescribed tests that already existed; and the strength denominator was chosen by the same call that graded against it. Deriving the class makes a rating that moves have a moved input behind it, and makes every rating recomputable from the stored review.

What the judge is asked to weigh, through the defect description: whether inputs distinguish competing interpretations; whether boundaries are exercised; whether negative behavior is tested; whether assertions target the required result; whether expected values have independent provenance; whether mocks bypass the behavior; whether the test reaches the relevant path.

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

**A recommendation is an uncovered defect.** Under the defect-first design (§9.3) the payload above falls out of the data model: every recommendation cites a defect record whose violation links to its obligation's text, so a recommendation can neither restate evidence that already exists nor target something that is not a violation (the two failures DR-312 lists). Recommendations are emitted in a **structured, machine-readable form** so a coding agent or harness can pick them up and add the test directly, and each is complete enough that the gap can typically be closed in a **single iteration**. The product recommends rather than modifies code; the recommendation is retrieved on demand per criterion (`acceptance recommendation --criterion <id>`) and may surface in the CLI, the coding agent, a PR comment, or the GitHub check. It is never written to a file that outlives the run that produced it. Confirming a subsequently added test (§8.4) is intended and not built.

---

## 10. Workflows

### 10.1 Local Completion Check

1. Capture the task file. 2. Coding work occurs (any agent/human). 3. Optional builder declaration produced. 4. Checker reads task, base revision, diff, relevant source/tests, and declaration if present. 5. Decompose: parse the registry, derive obligations per requirement, link duplicates, resolve open questions against the diff and derive obligations from the resolved ones (§7.3). 6. Enumerate defects per obligation, before any test is discovered (§9.3). 7. Discover candidate tests. 8. **Execution tier, when the review decides it is worth running** (§8.2): baseline the candidate tests, build and inject edits, observe results, route pairs. 9. Judge the remaining (defect, test) pairs statically. 10. Derive each criterion's support class (§9.3) and extract the test evidence the declaration comparison reads. 11. Implementation-coverage review and unrequested-change detection (§9.2). 12. Recommendations from uncovered defects (§9.5). 13. Compare builder declaration against requirement/code/tests. 14. Produce completion result: *no material gaps / incomplete / needs clarification / needs non-code review / unable to determine.* The verdict is a pure function of the findings, bounded by mandate coverage: a review that could not judge part of the mandate cannot report no material gaps, and any criterion owed tests that is rated below strong support, or indeterminate, blocks a positive result (`no plausible defect` and code-only criteria do not). 15. Make the next instruction available when gaps exist — pulled per criterion via `acceptance recommendation --criterion <id>`, never pushed to a file that outlives the run that wrote it, e.g.:

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

Against a labeled set of changes with known gaps: **gap detection (recall)** — of known material gaps, how many are found; **false-alarm rate (precision)** — of reported gaps, how many are spurious (a noisy reviewer is ignored, so this matters as much as recall); **obligation-decomposition accuracy** vs. a human-verified decomposition; **enumeration recall**, per defect type, against human-labeled defect sets, and the share of defects typed `other` (a rising share is a taxonomy gap, a near-zero share beside poor recall is defects forced into the nearest slot); **pair-verdict accuracy**, precision and recall on "this test fails," against executed kill/survive labels, currently computed by the Jev experiment's scorer (`docs/experiments/jev/m52/score_heldout.py`) rather than by `benchmark/`; and **twin splitting**, the rate at which one requirement yields two obligations, recomputed over the rendered reports' test links, which since the cutover are the derived test → defect → obligation edge. The two retired metrics, test-to-obligation mapping accuracy and evidence-classification agreement, remain declared in `benchmark/scoring.py` with a warning that they measure stages that no longer exist, and a test fails if that warning is softened. Because the review has two axes, gap detection (obligation → code) is complemented by **unrequested-change detection — precision and recall** — on the code → obligation axis: obligation-less findings scored against obligation-less ground-truth changes, a separate metric rather than part of the gap number. Precision matters here (legitimate incidental edits are the false positives) but detection is tuned recall-forward and kept advisory; this is scored on the hand-built archetype layer in Stage 1, with real-change scoring deferred because labeling a change "unrequested" is a judgment about intent (see DR-081).

### 11.2 Sourcing the benchmark without fabrication

Layered by source, from real changes:

- **Ready-made labeled instances** — public benchmarks pairing real GitHub issues with gold patches and explicit pass/fail test sets (the SWE-bench family and curated subsets; Python bug datasets such as BugsInPy) give task→implementation→test-evidence tuples from real projects. Base layer. *Exact dataset selection, subset sizing, and licenses are resolved in `docs/DR-168-benchmark-dataset-selection.md`.*
- **Real merged PRs** — mining Python repos for PRs that close linked issues and add/modify tests yields abundant real (issue→diff→tests→CI) tuples. Reverted or follow-up-"fix" PRs give natural **missed-obligation** labels — the follow-up documents what the first change missed.
- **Offline mutants for objective test-strength labels** — inject a mutant into real code with a real passing test; if the test still passes, that is ground-truth "weak evidence," built from real code and a real test with no fabrication. Uses mutation offline to *generate labels*, independent of whether execution ships in the product.
- **Real agent output (on-thesis layer)** — run actual coding agents on real issues; label their implementations against the known gold patch and tests. Most representative data available, since the product reviews agent work.
- **A thin hand-curated archetype set** — the demonstration scenarios (§13.5) for interpretability and readability checks only; not the basis for accuracy claims.

**What exists as of 2026-10-16.** Two of the five layers have code. The offline-mutant layer is built on BugsInPy: 231 executed kill/survive cases from 52 pinned bugs across four projects, each a fixed-operator edit run against a real test (`benchmark/mutants/`, #372); it is the ground truth for the pair judge (§11.5) and is dominated by constant changes (140 of 231), so a judge scored on it is mostly scored on constant edits. The archetype layer is 13 hand-built fixtures with human-reviewed defect-set labels. DR-168 selects SWE-bench Verified as the primary labeled-instance set, but nothing in the code references it yet; the real-merged-PR and real-agent-output layers have no code. No gap-recall or false-alarm rate on real changes has been measured.

### 11.3 Learning from users

Beyond external data, the product should improve from its own use: a user editing the suggested acceptance criteria or obligation decomposition (a correction to interpretation); overriding a finding as a **false positive** (a reported gap that wasn't real), or flagging a **false negative** (a real gap the tool missed); accepting or rejecting recommended tests. Each correction would be captured as a labeled case — the same shape as a benchmark case (§15). **Not built.** There are no users other than the author, and no override or correction capture exists in the code.

### 11.4 How validation feeds the product

Results tune obligation decomposition and evidence classification, set defensible default confidence language, decide which criterion types the reviewer handles reliably enough to report on, and produce the headline accuracy figures the product stands behind. The audit protocol (`docs/audit-protocol.md`) governs how a change to a model stage is measured before it is adopted: one run per arm is not separable from noise at the eight-point level, so a change is adopted on a count that moves far more than that, or not at all.

### 11.5 Measured so far

Every figure below is from one repository (this one) unless it says otherwise, and most are from one review of it. None is a headline accuracy figure; together they say where the reviewer is weak and why the design is shaped as it is. Dates are when the measurement was made.

**Reviewer instability, and its direction (DR-180, 2026-08-04).** Three consecutive runs over a byte-identical task file disagreed on 8 of 12 obligations' evidence class. In 7 of those 8 the lower rating was the correct one; the most serious was a `strongly supported` on a code path that deleted a file in the user's repo and reported nothing. The judge errs toward "looks fine." Damping it to stabilize ratings would have made it worse; the answer was to derive the class instead of asking for it (§9.3).

**Mapping instability (DR-173, 2026-08-21).** The retired test-to-obligation mapping gave 23 distinct answers in 25 draws at temperature 0 and seed 0 on one pairing, right in 80% of them. Prompt wording was a well-powered null over 1,472 calls. A forced per-obligation verdict cut the twin-split rate by destroying 59% of correct mappings. The stage was retired on this evidence.

**Mapping shedding (DR-164, 2026-08-03).** On a review of this repo the mapping call returned a schema-valid entry per test with an empty obligation list for 80 of 96 tests at 2.5% context use; zero of 17 obligations mapped, and the review reported "your change has no tests." A reviewer failure rendered identically to the finding the tool exists to produce. Request partitioning and a rule that every supplied id must be accounted for (DR-163; DR-302 later narrowed the per-call id enum to the ids identical across batches) came from this; any NO-MATERIAL-GAPS verdict from before that work should not be cited.

**Decomposition (DR-202, 2026-08-06; #317, measured 2026-08-21).** Precision about 1.0, recall about 0.75 against a hand decomposition of one task file: 4 of 15 completion expectations and 5 of 8 scope exclusions lost. The decomposer over-answers 23% of batches that contain a `task-*` requirement (8 of 35). Measured on one author's task files, which carry headings real tickets will not.

**Pair judge (`docs/experiments/jev/FINDINGS-m5.2.md`, 2026-10-13).** On 92 held-out BugsInPy cases, 95% Wilson ranges: the shipped judge (GPT-5.4 Mini, up to 40 cases per call, shown only the test and the defect) 66.3% (56 to 75), precision on "fails" 0.789. Mini asked one case at a time with the requirement and original code 82.6%, so most of the weakness was how the question was asked. Jev then Mini, the adopted design (DR-379), 85.9% (77 to 92), precision 0.845, $0.0001 per judgment, Jev deciding 96.7% of cases alone. Jev then Opus 93.5% at 45 times the cost; Opus alone 94.6%. The ranges of the cheap designs overlap. The cut-offs were fitted on 137 tuning cases and probably overfit (91.2% tuning against 85.9% held-out). Not wired into the pipeline as of this revision.

**Edit validity and the verifier (DR-171, 2026-09-16 to 09-23).** See §8.2: 52% to 60% of passing edits inject the named defect; 8% change no behavior; the verifier is at 76 to 77% catch rate against a bar of 80% and 16 to 26% false alarms against a bar under 10%. Several candidates per defect took "defects with no usable edit" from 7 to 0 on 64 defects at $0.025 per defect.

**Prefilters (`docs/experiments/coverage-prefilter`, `prefilter-committee`, `rank-prefilter`, 2026-08-31 to 09-22).** A coverage prefilter excludes 61% of 23,808 pairs but loses 43 of 268 judge kills (84% recall), which is why coverage is not a selector. Cosine-threshold committees exclude 26 to 31% at one or two kills lost and do not transfer between corpora. Ranking each defect's tests by similarity to its description, the top 20 of 166 to 496 tests hold a kill for 92.6% to 97.7% of killed defects across three corpora; judging in that order and stopping at the first kill cuts pair judgments 81 to 89% with ratings unchanged by construction. The oracle for these figures is the judge's own kills, which are themselves 66% accurate.

**Cost.** A full review of this repository cost $4 to $12 before similarity-ordered judging, with the pair stage 80 to 90% of it; since #348 (2026-09-21) a review runs $1 to $3 and the pair stage is 25 to 70%. One edited line in the enumeration prompt invalidates every stored defect set and re-judges every pair: about ten dollars at #45's scale before early stopping, around a dollar now.

**Verdict distribution over committed dogfood logs** (one verdict per run directory, 105 runs): 91 INCOMPLETE, 11 NO-MATERIAL-GAPS, 2 UNABLE-TO-DETERMINE, 1 NEEDS-CLARIFICATION. The tool reviews its own changes at every gate and most changes fail the first time.

---

## 12. Pipeline, determinism and carry

The system pursues one explicit goal, *determine whether the visible implementation and available evidence are sufficient for the requested task*, as a **fixed, deterministic pipeline**, not an agent. An earlier version of this section described autonomous repository navigation and tool use under the model's own direction. DR-202 rejected letting the decomposer direct its own retrieval with tools, on replay grounds, and the same reasoning is why no stage does: a review whose model calls cannot be recorded and re-run byte-for-byte cannot be measured, and measurement is the product's first commitment (§2.5).

**Bounded retrieval.** Each model stage is shown a fixed set of inputs assembled by code: the task registry, the diff with surrounding context, and, for the code-facing stages, each changed region's enclosing definition and its in-repo call sites, matched one hop by name, never a call graph. Test files are withheld from the enumeration and edit-building stages by the change set's own test-path rule. Retrieval decides what each call sees; the model decides nothing about what to read next.

**Fixed answer shapes.** Every model call has a response schema, runs at temperature 0 with a fixed seed, and is content-addressed by model, messages, schema, seed and stage controls. Transcripts are recorded and replayed by that key, so two runs over the same inputs are byte-identical and a benchmark scores recorded answers with no live calls. An answer the schema cannot bind (an id that was never supplied, a requirement left without a disposition, a verdict in a shape the stage did not define) is rejected and recorded as an unusable answer, which forces `indeterminate` rather than being read as a finding. Model output failure is itself a tracked failure class (DR-163, DR-164, DR-302).

**Execution as the one observe-and-act loop.** The execution tier (§8.2) is the only place the system acts on the world: it edits a copy of the project, runs tests, reads the result, and asks again on refusal. It too is replayable: candidate edits come from re-asking with the refusals shown, so each request records on its own key, and a mutant run's output reaches no model and no review state beyond its typed outcome.

**Structured review state and carry.** The review persists obligations with their requirement links, defect sets, pair verdicts, mutation attempts, findings, evidence tiers and open questions, so conclusions link to evidence and ratings can be recomputed from the stored review. Re-review is incremental one level down from the rating: a defect set carries while its obligation and its implicated region's contents are unchanged, a static pair verdict carries while the defect and the test's source digest are unchanged (an executed verdict is never carried), and the class is always recomputed as free arithmetic over the carried parts (DR-312 decision 6, DR-293). Carry keys exclude neighboring context, so an unrelated change cannot move a key (DR-269). Implementation coverage is re-derived every run. Findings are never carried; only recommendations for answers that were never obtained are. A user who adds one test between two `--continue`d runs pays for judging that test's pairs against the open defects and nothing else. Two earlier carry designs were built and retired: file-level staleness, which collapsed strongly-supported from 37 obligations to 4 when one test was appended, and anchored re-judgment of ratings, which became moot once the class stopped being a model's answer.

Concretely the model decides: how a requirement splits into obligations and whether it yields any; whether two obligations state the same thing; how the diff resolves an open question; which defects could fail an obligation and where; whether a given test would fail under a given defect; what edit would make a defect true; whether a diff region corresponds to an obligation and, if not, its disposition; and whether the declaration matches the mandate. Code decides everything else: the registry, mandate coverage, the evidence class, the tier, the verdict, what carries, and what each call is allowed to see.

---

## 13. MVP

### 13.1 Objective

Show the system can independently identify meaningful completion and test-evidence gaps in AI-assisted changes without depending on a particular coding agent — with **measured accuracy against a real-change benchmark**, not merely plausible output. Complete MVP = a **local completion checker** (static, with optional execution for hermetic repos) + a **validation benchmark and harness** (§11) + a **GitHub-native acceptance review** applying the same analysis. The local checker and its benchmark are the first milestone and independently useful; GitHub completes the product experience. *(Ordering/effort: the GitHub backlog.)*

### 13.2 Scope

**Environment:** Python; pytest; Git; GitHub repos, Issues, PRs, Actions; JUnit XML / pytest-compatible reports where available; Markdown task files and declarations. **Execution tier** runs by the review's own worth-doing decision in a sandbox with time budgets (§8.2); the hermeticity probe is not built, and static judgment covers whatever execution does not settle. **Coding-agent independent** per §4; no direct agent integration required.

### 13.3 Stage 1 — Local Completion Checker

Capabilities: **task ingestion** (read `current-task.md`; extract behavior/constraints/exclusions/expectations; flag ambiguity; produce structured obligations); **Git change analysis** (base↔head; read changed source/tests; config/dependency changes; retrieve surrounding code); **builder-declaration ingestion, optional** (compare declared mandate/implementation/tests/exclusions/assumptions/limitations with task and diff); **implementation-coverage analysis** (§9.2, incl. unrequested-change detection); **defect enumeration** per obligation, test-blind (§9.3); **test discovery** (added/modified and relevant existing candidate tests); **pair judgment** of (defect, test) pairs, similarity-ordered with early stopping, every unjudged pair recorded; **derived support** with disclosed denominator; **execution tier** (§8.2: baseline, edit building, injection, pair routing; verification gated off; coverage tier and recommended-test confirmation not built); **completion result** (obligation findings with requirement links, test-evidence findings with denominator and tier, mandate coverage, enumerated defects, unjudged pairs, mutation attempts, declaration discrepancies, confidence limitations, overall result, next instruction retrieved on demand).

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

Scenarios 1 to 9 exist as archetype fixtures and ground-truth labels; 3 is now expected to classify as `unsupported`, not nominal (§9.3), and its labels, like ten others, still say nominal, so the evidence scorer records a disagreement there until they are relabelled (#326). Scenarios 10 to 13 are Stage 2. Scenario 14 is unreachable while edit verification is off (§8.2).

### 13.6 Success criteria

**Local quality:** decomposition materially accurate to the developer; important omissions found in selected real agent changes; enumerated defects on point; classifications understandable and defensible; recommended tests specific enough to implement; next-instruction output materially improves the next agent iteration. **Measured accuracy:** reportable gap-detection and false-alarm rates on the benchmark, with pair verdicts agreeing with executed ground truth at a defensible rate (§11); as of this revision the first is unmeasured and the second stands at 66% shipped and 86% in the adopted, unwired design (§11.5). **GitHub quality:** adoptable without changing agents; existing Issues/PRs/tests/Actions suffice; check runs against the correct commit; output useful directly in the PR; static / execution-confirmed / CI-confirmed evidence distinguished; no duplicate requirements entry; declaration light enough to stay optional locally. **Trustworthiness:** findings link to requirement/code/test; inferences labeled; evidence tiers explicit; the denominator behind every rating shown; positive results don't overstate correctness; users can see why a criterion was classified as it was. The last of these is weakened, not abandoned, by DR-379: a pair verdict Jev decides carries a probability and no reasoning, and the report must say so where it applies.

### 13.7 MVP non-goals

Will not: require/privilege a specific agent; read full agent prompt histories; replace Issues; manage a backlog; provision environments the project doesn't already support; run arbitrary or non-hermetic suites; operate the deployment pipeline; modify source; auto-generate/commit tests; support arbitrary languages or CI providers; do browser/mobile testing; analyze production telemetry; provide formal verification; or guarantee defect-free software. The optional execution tier runs only the project's own hermetic tests in a sandbox for targeted confirmation — deliberately narrower than "executing arbitrary applications."

---

## 14. Product boundary

**Owns:** requirement interpretation for the reviewed change; obligation/criteria generation; implementation-coverage analysis; test discovery, pair judgment and derived support; targeted execution of the project's own tests, decided by the review; builder-declaration comparison; CI-evidence interpretation; evidence-gap identification; additional-test recommendations; completion/acceptance recommendations; review provenance, evidence tiers, and confidence limitations; and its own benchmark validation.

**Does not own:** requirements or backlog management; agent selection or prompt history; source authoring; test implementation; full-suite execution and CI orchestration; provisioning environments the project doesn't already support; build/deploy pipelines; automatic PR merging; comprehensive UI testing; production monitoring; formal verification; guarantees of correctness.

---

## 15. Conceptual data model

- **Project** — repo; default branch; test framework (pytest assumed); source/test locations; test interpreter (configuration, never inferred); review policy; GitHub config.
- **Task source** — local file or Issue; identifier; snapshot; text; references/attachments.
- **Requirement registry** — the task file carved into leaf blocks, each with a positional id, span, and disposition (yielded / no obligation with reason / open question); provable tiling of the source (§7.3).
- **Mandate interpretation** — derived obligations with their requirement links; linking results; open questions and their resolutions against the diff; mandate coverage.
- **Builder declaration** — the nine template sections (§7.4).
- **Change set** — base/head revisions; changed files; source/test diffs; config/dependency changes.
- **Obligation / criterion** — description; type; source spans, with requirement ids via the requirement map; importance; explicit/inferred; observable behavior; required evidence (code only / test / neither); **achieved evidence tier**; derived support with its counts.
- **Defect** — id; obligation id; type (taxonomy or `other`); description; expected and defective behavior; implicated code regions. A set per obligation, or a reasoned empty set; carried on the digest of its obligation and regions (§9.3, §12).
- **Pair verdict** — defect id; test id; fails / survives; short reason (verdict arm only); tier (static or defect-killed); carried on the digests of the defect and the test. **Unjudged pair** — defect id; test id; cause (prefiltered, unanswered, passed under edit, defect already covered).
- **Mutation attempt** — defect id; descriptor (file, span, replacement); candidates asked and set aside with causes; candidate used; outcome (killed / survived / not mutable / not a code property / no usable edit / not attempted / already present); verified or not; the tests that failed.
- **Execution decision** — whether the project's tests were run and the recorded reason.
- **CI evidence** — workflow; run id; commit; result; status; timestamp; report artifact.
- **Finding** — type; severity; related obligation (*absent for unrequested-change findings — obligation-less by construction, §9.2*); disposition (*unrequested-change findings only: in-service / separable / risky*); description; supporting evidence; evidence tier; uncertainty; recommended action.
- **Review** — mode; mandate; declaration; change set; requirement map; obligations; open questions; defect sets; pair verdicts and unjudged pairs; mutation attempts and set-aside tests; execution decision; findings; evidence tiers; limitations; recommendation; provenance; delta against the prior run; reviewed revision.
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

1 obligation(s) not fully implemented (active-filters-applied); 1 obligation(s) with non-discriminating test evidence (column-order-preserved).

Obligations:

  1. CSV generation implemented
       requirements: task-01
       code evidence: addressed
         1.1  export/csv.py#@@ -12,6 +12,28 @@
       test evidence: strongly supported — kills 3 of 3 enumerated defects (static prediction)  [tier: static]
         1.2  tests/test_export.py::test_generates_csv
         1.3  tests/test_export.py::test_escaping

  2. Active filters applied to the export
       requirements: constraint-01
       code evidence: not addressed
         (no corresponding change)
       test evidence: unsupported — kills 0 of 2 enumerated defects (static prediction)  [tier: static]
         (no mapped test)
         recommended test: Active filters applied to the export
           inputs:  an export taken with one active filter whose excluded rows differ from the unfiltered set
           detects: the export ignores the active filter set and emits every row
           full detail: acceptance recommendation --criterion active-filters-applied

  3. Displayed column order preserved
       requirements: constraint-02
       code evidence: unclear
         3.1  export/csv.py#@@ -40,3 +40,7 @@
       test evidence: partially supported — kills 1 of 2 enumerated defects (static prediction)  [tier: static]
         3.2  tests/test_export.py::test_columns

Mandate coverage: 3 of 3 requirements yielded obligations
  (none)

Unrequested changes:
  1. [separable] Export filename behavior changed
       export/naming.py#@@ -5,2 +5,6 @@

Ways the change could fail a criterion (what each rating is measured against):
  ...

Running the project's tests:
  the project's tests were run: 4 enumerated defect(s) name an editable region and pair routing is on, so an observation can decide which pairs are worth a model call — it still cannot count as evidence, because edit verification is off

Defects injected, and which tests caught them:
  [survived, NOT COUNTED] column-order-preserved/header-order-not-applied
    injected at export/csv.py lines 41-42: ...
    no test caught it; 12 candidate test(s) ran and none failed
    edit NOT verified to make the defect true, so this result is not counted; tier: static, and the defect went to the static judge
  ...

Pairs left unjudged (a criterion's rating cannot account for these):
  ...

Evidence limitations:
  ...

Next: retrieve a criterion's full recommendation with
  acceptance recommendation --criterion <id>
```

The tier line reads `[tier: static]` on every criterion in every committed review to date; `[tier: defect-killed]` appears once edit verification is adopted (§8.2).

**GitHub PR** — primary team interface: Checks, PR comments, file/line annotations, links to issue text and tests. No separate web app required for routine review. **Optional web app (later)** — installation/config, review-policy settings, historical reviews, user corrections, evidence exploration, cross-PR analysis, usage/quality reporting; secondary to CLI and GitHub-native.

---

## 17. Key risks and mitigations

- **Requirement ambiguity.** Preserve source text; separate explicit/inferred; ask targeted questions; don't silently invent obligations; allow correction.
- **Incorrect code/test interpretation.** Start with Python/pytest; link to exact code; express uncertainty; allow indeterminate; **elevate to executable confirmation where feasible** (§8); add language support incrementally.
- **Reviewer accuracy — the defining risk (§2.5).** Validate against a benchmark and report measured accuracy (§11); prefer execution-confirmed over prediction; tie conclusions to inspectable artifacts; label inferences and tiers; bound confidence language. Measured so far: the pair judge is the weak link (§11.5), and the judge errs toward "looks fine," so a false negative is the likely error and is invisible.
- **Model output failure read as a finding.** A schema-valid answer that silently sheds judgments (DR-164), mints an id (DR-163), or attaches a requirement to another requirement's obligation (DR-204) is indistinguishable from a real finding unless the shape forbids it. Every supplied id must be accounted for; every requirement must carry a disposition; every offered pair is answered or recorded unjudged; an unusable answer forces `indeterminate`.
- **The enumerator sets its own denominator (§9.3).** Mitigated, not removed: test-blind by construction, denominator disclosed on every rating, enumeration recall scored separately from pair accuracy. No floor on enumeration size.
- **A second vendor in the loop (DR-379).** Jev improves pair accuracy from 66% to 86% but returns no reasoning, sends test and project code to a second vendor, and its cut-offs are fitted on 137 cases. Mark its findings as carrying no reasoning; re-fit when more labels exist; keep Jev-then-Opus as the option if accuracy comes to matter more than cost.
- **A mutant that is not the defect (§8.2).** About half of model-built edits do not inject what they name, and a behavior-preserving edit that "survives" manufactures a false accusation against the tests. Mitigated by gating tier 4 on a verified edit, recording the mutant text, and refusing edits mechanically; the verifier itself is below its bar and off.
- **False confidence.** State the evidence type/tier; distinguish static / execution-confirmed / CI-confirmed; state the full app was not independently executed; bounded language; expose limitations.
- **Declaration gaming/omission.** Treat as a claim; compare independently with task/diff/tests; require structured sections when used; flag omissions/contradictions; never treat completeness as proof.
- **Generic recommendations.** Tie each to a criterion and plausible defect; specify inputs/assertions; use repo context; confirm the recommended test detects the defect where feasible; measure whether agents can implement it.
- **Execution safety/cost.** Sandbox with no network/secrets; targeted subsets only, never full suite; time budget; skip when feasibility checks fail.
- **Adoption friction.** Local mode usable with a task file and Git; declaration optional locally; agent-independent; reuse existing Issues/PRs/Actions; version-controlled config; advisory by default; no dashboard for routine use.
- **Cost/latency of deep analysis.** The pair stage is 80 to 90% of a review's cost. Controls in place: similarity-ordered judging with early stopping (81 to 89% fewer judgments); per-unit carry across `--continue`d runs; execution routing of pairs not worth asking. A shared input to a stage (its prompt, schema, model) is part of every carry key, so one edited line in the enumeration prompt re-judges every pair; sequence prompt work so that price is paid once.

---

## 18. Expansion path

**P2 deeper test/CI analysis** — detailed reports; skipped/quarantined detection; test↔workflow association; coverage-change analysis; flaky detection; cross-commit comparison. **P3 more languages** — TS/JS, Java, C#, more Python frameworks, language-specific test semantics and execution/mutation. **P4 optional agent integrations** — agent-specific declaration commands and convenience adapters; one-click finding transfer; harness integration after completion claims (all optional). **P5 more repositories, CI/CD, and work-management systems** — other code repositories and CI/CD providers (GitLab, Azure DevOps, Bitbucket, Jenkins/CircleCI, etc.) and work-management/requirement sources (Jira, Linear, Markdown specs, Confluence/Notion), so Mode B is no longer GitHub-specific (§5.2). **P6 controlled test generation** — repo-native drafts; separate test branches; test-only PRs run by the project's own CI. **P7 persistent assurance history** — reuse criteria across changes; track evidence across PRs; detect stale evidence; maintain regression obligations; compare agent performance over time. **P8 broader evidence** — manual demonstrations, browser automation, API probes, model-eval results, production incidents, user corrections, observability/trace data. **P9 technical-quality criteria** — extend obligations beyond *behavior* to *how* the change is written: enforce a configurable mix of general best practices, organization/project technical guidelines, and task-specific technical specifications. Targets common agent failure modes developers report — failing to reuse available shared libraries and utilities, overly verbose or sprawling changes, hard-coded values that belong in configuration, needless duplication, and violations of project conventions — surfaced as findings with the same evidence discipline as behavioral criteria.

---

## 19. Strategic framing (brief)

The **Local Completion Check** is the low-friction wedge — usable immediately with no GitHub App, agent change, CI access, requirements platform, or hosted repo access — proving the core capability: `task → obligations → implementation correspondence → test semantics → completion gaps`. The **GitHub Acceptance Review** adds stronger evidence and a team workflow: `Issue → criteria → PR implementation → repo tests → Actions evidence → acceptance recommendation`.

Note on defensibility: the space is exposed — GitHub, CI vendors, and agent makers could each fold in a version of this, and any long-term "structured-relationship" moat is aspirational. The near-term strengths are real regardless: a genuinely useful low-setup tool, measured evidence that it works, and depth on a hard problem (persuasive test evidence, confirmed by execution) that generic tools don't address well. Strategy: win on depth and measured credibility on the wedge, not on assumed lock-in. Begin as an independent completion checker with a validation benchmark and a GitHub acceptance layer — not a requirements platform, agent framework, or universal test runner.
