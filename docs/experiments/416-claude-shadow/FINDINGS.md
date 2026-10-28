# Claude beside GPT-5.4 on the existing hand labels (#416)

Findings for #416, part of #412 (moving model calls from OpenAI to the Claude
API). The question: before any judge is switched to Claude, how does Claude
score on labels we already have, next to the GPT figures those labels produced?
Nothing is switched by this document. Run 2026-10-26.

## The answer

- **Edit verifier** (`mutation/verification.py`, the model call that decides
  whether an injected edit really puts its named defect into the code): Claude
  is as good as GPT-5.4 at refusing bad edits and refuses about half as many
  good ones. Neither Claude model clears the adoption bar reliably, so
  `verify_edits` stays off.
- **"Would this test fail under this defect"** (the M5.2 discrimination
  judgement), on #372's 231 BugsInPy operator mutants: Sonnet 5.5 is far ahead
  of GPT-5.4 Mini, the model #379 measured. 90.2% against 66.3% as the batched
  judge #379 scored, and 96.7% against 82.6% asked one case at a time.
- **Not measured:** the pair mapping judge (which test is evidence for which
  obligation). No hand labels for it were found. #416's Acceptance names it, so
  #416 stays open.

## Edit verifier

`score_verifier.py`. Today's verifier prompt, no surrounding-code context, the
edits rebuilt from audits v6 and v10 at revision 518f876 with the stored defect
list `dogfood-logs/45-injection-audits/injection-audit-v6.defects.json`. Every
v6 edit was checked against the source at 518f876 before it was asked about.
GPT-5.4 was re-run on today's prompt as well, because the prompt has changed
since DR-171's figures (27 of 35 and 8 of 31 on v6; 16 of 21 and 5 of 31 on
v10). Results in `results/`.

The adoption bar (DR-171): at least 80% of bad edits refused, under 10% of good
edits refused. Per `docs/audit-protocol.md`, only audit v10 can confirm it; v6
has been measured against too often.

| audit | model | bad edits refused | good edits refused | cost |
|---|---|---|---|---|
| v6 (35 bad, 31 good) | GPT-5.4 | 28 (80%) | 9 (29%) | $0.44 |
| v6 | Sonnet 5.5 | 29 (83%) | 4 (13%) | $0.59 |
| v6 | Opus 5.5 | 28 (80%) | 4 (13%) | $1.30 |
| v10 (21 bad, 31 good) | GPT-5.4 | 17 (81%) | 6 (19%) | $0.25 |
| v10 | Sonnet 5.5, three runs | 16 / 16 / 18 | 3 / 3 / 4 | about $0.48 a run |
| v10 | Opus 5.5, three runs | 17 / 16 / 17 | 3 / 3 / 3 | about $0.98 a run |

The repeats record into their own transcript directories (`--repeat`), so their
answers are fresh. Catching bad edits moves by about two edits between runs of
one model, which is ten points on 21 bad edits and the whole distance between
missing and clearing the bar. Opus clears it in two of three runs, Sonnet in
none. The false-alarm difference is the result that holds: Claude refused 3 or
4 good edits in every run, GPT-5.4 refused 6 on its one run.

## Would this test fail under this defect

`mutants/`. The 92 held-out and 137 tuning cases from #379's split
(`docs/experiments/jev/m52/split.json`); 53 killed and 39 survived held out.
Only the model is swapped, with one exception noted below. GPT-5.4 Mini rows are
from `docs/experiments/jev/FINDINGS-m5.2.md`.

| design, 92 held-out cases | accuracy (95% Wilson) | precision on "fails" | recall on "fails" | precision on "survives" | recall on "survives" | cost per case |
|---|---|---|---|---|---|---|
| batched judge, GPT-5.4 Mini | 66.3% (56–75) | 0.789 | 0.566 | 0.574 | 0.795 | $0.0006 |
| batched judge, Sonnet 5.5 | 90.2% (82–95) | 0.911 | 0.962 | 0.941 | 0.865 | $0.0061 |
| one call per case, GPT-5.4 Mini | 82.6% (74–89) | 0.785 | — | — | — | $0.0006 |
| one call per case, Sonnet 5.5 | 96.7% (91–99) | 0.963 | 0.981 | 0.974 | 0.949 | $0.0048 |

On the tuning cases Sonnet scored 93.4% as the batched judge and 97.8% one call
per case. Precision on "fails" is the costly error: a false "this test would
fail" makes a weak test look strong.

What to weigh:

- **The batched judge no longer exists in the code.** #385, which adopted Jev
  with a fallback model, deleted it. `mutants/pair_mapping_fc9defc.py` is the
  module copied verbatim from `fc9defc`, the version #379 scored. Replaying
  GPT-5.4 Mini through it against #379's archived recordings reproduced 66.3%
  and $0.0566 exactly, so the requests are the same.
- **The one-call Sonnet arm uses different call settings from Mini's.** Mini
  ran with reasoning off and a 16-token limit, reading yes or no from
  log-probabilities. With those settings Sonnet ignored "answer with exactly one
  word" and was cut off on 4 of 4 probe cases, and the Claude API offers no
  log-probabilities. So Sonnet ran with thinking on and a 4096-token limit, and
  the verdict is the last word of its answer. All 229 answers parsed. The prompt
  is unchanged. Part of the gap is thinking against no thinking.
- **This held-out set has been scored many times** by #379's designs and now
  these. A figure on it is weaker evidence than one on untouched cases.
- Two batched-judge held-out cases came back with no verdict and count as wrong.
- The labels came from the archived #379 cache
  (`~/code/acceptance-worktrees/_archived-caches/379-jev-experiment/mutant-labels/`),
  copied into `.acceptance/mutant-labels/`, which is gitignored.

## Spend

About $8.20 in Anthropic credits: $5.88 on the edit verifier, about $2.30 on
the mutants. $0.69 at OpenAI for the two GPT-5.4 verifier runs. No batches.

## Not done

- The pair mapping judge.
- Re-deriving per-action thresholds on development cases, which #416 asks for
  only once a judge is switched.
- Whether a judge should switch. These figures are an input to that decision,
  not the decision.
