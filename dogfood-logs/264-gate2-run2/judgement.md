# Judgement — #264 Gate 2, run 2

**Command:** `.venv/bin/acceptance check --task current-task.md --base c652ab4 --head 23cf2e7 --mode record`
**Verdict:** `INCOMPLETE` — **not clean.**

## The three findings from run 1 are fixed, and three different ones appeared

The tool's own comparison section says it:

```
  fixed:
    - The command-line interface surfaces the breakdown.
        test evidence: unsupported -> strongly supported
    - The breakdown appears in no review state.
        test evidence: unsupported -> strongly supported
    - The breakdown appears in no rendered report.
        test evidence: unsupported -> strongly supported
  moved:
    - The change does not attribute cost to anything finer than the stage that issued the call.
        test evidence: strongly supported -> unsupported
    - A run's cost is attributable to the stage that incurred it.
        test evidence: strongly supported -> unsupported
    - Every model call the review pipeline issues records which stage issued it, ...
        test evidence: strongly supported -> unsupported
```

## This is #251, in the cleanest controlled pair we have

The three that fell are attributed to a **tool defect**, not to the delivery.
What separates run 1 from run 2:

- `23cf2e7` changed **two files**: `tests/support.py` and
  `tests/test_stage_attribution.py`. `git show --stat` confirms it.
- **No source file changed.** Not one line under `src/`.
- **`tests/test_usage.py` is byte-identical between the two heads.**

And yet, in run 1 those three obligations cited tests *from that byte-identical
file* and were rated `strongly supported`:

| obligation | cited in run 1 | cited in run 2 |
|---|---|---|
| `no-finer-than-stage-cost-attribution` | `test_usage.py::test_each_stage_is_accounted_for_separately_and_in_a_stable_order` | (no mapped test) |
| `stage-attributed-run-cost` | `test_usage.py::test_each_stage_is_accounted_for_separately_and_in_a_stable_order` | (no mapped test) |
| `model-call-stage-usage-cost-cache-recording` | `test_usage.py::test_usage_details_are_read_from_a_mapping_too` | (no mapped test) |

The tests still exist, unchanged, in a file that did not change. The obligation
text did not change. The code they cover did not change. The only difference in
the diff under review is **additional tests elsewhere** — which is exactly the
#251 shape: adding tests makes the report worse.

`session-state/264.md` warned about this before any code was written, and the
instruction there was followed: **the rating was not chased by writing more
tests.** Doing so is what made #269's run 5 worse.

### The likely mechanism, offered as a hypothesis rather than a finding

The usage footer this task added happens to instrument the stage that failed.
Mapping issued **14 live calls in run 1** and **15 calls in run 2, of which only
3 were live and 12 replayed**. So a new test file did not merely add work — it
**moved partition boundaries**, and the three partitions that were re-asked came
back with different answers from the ones the recording held. That is DR-164
territory (mapping-stage request partitioning), and it would explain why the
losses cluster rather than scatter.

Verified: the call counts, the byte-identical file, the lost citations.
**Not** verified: that the re-asked partitions are the ones carrying the lost
mappings. Confirming that needs the mapping transcripts read side by side.

## Everything else in the run

- All 28 obligations **addressed** on code evidence.
- 27 of 28 requirements yielded obligations; `[completion-01] Implementation`
  deliberately declined as a section marker. Correct.
- **No open questions.**
- **One unrequested change**, dispositioned `in_service` — the CLI footer itself.
  Its rationale is questionable (it says the obligations "do not call for
  changing these commands' stderr output", while `cli-surfaces-breakdown`
  requires exactly that the CLI surface the breakdown), but `in_service` is the
  benign disposition and nothing is being hidden by it.

## The footer, on an incremental re-run

```
  test-to-obligation mapping    15 (3 live / 12 replayed)  72,517  10,382  0.0%  $0.0172  $0.1011
  this run spent $0.0875 on 7 live call(s); the evidence cost $0.1950 to record
  (18 call(s) replayed at no cost to this run)
```

The mapping row is the deliverable working: this run paid $0.0172 for evidence
that cost $0.1011 to record. Before this change, both numbers were unknowable and
a reader would have had no way to tell them apart.

## Disposition

**Gate 2 not clean.** Three outstanding findings, all three attributed to a tool
defect (#251, with a mapping-stability component under #182). A filing is drafted
in `docs/DEFERRED.md` as a comment on #251 — the attribution is recorded before
moving forward, as the rules at both gates require.

**The human decides whether to land on this.** Recent practice (#271, followed by
#269) permits it when every outstanding finding is attributable to the tool rather
than the delivery, stated explicitly in the PR body. That condition holds here,
but the decision is not the session's to make.
