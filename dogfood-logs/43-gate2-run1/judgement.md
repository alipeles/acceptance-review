# Judgement — #43 Gate 2, run 1

**Not clean.** `Task completion: INCOMPLETE`, 11 obligations with
non-discriminating test evidence, 11 recommended tests.

**Command:** `.venv/bin/acceptance check --task current-task.md --base a520d67 --head fcb59fb --mode record --continue e1a0e28ecd9479c7`
**Run id:** `d9d9082200406840`, continuing Gate 1's run `e1a0e28ecd9479c7`
**Cost:** $0.5122 on 70 live calls.

The full triage of all three Gate 2 runs is in `43-gate2-run3/judgement.md`. This
file records only what is specific to run 1.

## Four recommendations named real defects, and they were fixed

1. `pytest_configure` returned early with no report path, leaving the per-test
   clock unarmed while the run still looked sandboxed.
2. A test that ran and called `pytest.skip()` was recorded as never started.
3. One undifferentiated reason for every requested test with no outcome.
4. The launching machine's user site-packages stayed on the child's path.

## One tool defect, and it did not recur

**Twenty pairs were left unjudged, and every one of them was against the same
test** — `test_a_test_that_does_not_exist_is_not_started_rather_than_dropped`,
paired against twenty different enumerated defects, each reported as "offered to
the judge and not answered; no verdict was produced". One test failing to draw a
verdict across twenty independent pairs is a property of the tool, not of the
code under review.

It did not reappear in run 2 or run 3, both of which reported zero unjudged
pairs, with the same test still present. So it is intermittent rather than
deterministic, which is the harder kind to catch. A drafted filing is queued in
`docs/DEFERRED.md` under #183, the evidence-judgement umbrella.

## Findings that were not defects

- The C-extension network bypass: a real limit, documented in
  `netblock.py::install_network_block`, and unkillable by any test.
- `PYTHONPATH` leakage on `no-launch-credentials-visible`: wrong. `PYTHONPATH` is
  not in the inherited allowlist and is overwritten. The finding did imply a real
  neighbouring gap — user site-packages — which was fixed.
- Duplicate test ids collapsing, and an empty request producing no outcomes: both
  deliberate, and the second is why `only-named-tests-run` holds at all.
