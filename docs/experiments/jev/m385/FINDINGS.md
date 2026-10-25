# Jev, then the model, as the pipeline's pair judge: measured (#385)

#385 wires DR-379's rule into the pipeline: Jev decides a (defect, test) pair
on its own at 0.34 or more ("fails") and at 0.24 or less ("survives"), and the
run's default model (Claude Sonnet 5.5) answers yes or no in between. Three
things differ from what DR-379 measured: the defect is described with its
lines marked rather than applied as an edit, the fallback is Sonnet rather than
GPT-5.4 Mini, and a fallback with no usable answer leaves the pair unanswered.
These are the two measurements #385's Acceptance asks for.

## Held-out mutant cases (2026-10-25)

`score_pipeline_judge.py` runs the pipeline's own judge
(`pair_mapping._decide_all` over `jev_context.build_context`) on DR-379's 92
held-out cases from #372's BugsInPy mutant labels. Results in
`heldout-pipeline.json` (ids and numbers only).

| | accuracy (95% range) | precision on "fails" | cost per judgement |
|---|---|---|---|
| DR-379, Jev then Mini, edit shown | 85.9% (77–92%) | 0.845 | $0.0001 |
| **#385, Jev then Sonnet, defect described** | **87.0% (78.6–92.4%)** | **0.848** | **$0.00023** |

Jev decided 90 cases alone; Sonnet decided 2; none were left unanswered. Cost
per judgement is higher than DR-379's because each Sonnet call costs about
$0.0064 against Mini's fraction of a cent; Jev's own share is $0.000096.

Meets #385's bar ("at least as well as the experiment's held-out figure,
within its range"). The ranges overlap almost entirely, so this says the
described-defect form lost nothing measurable, not that it is better.

**Defect found by this run.** Two mutants of youtube-dl bug 9 read identically
once described, so they sent Jev the same request concurrently. Both missed the
store, both went live (0.74 and 0.71), and the recording kept the last answer,
so the replay disagreed with the run that recorded it. Fixed in the judge
(each distinct question asked once); the general race in `llm.py`'s recording
is queued as a filing under #184. Two offline replays after the fix are
byte-identical.

## A priced real review (2026-10-25)

`acceptance check --mode record` over #413's change (the task file and
revisions of `dogfood-logs/413-gate2-run4`), everything live. Saved in
`priced-review/`.

- **Pairs:** 3,700 formed over 25 enumerated defects; 2,316 asked about, 1,384
  skipped once their defect was covered (#348's early stop), none unanswered.
- **Who decided:** Jev 2,285 (98.7%), Sonnet 31 (1.3%).
- **Cost of judging:** Jev $0.2982 (2,316 calls, 7.1M input tokens); the pair
  stage's model row $0.3539 (31 Sonnet calls plus the ranking embeddings).
  About $0.65 in all, $0.00028 per judgement.
- **Whole review:** $2.12 on 2,419 live calls.
- **Time:** Jev's calls took 610 s of the run.

For scale only: #413's first Gate 2 run (`dogfood-logs/413-gate2-run1`) spent
$1.54 and 690 s on the old batched judge. That run enumerated different
defects, so the two are not like-for-like.
