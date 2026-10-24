# #398 Gate 2, run 2 — judgement

Run `38a9481d190f816a`, `acceptance check --task current-task.md --base b3261cc
--head c193ac3 --mode record --continue fa81be2b2dc8c191`. Output redirected to
`$TMPDIR` and copied in (70 KB). $0.03, 12 live calls; most pair judgements and
all mutation descriptors replayed from run 1.

**Not clean.** INCOMPLETE: one obligation partially supported, one with no
defect enumerated, two changes rated `separable`. Every remaining finding is
attributed to a tool defect with a drafted filing in `docs/DEFERRED.md`.

## What run 1's fixes changed

- `invalid-api-key-reply-not-shown` is now **strongly supported**, 3 of 3,
  with `test_the_classify_command_warns_then_stops_before_the_first_live_call`
  cited. Run 1's real gap is closed.

## Remaining findings

1. **`startup-warns-missing-model-keys`, still partially supported — tool
   defect, now sharper.** The same surviving defect,
   `startup-warning-omits-embedding-model-when-no-embedding-fn`, 80 pairs put to
   the model. The two new tests included
   `test_a_client_on_the_default_embedding_path_names_the_embedding_models_key`,
   written to run 1's recommendation: a RECORD client, `embedding_model` set,
   no `embedding_fn`, asserting the embedding model's key is named. It fails
   when the check is disabled on that path (I planted it). It was judged not to
   catch the defect, and run 2's recommendation asks again for the same test.
   Three tests now demonstrably catch it. Draft under #183 updated with this.
2. **`env-vars-take-precedence-over-dotenv`, "no plausible defect"** — reused
   from run 1, same reasoning. Draft under #183.
3. **`separable` `pyproject.toml`** (`python-dotenv`) — as run 1. Draft under #185.
4. **`separable` `tests/test_env_and_keys.py`** — as run 1. Comment on #376 drafted.

No further code change addresses any of these: each is the tool misjudging
evidence or scope that is already present.
