# Task
Materializing an archetype fixture into a git repository must commit exactly the
files the fixture describes, and must produce the same commit identifiers every
time it runs.

## Constraints
- The base commit's tree holds exactly the files of the fixture's `base`
  directory, each carrying that file's content.
- The head commit's tree holds exactly the files of the fixture's `head`
  directory, each carrying that file's content.
- A file whose content differs between `base` and `head` is committed with its
  head content even when the head file has the same size, mode and modification
  time as the base file it replaced.
- What a commit records is determined by file content alone, not by the
  modification times of the files on disk.
- What a commit records does not change when git is configured to compare a
  working-tree file against its recorded status using fewer fields.
- Materializing one fixture twice produces the same base commit identifier both
  times, and the same head commit identifier both times.

## Scope exclusions
- Whether a fixture's `base` and `head` trees describe the change they are meant
  to describe.
- Which archetype fixtures exist, and the ground-truth labels attached to them.
- How long materialization takes.

## Completion expectations
- Implementation
- A test asserts that a file replaced between base and head by content of the
  same size, mode and modification time is committed with its head content.
- A test asserts that the committed content of every file in a materialized
  fixture equals that file's content in the fixture directory.
- A test asserts that materializing one fixture twice produces the same base
  commit identifier and the same head commit identifier.
