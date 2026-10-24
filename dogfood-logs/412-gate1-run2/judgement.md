# 412 Gate 1, run 2 — judgement

Run `6bc7ccd4832f4975`, continuing run 1 (`7744c16d7cd1f3ed`), on main at 5f841e0.
Only the first two requirements were reworded (see run 1's judgement); 8 carried,
2 revised.

13 obligations plus 5 from the scope exclusions, 0 open questions. Accepted as
accurate: no invented obligation, none missing.

## Notes

- `provenance-records-neither-applied` reads "records that Claude applied
  neither" — "neither" refers back to the temperature and seed named in the
  requirement, not in the obligation. Minor, and an instance of open #330 (an
  obligation description that refers outside itself is emitted with no
  diagnostic). No new filing.
- `config-only-model-selection` is `code_only`. A test could check that no module
  other than `config.py` names a model, so this is arguable; I accept it, since
  the location is visible in the diff.
- The run-1 `code_only` misclassification (#374) did not recur here.
