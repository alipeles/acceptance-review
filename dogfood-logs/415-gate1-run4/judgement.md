# #415 Gate 1, run 4 — `0120ca7731131f30`, at 9527671, continuing run 3

6 requirements, 9 obligations, no open questions.

## Why this run exists

Run 3's task file, confirmed by the owner, was wrong on a fact I supplied: it
named "the benchmark's command-line runs — the instability measurement and the
mutant audit". The mutant audit (`python -m acceptance.benchmark.mutants`) makes
no model call, and the instability measurement (`measure_instability`) has no
command line; it is a library function. Found while reading the code, before
any was written. The owner chose: `measure_instability` prints the table when it
finishes; the mutant audit is dropped.

## Findings

- task-01 now yields `instability-measurement-prints-usage-table`,
  `usage-table-covers-every-measurement-call` and
  `usage-table-live-replayed-counted-apart`. All accurate; the purpose clause
  that produced run 3's duplicate is gone.
- Every other obligation carried unchanged and accurate. None missing.

## Disposition

Accurate. I confirmed it; the owner had chosen the scope it encodes.
