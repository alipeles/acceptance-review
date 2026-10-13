# Probe: GPT-5.4 Mini token probabilities

Deliverable 1 of #379 (part 1 of the Jev experiment: would this test fail
under this defect). Run 2026-10-13, live, on one toy question with no BugsInPy
content.

## Result

**Approach D can run, using a one-word yes/no answer.** With
`reasoning_effort="none"`, `logprobs=True` and `top_logprobs=5`, GPT-5.4 Mini
returns the probability of both answers at the answer token:

```
'yes'   -0.0789  top=[('yes', -0.0789), ('no', -2.5789)]
```

That is p(yes) ≈ 0.924 and p(no) ≈ 0.076. A second run gave the same numbers.
Only two alternatives came back although five were asked for. The issue
comment on #371 had reported server errors when asking for two or more
alternatives; none occurred here.

**The structured JSON answer (`{"fails": bool}`) cannot be used for approach
D.** At the `true` token, the only alternative listed was `' true'` (the same
answer with a leading space) on one run, and nothing on the other. `false`
never appeared, so the probability of the other answer cannot be read from
it. Approach D therefore uses the one-word answer, not the schema-constrained
shape the harness uses.

## Other observations

- Through LiteLLM (`probe_mini_logprobs.py`), `max_tokens=1` returned an empty
  answer and no probabilities. Calling the OpenAI SDK directly with
  `max_completion_tokens=4` works, so the experiment's recorder calls the SDK
  directly.
- The toy answer itself was wrong: `parse('1,2') is not None` still passes
  when the split character changes, yet Mini said "yes" at 0.92. One case
  proves nothing, but it is the kind of confident wrong answer approach C's
  threshold has to catch.

## Jev

Run 2026-10-13 with `probe_jev.py`: the same toy question as one yes/no
("noul") question, test source and defect as a structured `state`. The request
shape is from https://docs.typesafe.ai/api.md (`questions` is a map keyed by
question id; the answer is `answers[id].noul`, the probability of yes).

```
status: 200  elapsed_ms: 585
model: jev-1.13.0   answers.fails.noul: 0.75   usage: 366 input, 20 output tokens
```

Jev leans the same wrong way as Mini but less confidently (0.75 against 0.92).

**`api.typesafe.ai` is not reachable from the sandbox.** The call timed out
waiting for the sandbox's network proxy, twice, while OpenAI calls through the
same proxy worked. It succeeded with the sandbox off. Jev runs need the host
allowed in the sandbox settings, or they each stop for a permission prompt.

## Files

- `probe_mini_logprobs.py`: first pass, through LiteLLM.
- `probe_mini_logprobs_raw.py`: second pass, OpenAI SDK directly.
- `probe-output.txt`: output of the second pass.
- `probe_jev.py`: the Jev call.
- `keys.py`: reads a provider key from the environment or the worktree's env
  file, never printing it.
