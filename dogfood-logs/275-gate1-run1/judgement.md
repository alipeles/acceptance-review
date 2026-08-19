# Judgement — #275, Gate 1, run 1

`decompose` over `current-task.md` for #275, at `5c5d9de` (branch
`275-recommendation-omission`, tree clean apart from `session-state/275.md`).
Recorded live, then replayed byte-identically for the JSON inspection.

**Header:** `Requirements: 33   with obligations: 32   deliberately none: 1`
**Obligations:** 31. **Open questions: 0.**

## Verdict on the breakdown — accurate, and I would defend it

- 33 requirements = 1 `## Task` + 13 Constraints + 6 Scope exclusions + 13
  Completion expectations. Every one is dispositioned.
- The single deliberate decline is `completion-01` ("Implementation"), a bare
  section marker. Correct.
- **No invented obligations.** Every obligation traces to text I wrote.
- **None of the real ones missing.** Each of the 13 constraints and 12 checkable
  completion expectations is represented.
- **No open questions**, so the Gate 1 triage table has no entries.
- `required_evidence` (#266) is sane: 19 `code_and_tests`, 6 `tests_only` (the
  six `test_demand` obligations — a test asserting something is owed a test, not
  code), 6 `code_only` (the six scope exclusions). None `neither`, so nothing is
  routed to non-code review.

## Negative findings — three, all attributed to already-filed tool defects

### 1. One requirement yields two obligations stating the same thing — NEW, filing drafted

`constraint-07` ("The report states, for a criterion whose prescription was not
obtained, that no prescription was produced for it.") produced **two**
obligations:

| id | type | description |
|---|---|---|
| `report-no-prescription-produced` | functional | "State in the report, for a criterion whose prescription was not obtained, that no prescription was produced for it." |
| `report-says-no-prescription-produced` | explanation_observability | "The report states, for a criterion whose prescription was not obtained, that no prescription was produced for it." |

The second is the requirement text verbatim; the first is the same sentence in
the imperative. `constraint-12` ("A response naming the same criterion more than
once is rejected.") did the same thing — `reject-duplicate-criterion-names`
(imperative) and `duplicate-criterion-rejected` (declarative), both typed
`error_handling` — and that pair was **not** flagged as unreconciled anywhere.

This is not the twin-across-sections shape of #245/#273: one requirement, one
property, two obligations, differing only in voice. Not attributable to my
wording — both requirements state a single property in one sentence, in the same
shape as `constraint-08`, which produced exactly one.

**Disposition:** filing drafted against #181 (see `docs/DEFERRED.md`).

### 2. A cluster of three genuine duplicates merged none of them — #242

The tool flagged it itself:

```
Unreconciled linking answers: answers contradict each other: these obligations are
linked transitively but at least one pair among them was denied, so none of them
were merged
  affected: report-states-no-prescription-produced-for-omitted-criterion,
            report-no-prescription-produced, report-says-no-prescription-produced
```

Same message and same mechanism as #242 (`_confirmed_clusters`, all-or-nothing
on an inconsistent cluster) — but with one fact #242's instance does not have.
There, a **spurious third member** dragged two genuine duplicates into an
inconsistent cluster. Here **all three members are genuine duplicates of one
another**, so no false-positive link is available to blame: some pair among three
synonymous obligations was denied. The blocked merge is caused by a false
*negative* on a true pair, which is a different input to the same policy.

**Disposition:** comment drafted on #242.

### 3. Nine constraint/completion twins unmerged; six merges refused, three made — #273

Merged correctly: `constraint-05`+`completion-05`, `constraint-08`+`completion-08`,
`task-01`+`completion-04`. Unmerged twins: constraints 01, 02, 03, 09, 10, 11, 12,
13 against their completion counterparts, plus the trio above.

The correlation worth reporting: **every completion obligation typed `test_demand`
(6 of 6) is unmerged**, while completion obligations typed anything else merged 3
of 6. All three merges are with a non-`test_demand` twin. One run, so a
correlation and not a finding — but it is a cheap thing for #273 to check, and it
would explain "inconsistent rather than absent" mechanically.

**Disposition:** comment drafted on #273.

### Noted, not counted against the breakdown

- `no-omission-cause-analysis` (from `exclusion-03`) is typed `human_review` —
  the #196 shape. It carries `required_evidence: code_only`, and `derive_verdict`
  reads `required_evidence`, not the type, so it does **not** route the review to
  `needs_non_code_review` and is not a Gate 2 hazard. Recorded as a fresh #196
  instance, no new filing.
- `required_evidence` is invisible in the text output — I had to read `--json` to
  audit it. That is #276, already filed.

## Environment defect found on the first run

The first `decompose` died before any model call completed:

```
litellm.exceptions.APIConnectionError: `Message` is not fully defined; you should
define all referenced types, then call `Message.model_rebuild()`
```

This worktree's fresh `.venv` had resolved **litellm 1.97.0** against
**pydantic 2.13.4**; the other worktrees hold 1.96.2. `pyproject.toml` floors it
at `litellm>=1.50` with no ceiling, so any new environment picks up the break.
Pinning to 1.96.2 in this venv fixed it with no other change. Replay-mode runs
are unaffected — this only bites recording, which is exactly what a new worktree
must do first. Filing drafted against #184.
