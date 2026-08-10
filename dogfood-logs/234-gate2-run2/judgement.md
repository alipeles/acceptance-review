# Judgement — #234 Gate 2, run 2

`NO-MATERIAL-GAPS`. Clean by the gate's definition.

- All 10 obligations **addressed**.
- All 10 **strongly supported** by discriminating tests.
- **No open questions** — none raised at either gate.
- **No recommended tests.**
- Recommended next instruction: none.

The delta section records the three obligations that moved since `2fc8c122`:
two `unsupported -> strongly supported`, one `partially supported -> strongly
supported`, verdict `INCOMPLETE -> NO-MATERIAL-GAPS`. Nothing else changed
rating, which is worth noting given #180 — the run-to-run rating drift seen on
#232 did not recur here.

## Mapping check (DR-164)

A clean verdict is only as good as the mapping behind it, so the transcripts
were inspected rather than trusted. Across the mapping batches, 92 candidate
entries produced 10 non-empty mappings, and the non-empty ones are exactly the
six tests that bear on materialization:

```
test_modification_times_do_not_change_what_is_committed        -> 2 obligations
test_recorded_commits_survive_git_comparing_fewer_status_fields -> 2 obligations
test_each_commit_records_the_fixture_tree_verbatim             -> 4 obligations
test_head_content_wins_when_the_replacement_has_matching_metadata -> 2 obligations
test_materialization_ignores_compiled_python                   -> 2 obligations
test_materialization_is_deterministic                          -> 2 obligations
```

The high proportion of empty `obligation_ids` is the healthy case, not DR-164's
failure mode: the empties are unrelated candidate tests, and every test that
should have mapped did. DR-164's concern is the opposite shape — relevant tests
coming back empty.

## Advisory, carried forward rather than acted on

Four `separable` unrequested changes remain, none a code defect:

1–2. `docs/DEFERRED.md` and `session-state.md` — process files the working
agreement requires updating. Correctly flagged as unrelated to the mandate.

3. Collapsed formatting in `benchmark/fixtures.py` — produced by the repo's own
formatter hook, which re-applies it when reverted. See run 1's judgement.

4. (`in_service`, not separable) `_stage_worktree` itself is flagged as an
implementation detail the obligations do not name. That is a fair reading of a
mandate written in terms of outcomes, and the disposition is right.

## Evidence limitation, as reported

Judgements are static; the application was not independently executed (§3.7).
The fix's own evidence is stronger than that tier implies — each of the three
determinism tests was run against the unfixed code and observed to fail — but
that is my verification, not the tool's.
