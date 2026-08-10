# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed, so it survives a context reset or a machine change — but still a
scratch record, not a plan. **The GitHub issue stays authoritative** (#168).
Clear it out when the task lands rather than letting it accrete.

*Last updated: 2026-08-09*

---

## Task in flight — the decomposition-prompt bundle: #232 + #219 + #230

Branch `232-decomposition-prompt-shaping`, off `eb182de`. Nothing pushed.

**Bundled on an explicit human call.** All three are derivation-prompt shaping
defects in `src/acceptance/requirement/obligations.py` — prompt text only, no new
stage, no schema change, one transcript re-record. #219 and #230 are inseparable:
#219 wants exclusions to yield preservation obligations instead of being declined,
#230 says the preservation obligations that *were* produced are the harm. Fixing
either alone picks the other's answer by accident.

**#205 and #206 were deliberately excluded** — each is a new pipeline stage with a
live-run acceptance item, and would not reach Gate 2 in one session. **#231** was
excluded as architectural (reversing DR-204's whole-registry prompt, or deriving
ids from the requirement).

## Gate 1 — done, four runs, not clean and cannot be

`dogfood-logs/232-gate1-run{1,2,3,4}/`. Run 4 is the task file to implement
against. **No open questions in any run**, so the three-case triage is empty.

Runs 2–4 were sanctioned rewrites of `current-task.md`, each re-arming the gate.
What they fixed was mine; what remains is the tool's, and all of it is #232 /
#219 / #230 — the bundle's own subject. **Human gave explicit go-ahead to code on
that basis.** Gate 2 is the gate that must come back clean.

Read `dogfood-logs/232-gate1-run4/judgement.md` before implementing — it states
what the fix must achieve.

## The three findings that shape the implementation

1. **#232 is unstable within a single run, not just across task files.** Run 4:
   five Completion expectations of one shape, framing kept for `completion-02`
   and `-03` ("Produce a test that asserts …"), dropped for `-04`, `-05`, `-06`
   — and those three then merged with their Constraint twin. Run 1 was 0 kept / 5
   dropped. So the fix's test must assert the framing is kept for **every**
   sentence of the shape, not that it is usually kept.
2. **A test asserting "these two obligations did not merge" is worthless.** Run 2
   showed four merges absent only because an 8-obligation transitive clique was
   contradicted, so #144's clique rule merged nothing. It would pass with the fix
   reverted. Assert that the **derived obligation demands a test**.
3. **Scope exclusions invert, they do not merely differ.** Four of six yield
   obligations to *do the excluded work* — `exclusion-05` (#231) →
   "Keep obligation identifiers stable across task-file edits". Stable across all
   four runs. This is the sharpened #230.

## Design call to make, recommended not yet decided

#219 leaves the branch open: an exclusion *yields a preservation obligation* or
*declines with a reason stating no preservable property*. **Recommended: decline,
uniformly**, with the reason constrained to naming what is out of scope. It
satisfies both of #230's clauses and does not depend on #148 landing. Cost —
nothing checks the exclusion was not violated — stays tracked on #133/#148/#214;
an obligation no test can support is worse, because it blocks clean verdicts.

## Filed this session

- **#234** — `test_materialization_is_deterministic` flaky in CI, child of #184.
- **Comment on #230** — exclusions invert into obligations to do the excluded
  work; proposed acceptance clause added.
- **Comment on #212** — the problem statement derived an obligation contradicting
  `constraint-01`; notes that nothing detects a contradictory obligation pair.

## Do not rediscover

- **Gate 1 cannot be clean for this task by construction.** Every Completion
  expectation in this repo's convention uses the framing #232 drops.
- **#153 looks stale** — open as "decompose never learns the exclusion section
  exists", but #219's body says #202 fixed exactly that. Candidate to close.
- **The whole registry is in every derivation prompt** (DR-204). Any task-file
  edit re-derives everything — that is why `exclusion-01`/`-02` took three
  different types across four runs on byte-identical text. #231.
- **Obligation ids are minted per response, not stable across runs.**
- **`decompose --mode record` writes nothing to stdout when redirected.** Record
  once, then re-run in replay to capture.
- **Python here is 3.10**; repo is `alipeles/acceptance-review`.

## Queue — `docs/DEFERRED.md`

Empty of open items. All three entries from this session are filed.

## Known open

**#210**, **#180**, **#193**, **#153**, **#191**, **#196**, **#178**, **#214**,
**#129**, **#223**, **#224**, **#173**, **#225**, **#227**, **#228**, **#212**,
**#230**, **#231**, **#232**, **#219**, **#234**.
