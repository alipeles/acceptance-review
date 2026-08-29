# Judgement — #317, Gate 2, run 1

Run `30820e1364fc6d09`, `--mode record`, base `20e3fb1` head `d925986`.
Verdict: **INCOMPLETE**. Gate 2's "clean or stop" rule is suspended while
#312's sub-issues are in flight, so this is one run, triaged and moved past.

**The run cost nothing.** Every one of its 75 calls replayed: the decompose
corpus had just been rebuilt by the prompt-suite re-record, so `--mode record`
found what it needed on disk. `$0.9229` is what the evidence cost to record, not
what this run spent.

## What it got right, and is worth keeping

- **30 of 30 requirements yielded obligations.** No requirement was lost, and
  none was disposed `no_obligation` by mistake.
- **The summary step worked on this mandate.** `task-01` yielded one obligation
  — *"Account for the mandate's opening summary after the obligations produced
  from the rest of the mandate…"* — and nothing that restates a Constraints
  bullet. That is the defect #317 exists to fix, not reproducing.
- **The per-stage model reached the report.** The usage footer shows
  `decompose-summary` on `openai/gpt-5.4` and every other stage on
  `openai/gpt-5.4-mini`, which is the acceptance item *"a completed run says
  which model each step used"* demonstrated on a real run rather than in a test.
- **30 decompose calls for 30 requirements**, one each, visible in the footer.

## The one finding that was real, and was fixed

**`requirement/summary.py` had no tests of its own.** Three completion
expectations of the mandate demand them by name — every stretch decided exactly
once and a substring of the summary (`completion-05`), a covered stretch
yielding no obligation (`completion-06`), an uncovered stretch yielding one
(`completion-07`) — and all three came back `indeterminate` with `(no mapped
test)`. The module had been validated only through its callers.

Fixed in `tests/requirement/test_summary_pass.py`, 13 tests. Each was checked by
injecting the defect it names and confirming it fails:

| defect injected | tests that failed |
|---|---|
| drop the decided-exactly-once check | 3 |
| drop the guard on an uncovered span yielding nothing | 1 |
| take the span obligation's quotation from the answer instead of the mandate | 1 |
| author obligations for covered spans too | 4 |

The first attempt at the quotation injection was a **no-op** — the patch string
had the wrong indentation, so nothing changed and the test passed for the wrong
reason. Caught, redone, and the table above is the corrected result.

## Findings attributed to known tool defects — nothing new to file

- **Seven obligations `indeterminate` with `(no mapped test)`**, including
  `completion-02` and `completion-03`, which are covered by
  `test_a_task_file_of_n_requirements_produces_one_call_per_requirement` and
  `test_a_call_is_offered_only_its_own_requirements_quotations` respectively.
  The mapping stage did not link them. That is the open mapping-recall defect
  under umbrella #182; the tests exist and were verified by hand.
- **One recommendation `NOT OBTAINED`** — *"the recommendation stage was given 8
  criteria and returned 7"*. The known omission defect; #279 removed the
  whole-review abort, and the residual omission is recorded, not new.
- **13 unrequested changes**, ten `in_service`, two `separable`, one `risky`.
  Every one names real work this change did — the `stage_models` field, the
  `build_request` signature, the `DECOMPOSE_STAGE_LOGIC_VERSION` bump, the
  singular `requirement_disposition`. All are required by the mandate's own
  constraints and are reported at the right severity; the `risky` one is the
  response-schema change, which is a fair thing to flag.
- **A zero-byte `output.log` on the first invocation**, exit 0, with the
  identical command producing 49 KB after `rm -f`. The defect CLAUDE.md already
  documents under *Dogfooding*; reproduced, not diagnosed.

## Not clean, and why that is where it stops

Per CLAUDE.md's suspension of the clean-or-stop rule: the run was made once, the
one thing it genuinely identified was fixed, nothing genuinely new was found to
file, and the rest is evidence of already-tracked defects. No finding was
attributed to a tool defect without being recorded here.
