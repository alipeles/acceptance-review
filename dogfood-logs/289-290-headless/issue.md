# #289 — The instability harness restates the client contract in two places, and both drifted silently

Found during #191, taking the pre-change baseline. `src/acceptance/benchmark/instability.py`.

`benchmark/instability.py` wraps `ModelClient` in an `ObservingClient` and builds
that client itself. It duplicates `ModelClient`'s contract in two places rather
than delegating; #259 broke both:

| site | what it duplicates | what #259 added | symptom |
|---|---|---|---|
| `run_once` | `RunConfig.build_client()`'s parameter set | `embedding_model` | `LLMError: this client has no embedding model configured` at `linking.py:285` |
| `ObservingClient.complete` | `ModelClient.complete`'s signature | `stage_controls` | `TypeError: ObservingClient.complete() got an unexpected keyword argument 'stage_controls'` |

Third instance: `run_once` filtered `client.observed` for
`ObligationDiscrimination`, which can never match. (Since fixed on main by
#316, which reads pair verdicts off the `Review`.)

Nothing caught it because #189's tests all inject a `client_factory`. The fix
that matters is the missing test: run the harness through its **default**
construction over a tiny recorded case, and fail if the pipeline's client gains
a parameter the harness does not pass.

Related: #189, #191, #259, #253, #186.

---

# #290 — Perturbation sensitivity divides a numerator that can count judgements its denominator excludes

`_perturbation_result` computes one blended sensitivity figure from two
populations that are not the same:

```python
watched = len(baseline.obligations) + len(baseline.open_questions)
changed = len({d.subject for d in content})
```

`changed` includes `DEFECT_VERDICT` differences, which are not in `watched`, so
`sensitivity()` can exceed 1.

**Suggested fix:** count the watched population per axis.

- presence and evidence-class axes: `len(obligations) + len(open_questions)`;
- verdict axis: the number of verdict keys present in both snapshots.

Report a sensitivity per axis and never a blended one.

**Suggested acceptance:** a report over two snapshots whose defect verdicts flip
states a sensitivity per axis, each in `[0, 1]`; a test constructs a pair where
the blended figure would exceed 1 and fails if any reported sensitivity does.
`sensitivity()` returning `None` when nothing was watched is preserved per axis.
