# Jev experiment, part 1: would this test fail under this defect (M5.2)

Findings for #379, the first part of #371 (whether TypeSafe's Jev can take over
the checker's fixed-label judgements). The verdict is in
`docs/DR-379-jev-m5.2.md`. Scripts and per-run JSON are in `m52/`; every figure
below comes from a file named next to it. Only aggregates and case ids are
committed.

## The answer

The shipped judge is the weak link, not the model that could replace it. On
the held-out cases, GPT-5.4 Mini as the shipped judge calls it was right 66% of
the time. Jev alone was right 80%. No-tools Opus 5.5 was right 95%. Jev first,
with Opus deciding the cases Jev is unsure of, was right 93.5% at about half of
Opus's cost.

## Cases

The 231 BugsInPy operator mutants from #372, each run against a real test and
labelled killed or survived. Split 60/40 by label from seed 379 before anything
ran (`m52/split.json`): 139 tuning, 92 held out. Two tuning cases cannot have
their mutated code rebuilt, so 137 tuning cases are usable. The held-out set has
53 killed and 39 survived. 136 of the 231 cases come from youtube-dl.

## Held-out results

Every rule was fitted on the tuning cases and committed (`m52/frozen.json`,
`437229f`) before the held-out set was scored once (`m52/score_heldout.py`,
`m52/heldout.json`). Ranges are 95% Wilson intervals.

| design | accuracy | precision on "fails" | recall on "fails" | precision on "survives" | recall on "survives" | cost per case | sent to Opus |
|---|---|---|---|---|---|---|---|
| shipped judge (Mini, batched) | 66.3% (56–75) | 0.789 (0.64–0.89) | 0.566 | 0.574 | 0.795 | not measured | — |
| Jev alone, at 0.5 | 80.4% (71–87) | 0.857 | 0.792 | 0.744 | 0.821 | $0.0001 | — |
| Opus alone, no tools | 94.6% (88–98) | 0.929 (0.83–0.97) | 0.981 | 0.972 | 0.897 | $0.050 | 100% |
| Jev then Opus, aiming 97.8% | 93.5% (87–97) | 0.912 (0.81–0.96) | 0.981 | 0.971 | 0.872 | $0.027 | 52% |
| Jev then Opus, aiming 95% | 90.2% (82–95) | 0.867 (0.76–0.93) | 0.981 | 0.969 | 0.795 | $0.008 | 14% |

Precision on "fails" is precision on the costly wrong answer: a false "this test
catches the defect" makes a weak test look strong.

"Jev then Opus" uses the targeted-context prompt (below). Jev's probability that
the test fails decides alone at 0.80 or more ("fails") and at 0.14 or less
("survives"); the rest go to Opus. The 95% variant also says "survives" when
Jev thinks the edited line probably never runs. The same two aims using a
prompt with only the code around the edit scored 93.5% at $0.029 and $0.024.

Of the 6 cases the main Jev-then-Opus design got wrong, Opus alone also got 5
wrong. Jev's own confident calls added one error.

The tuning figures were higher for every design (Opus alone 97.8%, Jev then
Opus 97.8% by construction). The held-out set cannot tell Jev-then-Opus and Opus
alone apart: their ranges overlap almost entirely.

## What the tuning experiments showed

- **The approaches as #379 first specified them.** C, Jev first with the shipped
  judge for the unsure cases, got 78.8% on tuning, deciding 68.6% itself; Jev
  alone beat it, because the fallback is the weaker judge
  (`m52/tuning-thresholds.json`). D, Mini's token probabilities through the same
  rule, had no threshold pair that met the bar on tuning; Mini's probabilities
  are badly overconfident (log loss 1.16 against Jev's 0.37,
  `m52/tuning-prompts.json`). Neither was scored on the held-out set.
- **Jev's mistakes are mostly one kind.** 16 of its 17 errors on the hard tuning
  cases were survivors it called "fails". In 11 of those 16, the test never runs
  the edited line.
- **A bigger model closes most of the gap; tools barely matter.** A coding agent
  (Opus with read-only tools, not allowed to run tests) got all 49 hard tuning
  cases right (`m52/tuning-agent.json`). Opus with no tools, given only Jev's
  exact input, solved 15 of the 17 Jev got wrong; the other 2 needed tracing
  inputs through the code step by step (`m52/tuning-gap-categories.json`).
- **Code context helps only where the edit is cut off.** Whole files, or a
  targeted set (the function holding the edit, the test with its helpers, the
  code the test calls), raised Jev's ranking quality (AUC 0.929 to about 0.95).
  The gain came entirely from youtube-dl and tqdm cases where the usual 30-line
  window cut the edited function short (`m52/tuning-context.json`,
  `m52/tuning-targeted.json`). Where the window already held the function, more
  code did not help. Jev's limit is its reasoning, not missing code.
- **Jev cannot tell whether a test runs a line.** Asked only that, it ranked
  correctly 91% of the time with the edit window and 95% with targeted context,
  but too unreliably to drop cases on its own (`m52/tuning-reach.json`). Telling
  it a reach result did not change its answers (`m52/tuning-reach-hint.json`).

## Not measured

Dropped from #379 when its Acceptance was amended, because the shipped judge
proved the wrong baseline: C and D on the held-out set, calibration (reliability
diagram, Brier score, expected calibration error) on the held-out set, the
five-run repeat check, and time per case on the held-out set. On tuning, the
shipped judge took 871 ms per case; Jev's vendor quotes 70–500 ms per call, which was not measured here.

## Spend

About $17.40 on Opus: $6.56 for no-tools Opus on the tuning cases, $6.25 for
the coding agent, and $4.56 for no-tools Opus on the held-out cases. I believe
Jev and Mini together cost under $1, but their spend was not totalled.
