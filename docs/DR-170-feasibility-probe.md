# DR-170 — what signals declare a suite hermetic and fast enough

**Issue:** #170 (the open decision on what signals the feasibility probe reads to
decide a project's pytest suite can be run), owned by M8.1 / #42 (the feasibility
probe).
**Resolved:** 2026-09-02, in conversation, before #42 is implemented.
**Status:** resolved.

## What was open

§8.3 (feasibility detection and graceful degradation) states the *policy* — no
network, no secrets, targeted subsets, a short time budget, skip when the probe
fails — but not the **signals** the probe reads. #170 listed five candidates and
chose among none of them: a declared test command versus an inferred one; static
signals such as network-library imports and pytest markers; a dynamic trial run;
the granularity of the verdict; and whether the result is cached.

Both failure directions are invisible in the output, which is the issue's stated
reason for deciding deliberately. Too permissive violates §17's execution-safety
constraint the first time it runs a network-bound test. Too conservative degrades
every project to `static` and the execution tier — the thing that turns
predictions into observations — never fires.

## The evidence this record rests on, and what it cannot support

The one repository available to calibrate against is this one, and it is the easy
case: hermetic, about five minutes, no services, no credentials, no UI, no build
step. §8.3 names the four classes where execution is infeasible — cloud
dependencies, UI-bound behavior, live-service integration tests, excessive
runtime — and this repository exhibits none of them.

So measurements taken here are valid as **counterexamples**, which disprove that
a proposed rule always works, and invalid as **thresholds**, which need cases
where the answer should be no. Every threshold in this record is therefore
configuration with a conservative default, to be calibrated at benchmarking
(Decision 6). Nothing here should be read as a measured cut-off.

## Decision 1 — feasibility is earned by observation and declined by declaration

The relationship between the signal kinds is one-directional:

- **Nothing static or declared may conclude that a test is feasible.** Only a
  completed run in the M8.2 sandbox does, and it says so for that test alone.
- **Static and declared signals may decline, cheaply, before anything runs**, and
  must record why.

This is the same asymmetry as §8.1's evidence ladder, applied one stage earlier:
a higher tier is never reached by predicting. It also matches the costs of being
wrong in each direction. A wrong decline costs a degraded tier, which is
recorded, visible in the report and arguable. A wrong admission costs an
execution-safety incident on someone else's repository, which §17 exists to
prevent and which nothing downstream can undo.

The reason the probe can afford to be an observation at all is DR-171 (the
mutation-targeting decision) Decision 6, which already requires one instrumented
run of the selected tests at head before any injection, and names a feasibility
signal as one of the three things that run buys. The probe reads a run the
execution tier pays for anyway; it does not commission one.

## Decision 2 — the declining signals are the project's own declarations

What may decline a test or a project before any execution:

1. **Pytest markers** naming network, integration, slow, or a configured list of
   synonyms.
2. **A declared test command** — in `pyproject.toml`, `tox.ini`, `noxfile.py` or
   a CI workflow — that names a service, a container orchestration step, or a
   build step the probe cannot reproduce.
3. **A declared dependency set** naming cloud or service SDKs.

In §8.1's vocabulary these are **builder claims**, the weakest tier and "a
starting point, not evidence." That is exactly the right instrument for
declining. The tool's standing objection to builder claims is that they may not
be believed *in the builder's favour*; here the claim is read against the
builder's interest in getting a stronger tier, and the cost of believing a wrong
one is a lower tier rather than an unearned one.

**A declaration cannot admit.** A project asserting its suite is hermetic buys
nothing, and neither does the absence of any of the three signals above. Silence
is not a claim of hermeticity, and treating it as one is how a permissive probe
would be built by accident.

## Decision 3 — the import scan does not gate

Scanning the mapped tests and their fixtures for imports of `requests`, `httpx`,
`socket` or `boto3` is not permitted to decline on its own. It contributes to the
ordering of candidate tests and to the reason recorded when something else
declines, and nothing more.

The counterexample is this repository, which produces both error directions at
once. I verified that no network library is imported at module level anywhere in
`src/acceptance/`, while `litellm` — a network client — is a declared top-level
dependency at `pyproject.toml:12` and is imported lazily inside function bodies
at `llm.py` lines 132, 224, 245, 332 and 333. A scan of declared dependencies
flags the project; a scan of module-level imports in the tests misses the client
entirely.

The deeper reason is that hermeticity here is not a property of the code. It is a
property of `RunConfig.mode`: in replay the suite makes no live call and needs no
API key, in record it does. No reading of imports can see a runtime configuration
value, and lazy imports behind a mode flag are a common way to make a suite
hermetic.

Per the evidence limits above, this shows the scan is unreliable, not that some
static rule could not work. It is demoted rather than forbidden, and Decision 6
leaves its weight configurable.

## Decision 4 — the observing run covers the candidate tests, not the suite

§17's execution-safety line is "targeted subsets only, never full suite," which
settles a scope ambiguity between the two records: DR-171 Decision 6 asks for a
run of the *selected* tests, while the 5m15s figure it cites was measured over
the **whole** suite in the coverage-prefilter experiment (1,623 tests; its
`README.md`, method step 1). At #316's Gate 2 the candidate set was 496 tests of
about 1,311, so 5m15s is an upper bound on the run this decision authorises, not
an estimate of it.

Each test in that run yields its own feasibility outcome: it completed, or it
timed out, errored, or was blocked reaching the network. A test already red at
head is excluded from the verdict with a recorded reason, which DR-171 Decision 6
requires independently.

## Decision 5 — the verdict is per test, under one per-project collection gate

**Per test.** #170's fourth candidate makes the argument — a repository can be
hermetic in one module and not another, and a per-project verdict throws away the
usable half — and on an arbitrary repository the mixed case is the common one.
The data model is already at this grain: `PairVerdict.test_id` in
`review_state.py` is a pytest node id, and its comment records that the digest is
deliberately per test and never per file, citing DR-293 (the record on
over-invalidation from file-level digests).

**One per-project gate above it**, and only one: whether pytest can be invoked
and can collect the candidate node ids at all. This is a few seconds of
`pytest --collect-only` in the sandbox, and it is still an observation rather
than an inference. It fails closed for a missing interpreter, an uninstallable
package or a collection error, and it independently confirms that the node ids
the review is holding still exist at head.

**Per test file is rejected.** Nothing in the data model works at file grain, and
DR-293 already rejected file-level digests for over-invalidation.

## Decision 6 — thresholds are configuration with conservative defaults

The values this record deliberately does not fix, because this repository trips
none of §8.3's four infeasible classes and so cannot calibrate them:

- the per-test and total time budgets;
- which markers decline, as a configurable list with a conservative default;
- how much weight, if any, the import scan of Decision 3 carries in ordering;
- the maximum number of candidate tests the observing run will start.

They are calibrated at benchmarking, against repositories that exhibit the
classes §8.3 names. Until then the defaults are set to decline rather than admit,
per Decision 1's cost asymmetry.

**The interpreter is configuration, not inference.** No file declares which
interpreter a project's tests already pass under — this repository's own
convention that it is `.venv/` lives in `CLAUDE.md`, which is prose. The probe
takes an explicit configuration value with a conventional default and does not
infer one from CI workflows.

## Decision 7 — only the per-project gate is cached

Cached on the head revision and the interpreter. Per-test outcomes are not cached
separately: they fall out of the observing run, which is itself per revision and
already stored in review state.

Nothing more elaborate is worth designing. The run is on the order of CPU-minutes
and zero tokens, against $6.87 of model calls in #316's Gate 2 review, so cache
invalidation here is not where the cost is.

## Consequences

- **#43 (M8.2, the sandbox runner) becomes load-bearing and should land before or
  alongside #42 (M8.1, the feasibility probe)**, inverting the milestone
  numbering. Decision 1 permits execution to proceed on anything the declarations
  did not decline, so the sandbox's network block and time budget are the only
  remaining rail. A weak sandbox turns this record's probe into the too-permissive
  failure #170 warns about.
- **The outcome vocabulary already exists.** DR-171 Decision 8 gives a declined
  attempt `not_attempted` with a required reason, for the same reason `DefectSet`
  requires one on an empty set: "looked and could not" and "did not look" are
  different, and only one is a defect in the tool.
- **A new record holds the per-test feasibility outcome** and the per-project
  gate's result. Additive to review state, so it orphans no recordings.
- **The fallback is unchanged and structural**, per DR-171 Decision 7: a
  repository where the probe declines everything is simply the case where every
  `PairVerdict` stays at `STATIC`. There is no separate degraded mode.
- **No model call is added.** Every signal in this record is a file read, a
  collection step or a test run.
- **What this record does not decide:** any threshold value, per Decision 6.
