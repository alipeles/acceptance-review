# Task

The reachability prefilter in `src/acceptance/defects/reachability.py` excludes a
(defect, test) pair from judgement only when it can prove the test has no path to
the defect. Its proof follows imports, fixtures and Python names, so it holds only
for defects that live in Python modules.

When any of a defect's implicated files is not a Python module — a Markdown
document, a config file, a data file read from disk — the prefilter makes no
exclusion for that defect: every pair with that defect is sent to the judge.
Defects whose implicated files are all Python modules are prefiltered by the
existing rules.

A regression test is part of the deliverable: a test that opens a non-Python file
by path and asserts on its content, paired with a defect implicating that file,
is judged and not prefiltered.

## Scope exclusions

- Recognising a test that names a file's path in its source as reaching that file.
- Any change to the judge, the defect builder or how prefiltered pairs are scored.
