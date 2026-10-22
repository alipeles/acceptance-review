# #398 Gate 2, run 1 — judgement

Run `fa81be2b2dc8c191`, `acceptance check --task current-task.md --base b3261cc
--head 34e74cb --mode record --continue 8ec089ff76154502`. Output redirected to
`$TMPDIR` and copied in (69 KB). $0.38, 163 live calls.

**Not clean.** INCOMPLETE: two obligations partially supported, one with no
defect enumerated, two changes rated `separable`.

## Findings

1. **`invalid-api-key-reply-not-shown`, partially supported — real gap.** The
   surviving defect `startup-warning-not-issued-for-classify-client`: no test
   ran `classify`, so deleting its `warn_missing_keys` call broke nothing (the
   run's unverified edit did exactly that and survived). **Addressed:** added
   `test_the_classify_command_warns_then_stops_before_the_first_live_call`;
   I verified it fails with that call removed.

2. **`startup-warns-missing-model-keys`, partially supported — tool defect.**
   The surviving defect `startup-warning-omits-embedding-model-when-no-embedding-fn`
   says the warning could skip the embedding model on the default embedding
   path. Two existing tests already catch it: with the embedding check turned
   off on that path, `test_record_mode_names_every_configured_models_missing_key`
   and `test_the_cli_warns_at_startup_then_stops_before_the_first_live_call`
   both fail (I planted it and ran them). All 78 pairs went to the model and
   none was judged to catch it. The run's own edit for it
   (`embedding_fn is None and embedding_model is not None`) changes no
   behaviour, so its survival is correctly not counted. Addressed anyway with
   the recommended test,
   `test_a_client_on_the_default_embedding_path_names_the_embedding_models_key`,
   and attributed: filing drafted under #183. This obligation also lacks "in
   record mode" (#399); the warning was built for record mode only, and no
   finding here turned on that.

3. **`env-vars-take-precedence-over-dotenv`, "no plausible defect" — tool
   defect.** The enumerator argued that `override=False` makes the property
   hold, so nothing could fail it. Changing that one argument to `True` breaks
   it, and `test_a_variable_already_set_wins_over_the_env_file` catches that (I
   planted it). The enumerator described the code as delivered rather than ways
   it could go wrong. Filing drafted under #183.

4. **`separable`: `tests/test_env_and_keys.py`** — the file every obligation
   cites as its evidence. Known defect #376 (a test file cited as evidence is
   reported as a separable unrequested change). Comment drafted.

5. **`separable`: the `python-dotenv` dependency in `pyproject.toml`** — the
   CLI now imports `dotenv` directly, so declaring it is what makes an install
   correct; relying on litellm to pull it in is an accident of litellm's own
   dependencies. Tool defect, filing drafted under #185. Close to #375 (a
   backward-compatible parameter that delivers an obligation is rated a risky
   unrequested change), but that is a parameter and `risky`; this is packaging
   metadata and `separable`.

`in_service` changes 2–5 (the new helpers, `MissingKeyError`, the `key_check`
parameter) are in service of the mandate and need no action.
