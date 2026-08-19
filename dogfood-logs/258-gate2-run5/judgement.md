# Judgement — #258 Gate 2, run 5

**INCOMPLETE, but the largest single improvement of the sequence.** Eight
obligations moved `partially supported -> strongly supported`; the weak set went
from fourteen to six.

Base `a4abbf4` → head `43c3646`. Live calls.

## What produced it

Rereading all fourteen of run 4's prescriptions in full — rather than assuming
they restated run 3's — found three that named real holes in the tests written
the round before:

- **Outcomes, not only collection.** A test that reads the root file to compute
  an expected value keeps its node id and changes what it asserts. The affected
  subset is now run in both root-file states and the summaries compared.
- **No silent skip.** The absent run must contain no `skipped` and no
  `no tests ran`, and both runs must exit alike.
- **The exclusion rule itself.** The guard's `fixtures` exclusion must drop those
  files and nothing else; naming two files it has to see does not catch an
  exclusion that widens.

Three assertions, eight ratings. Worth noting against the run-3→run-4 pair,
where six whole tests moved four ratings and cost one.

**Every one of the fourteen defect statements had changed since run 3**, for
obligations whose text never moved and against source that never changed. The
prescriptions are not a stable description of a gap; they are a by-product of the
response that produced them. That is queued against #225.

## The six that remain

| obligation | defect the prescription names | class |
|---|---|---|
| 2, `…-non-empty-test` | *"returns only non-dogfood paths but still non-empty"* | addressable |
| 3, `…-stays-within-…` | *"includes only dogfood-logs paths but also duplicates one"* | addressable |
| 4, `no-root-task-file-read-check` | *"read indirectly through a helper, no literal pattern in any source"* | addressable — and a good catch |
| 5, `no-root-task-file-read` | *"a helper reads it only on an untested code path"* | addressable |
| 11, `…-nonempty` | *"contains one case but the reproduction logic ignores it"* | crosses `exclusion-03` |
| 12, `…-omits-missing-path` | *"omits a present file as well as the missing one"* | **prescribes its own cited evidence** |

Obligation 12 is worth reading in full, because the prescription and the citation
are two lines apart in the same block:

```
       test evidence: partially supported  [tier: static]
         12.2  tests/requirement/test_task_file_corpus.py::test_an_entry_whose_target_is_missing_is_omitted
         recommended test: The region-coverage case list excludes at least one path that is absent from the tree.
           detects: The corpus builder omits a present file as well as the missing one.
```

`test_an_entry_whose_target_is_missing_is_omitted` asserts
`committed_task_files(tmp_path) == [real]` — the dangling entry omitted, the real
one kept, which is exactly the named defect. The stage cited it as the
obligation's evidence and prescribed it in the same breath. This is #225's second
half in its cleanest form.

Obligation 4's is the opposite and is the best prescription this tool has
produced for #258: a source scan cannot see a read reached through a helper or an
alias, and absence alone does not probe it either, since a read guarded by an
existence check passes happily when the file is gone. That became
`test_a_read_of_the_root_path_would_fail_the_affected_tests`, which makes the
root path a *directory* so any read raises however the path was arrived at.
