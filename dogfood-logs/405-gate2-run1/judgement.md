# #405 Gate 2, run 1 — judgement

Run `18c717ef086fedb2`. Verdict INCOMPLETE. **Not clean.** Cost $1.48.

## Findings and dispositions (proposed; owner decides at the gate)

1. **Set-aside test** `test_the_network_is_not_blocked_under_a_test_command`
   failed. Real, my test: its last line asserted the suite's own process had no
   network block, but two tests in `tests/test_execution_sandbox.py` call
   `netblock.pytest_configure` in-process and leave the block installed.
   Fixed by removing that line. The in-process leak predates #405; queued.

2. **Needs human review — "already defective" claim** on `print-env-var-names`:
   the model says the names are not printed "in output" because they go to
   stderr. I believe this is wrong: stderr is on the terminal, and stdout is
   kept for the report so two reviews stay byte-identical (the run id goes to
   stderr for the same reason). Its "repair" only rewrites a docstring.

3. `pytest-collected-tests-match-requested-tests` partially supported. The
   uncaught defect: names collected before pytest exits with an error are
   discarded. That is the existing design (`_collect_in_workspace`: the set
   must collect jointly, then file by file). Proposed: tool defect, #283 shape
   (an enumerated defect that does not violate the obligation).

4. `test-command-provided-once-per-repo` partially supported. Uncaught defect:
   storing the parallel count "splits" the one record. There is one file per
   repository. Proposed: address with a test that setting twice leaves one
   record.

5. `run-tests-with-configured-command` partially supported, and the
   recommendation's enumeration names a real mismatch: the tool adds
   `-p <plugin> -p no:cacheprovider --no-header` and `-q`/`--collect-only`, not
   only the tests. The mandate says "adding only which tests to run".
   **Owner's call.** Also: shell string and absolute paths, which are DR-405
   design — address with a test that shell quoting in the command survives.

6. `reconfirm-on-command-change` partially supported: same command, new
   `--parallel` → asked again? Address with a test.

7. `test-command-parallel-copies-limit` partially supported: `--parallel`
   from the setter survives the round trip. Address with a test.

8. Unrequested change 5, `[separable]`: the `.venv` link in copies. I believe
   it is in service of `use-project-dependencies` (the copy is where broken
   code runs, and without the link the command's interpreter is missing).
   Proposed: tool defect, a comment on #375 (a change that delivers an
   obligation rated as an unrequested risk).
