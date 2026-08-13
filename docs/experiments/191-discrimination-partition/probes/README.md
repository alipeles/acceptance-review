# Probes — the method behind #191's findings

The conclusions are in `../README.md` and `session-state/191.md`. This directory
is the *method*, kept for the reason `docs/experiments/obligation-dedup/` exists:
DR-259's analysis lived entirely in a session scratchpad, the conclusion was
recorded and the method was not, and the next experiment rebuilt the parsing that
had already gone wrong twice.

All of these read `.acceptance/cache/transcripts/`. Two issue live calls and say
so in their docstring; the rest are free. Run them from anywhere — paths are
derived from the file's own location.

## What each one answers

| script | question | live calls |
|---|---|---|
| `cache_probe.py` | how much of a verdict request is the invariant prefix, and what does the stage cost? | no |
| `live_cache_probe.py` | does the provider actually cache that prefix? | **yes**, 3 |
| `isolate_cache_miss.py` | if it does not, is the per-call constrained schema the reason? | **yes**, 6 |
| `dump_and_repeat.py` | what does a real verdict request look like, and does an identical one get an identical answer? | `--live`, 3 |
| `mapping_churn_by_seed.py` | how much does the mapped test set move between two runs differing only by seed? | no |
| `verify_wiring_discriminates.py` | would this test actually fail if the behaviour were removed? | no |

## Traps, each of which cost something

**Transcripts do not record cached tokens.** `_extract_usage` keeps
`prompt_tokens`, `completion_tokens`, `total_tokens` and `cost_usd`, and drops
`prompt_tokens_details.cached_tokens` — the only field that says whether the
prompt cache is working. That is why `live_cache_probe.py` exists and has to
spend money. Queued as a defect in `docs/DEFERRED.md`.

**A cold cache reads exactly like a broken one.** The first run of
`live_cache_probe.py` reported `cached=0` on all three calls and was read as
"caching does not engage". It was the first traffic to touch that prefix. Re-run
it and it reports 84–93%. **Always issue a warm-up call, or run it twice, before
concluding anything from a zero.**

**Mapping batches shift when a test is added, so you cannot separate a perturbed
run from its baseline by looking for the added test.** `partition()` sorts by
`test_id` and chunks, so inserting one test moves every test after it across
batch boundaries. Only the batch containing the new test mentions it by name;
several others differ anyway. An earlier version of the churn analysis filtered
on the marker string and produced a spectacular, entirely false result — every
criterion appearing to lose all its mapped tests. **Separate runs by seed
instead**, and use 1001/1002, because seed 1000 is shared with the perturbation
run.

**Criterion ids are re-minted between runs, so id-keyed set comparison
overstates churn.** `no-speculative-writing` in one run is
`nothing-written-speculatively` in the next with an identical description. A raw
string diff called the decomposition "45% different"; the harness's own semantic
alignment reports **zero** obligation content differences. Compare descriptions,
and prefer `benchmark/alignment.py::align_obligations` over anything hand-rolled.

**An identical request never reaches a model.** The transcript store is keyed on
the whole request, so "same prompt, different answer" is structurally invisible
from inside a run — it replays instead. Testing it requires issuing the call
directly, which is what `dump_and_repeat.py --live` does.

**A dumped prompt embeds the repo's own diff.** `dump_and_repeat.py` writes to
`.acceptance/`, which is gitignored, deliberately: it is a request dump, and the
no-committed-transcripts rule applies to it.
