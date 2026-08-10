# Judgement — #153 Gate 2, runs 1 and 2

| | run 1 | run 2 |
|---|---|---|
| head | `0d6349d` | `7e6e1ea` |
| verdict | INCOMPLETE | INCOMPLETE |
| obligations | 25 | 25 |
| below strongly supported | 3 | 3 |
| **which 3** | `test-byte-identical-task-text-yields-byte-identical-review-state`, `deterministic-review-state`, `no-live-model-calls-in-tests` | `test-scope-exclusion-yields-code-only`, `test-code-only-obligation-does-not-incomplete-verdict`, `no-test-recommended-for-code-evidence-only` |

**Gate 2 is NOT clean.** Not a judgement call: the gate requires every
obligation strongly supported, and 3 are not.

## The feature itself works

All 7 exclusions yielded, in absence form, none inverted, and rendered as the
acceptance describes:

```
19. The change does not alter which open questions are raised or what they cite.
     code evidence: addressed
       examined 53 changes across 23 files; none breaches this boundary
     test evidence: not applicable — confirmed by code evidence alone
```

## Finding 1 — a real defect in this change, caught by the run (fixed)

Run 1 rendered obligations 17, 18 and 22 as a **listing of hunks** rather than
the completeness claim. The classify prompt tells the model to leave `diff_refs`
empty for a respected boundary; it returned them anyway on 3 of 7. Under a
respected boundary a cited hunk reads as evidence *for* the obligation, which is
what the acceptance forbids.

Fixed in `7e6e1ea` by dropping the refs in code for `CODE_ONLY` + `addressed`.
Third time in this task the same move was needed. Every existing test fed a
compliant response, so none could have caught it; the new one feeds a
non-compliant response and was defect-injected.

## Finding 2 — a real gap, raised by the tool's own recommendation (fixed)

The recommendation for `test-scope-exclusion-yields-code-only` asked for
*"assert the ordinary non-exclusion requirement is not marked CODE_ONLY"*.

That was correct and I had missed it. `test_every_scope_exclusion_yields_a_code_
evidence_only_obligation` asserts exclusions **are** code-only, which an
implementation marking **every** obligation code-only would also satisfy — and
that implementation would silently exempt the whole mandate from test evidence.
`test_only_exclusions_are_on_the_code_evidence_only_axis` closes it, and defect
injection confirms it is the only test in 952 that catches that variant.

## Finding 3 — the gate does not converge (tool defect, #180)

The two runs name **three different obligations each**, with no overlap, for a
change consisting of one code fix and two added tests. Run 1's three were all
determinism/no-live-call obligations; run 2's three were all code-only-axis
obligations. None of the six is an unmet requirement — each names a test that
exists and is asserted on.

This reproduces exactly what `dogfood-logs/232-gate2-run2/judgement.md` recorded
and #180 tracks: the evidence rating is unstable across runs over near-identical
input, so "3 below strongly supported" carries no information about which
obligations are actually weak. Recorded against **#180** rather than acted on.

## Disposition

Findings 1 and 2 addressed in code. Finding 3 attributed to #180, with this run
pair as fresh evidence — the queued comment is in `docs/DEFERRED.md`.

The gate is re-armed by both fixes and has not been re-run at `HEAD`. Given
finding 3, another run is expected to name a third disjoint set rather than come
back clean, which is the thing to decide with the human rather than iterate on.
