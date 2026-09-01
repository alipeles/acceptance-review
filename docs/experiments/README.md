# Experiments — what is here and which are still open

Offline measurements that informed a decision, kept so the decision can be
re-argued against numbers rather than memory. Each directory holds its own
`README.md` (the method and its traps) and `FINDINGS.md` or `findings.json` (the
numbers). A decision that shipped has a Decision Record in `docs/`; an
experiment on its own never is one.

**This index exists so a finished experiment does not read as an open one.** The
two prefilter directories reached a result and then stopped on something only
M8.4 can settle, and without a line saying so they look abandoned.

## Waiting on M8.4 — do not re-litigate before then

M8.4 is the execution tier's defect injection: inject a defect, run the test,
see whether it fails. It is the only thing that can adjudicate a *disagreement*
between a static filter and the pair judge, because both are opinions and
neither is ground truth.

| directory | what it found | what M8.4 decides |
|---|---|---|
| `coverage-prefilter/` | Coverage reachability excludes 61.3% of 23,808 pairs but drops 43 of 268 recorded kills (84.0% recall); the conservative rule keeps 267 kills and excludes 3.5%. Neither is shippable as a silent prefilter. | Whether the 43 lost kills are filter blind spots or judge error. If judge error, coverage's ~61% exclusion becomes available. Separately: the same coverage map is the natural **test selection for injection itself** — a test that never executes a line cannot fail on a mutation of it. |
| `prefilter-committee/` | Three voters — locality, coverage, embeddings — joined by reject-only-when-all-reject. Transferred across corpora it excludes 26.0% and 30.6% while losing 1 of 127 and 2 of 268 kills, worth roughly $1.70 a run. Zero-loss thresholds do **not** survive transfer, so it is not lossless. | The same question. Three specific pairs cap every transferred committee, and they are from the same families that cap coverage alone: end-to-end replay, doc-text reads, ledger carry. |

Both stop at the same wall, and it is one wall: a small set of pairs where a
static signal and the judge disagree, which nothing static can adjudicate. When
M8.4 lands, run its injection over those pairs first. That measures pair-verdict
accuracy against ground truth for the first time — #315's human-reviewed labels
are the only current proxy — and settles both experiments at once.

**Neither is runnable from a clean checkout without inputs that are not in the
repo**: a worktree at the reviewed revision, a `.coverage` file from an
instrumented suite run there, and the review's own JSON. Each script names what
it needs and stops with a sentence when it is missing;
`prefilter-committee/paths.py` lists the environment variables. They also need
`pip install coverage`, which is deliberately not a project dependency — the
tool does not use it, only these experiments do.

## Settled

| directory | question | where the decision lives |
|---|---|---|
| `pair-response-shape/` | Which response shape the (defect, test) pair question uses, and whether the `test_id` enum can go. | `docs/DR-314-pair-response-shape.md` for the shape; the `test_id` result shipped in `defects/pair_mapping.py`. |
| `pair-prefilter/` | Whether a cheap filter can cut the pair set before the judge. Found an embedding union excluding 22.0% with no recorded kill lost — in-sample. | Superseded by `prefilter-committee/`, which showed the zero-loss property does not transfer. |
| `obligation-dedup/` | When the linking stage should call two obligations duplicates. | `requirement/linking.py`. |
| `265-prompt-cache-baseline/`, `265-cache-key-scope/` | What the transcript corpus was actually caching, and what a request key's scope should be. | #265; the per-stage key behaviour in `llm.py`. |
| `317-over-answering/` | Whether the judge answers about pairs it was not offered. | #317. |
| `191-discrimination-partition/` | Rating instability under partitioning of the discrimination stage. | #191. |

## Adding one

Copy the shape, do not invent a new one: a `README.md` that is the method and
the traps, a `FINDINGS.md` that leads with the answer, and the raw numbers in
JSON so a disagreement with the write-up can be traced to the case that caused
it. Name external inputs through the environment rather than hard-coding a path
— two of the directories here arrived with absolute paths into a container and
could not be run or checked until they were rewritten.
