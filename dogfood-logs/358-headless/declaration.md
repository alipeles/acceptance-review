# Declaration — #358

**Implemented.** In `src/acceptance/defects/reachability.py::_exclusion_reason`, a
new early return: if any of the defect's implicated files (the paths in its
`path#hunk` code refs) does not end in `.py`, the pair is judged, never
prefiltered. It sits right after the "no implicated files" check, so it applies
before any test-module parsing. The module docstring's list of proof conditions
gains this as condition 2, and the two later references to condition numbers
("Condition 3 is what makes this rare", "condition 6 harder") were renumbered.

I took the issue's first option (non-Python implicated file means no
prefilter). I did not take the second option (a test whose source names the
file's path counts as reaching it).

**Tested.** Two new tests in `tests/defects/test_reachability.py`:
- `test_judges_a_test_that_reads_a_non_python_implicated_file` — a test that
  opens `FINDINGS.md` by path, paired with a defect implicating `FINDINGS.md#0`,
  is judged. Failed before the fix with the exact "no path to the defect exists"
  reason the issue quotes; passes after.
- `test_judges_when_any_implicated_file_is_not_python` — a defect implicating
  both `billing.py` and `config.toml`, paired with an unrelated arithmetic test,
  is judged. Failed before, passes after.
The existing `test_excludes_and_records_the_one_provable_shape` still passes,
so a Python-only defect is still prefiltered.

**Left out.** Path-naming detection (the issue's second option). I did not
replay #348's Gate 2 run 3, which is the issue's Acceptance check; the unit
test reproduces its shape on a constructed fixture instead.

**Assumed.** "Python module" means a file whose suffix is `.py`. A `.pyi` stub
or `.pyx` file counts as non-Python, so its defects are always judged — the
safe direction for this filter.

**Unverified.** The Acceptance replay of `dogfood-logs/348-gate2-run3/`. The
full suite shows 11 failures, all from corpus case `163-gate2-run1` naming a
revision (`41cd0da`) and tag that origin does not have; I believe these are
unrelated to this change and checked that on a clean checkout of main (see
notes.md).
