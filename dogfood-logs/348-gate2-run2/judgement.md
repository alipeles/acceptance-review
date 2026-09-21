# #348 Gate 2, run 2 — run `845dbd7c4ca04392`, continuing `6806443320874a62` — NOT clean

Verdict UNABLE-TO-DETERMINE: one obligation indeterminate. Run 1's `separable`
flag is gone now that the task file names the findings update.

## The first attempt died on a provider error

`output-attempt1-502.log`: `litellm.APIConnectionError: VoyageException - 502
Bad Gateway`, raised from `pair_ranking.py::rank_pairs` and not caught anywhere
— the CLI printed a raw traceback. No provider call in `llm.py` is retried,
completion or embedding. The second attempt (this log) replayed the 74 calls
the first had already recorded (the footer: $0.47 of recorded evidence at no
cost), so the money lost was small; the wall-clock time, including the
injected-edit test runs, was not. Queued as a blocker filing against #184.

## 1. `docs-ranking-experiment-findings` — indeterminate — addressed

"The ranking experiment's findings record whether the ranking still holds …
and what stopping early costs and saves" was derived as owing test evidence,
and nothing tested it. This repo tests document content where the content is
a record of a decision (`tests/test_decision_records.py`), so it is addressed
the same way: `tests/test_rank_prefilter_findings.py` checks each outcome is
stated, and that the replay figures in the prose are the ones the committed
replay logs printed. Checked by injection: changing one share in FINDINGS.md
fails it.

## 2. `[no_obligation] completion-01: Implementation` — not acted on

The tool reports the line as "a section marker standing alone with no
requirement under it … taken at face value and not counted against coverage".
That is the correct reading of a spec §7.1-grain completion line, and it asks
for nothing.

## 3. `[already_present] pairs-asked-about-count-per-defect/asked-count-excludes-unanswered-pairs` — tool defect

The same false lead as run 1; recorded against the filing queued then
(`docs/DEFERRED.md`, 2026-09-21, "An enumerated 'defect' whose defective
behaviour is the requirement, confirmed as already present").

## Unrequested changes

Six, all `in_service`. None `separable`.
