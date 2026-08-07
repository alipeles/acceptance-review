# Task
`parse_task_file` walks the top-level nodes of the parsed task file and spans
each list item using `_inline_content`, which returns the first inline node it
finds and stops. A list item whose content is a paragraph followed by a nested
bullet list therefore yields the first paragraph's text, that text is located in
the source, and the narrow span is accepted. The nested list is never visited.
The same happens to a second paragraph inside a single list item, and to any
block nested inside a claimed item — a nested code fence, a nested table.

The widening fallback in `_span` fires only when the inline text cannot be found
in the source. Here it is found, so the fallback never runs.

Because the item was claimed, the dropped content reaches neither the registry
nor `unclaimed`. It produces no requirement id, receives no disposition, and
cannot be recorded as unaccounted for, because no registry entry exists for it.
`unread_source` is therefore empty and the CLI prints `unaccounted for: 0`.

#202 established that a parse may only be authoritative if it reports what it
missed, and taught readers to trust that zero. This drop occurs under a clean
bill of health, which is worse than a drop under no bill of health at all.

Decide whether nested content under a claimed list item is a requirement in its
own right or a continuation of its parent, then make the parse account for every
region of the task file: each one is either inside a registry span or inside an
unclaimed span, and never inside neither.

## Constraints
- Nested content under a claimed list item is extracted as its own requirement,
  or reported as unread. It is never absent from both.
- A second or subsequent paragraph inside a single list item is extracted as its
  own requirement, or reported as unread.
- The choice between extracting nested content and reporting it as unread is
  made once, stated, and applied uniformly.
- `unclaimed` accounts for all task-file text, not only text under unrecognised
  top-level headings.
- Every non-whitespace, non-heading region of a task file is inside a registry
  span or inside an unclaimed span.
- A test asserts that total coverage directly, over the source regions rather
  than over a requirement count.
- That coverage assertion runs over the repository's own committed task files.
- That coverage assertion runs over the `tests/fixtures/decompose-stability/`
  corpus.
- A task file whose Constraints bullet carries two nested bullets, plus a second
  Constraints bullet carrying a second paragraph, yields five requirements, or
  two requirements plus three unread blocks.
- The reported unaccounted-for count is non-zero whenever task-file text was in
  fact not read.
- Typed schemas are pydantic models, as the rest of the repository defines them.
- Tests issue no live model calls.

## Scope exclusions
- Whether the model yields an obligation for a given requirement. This change
  concerns only which requirements the parse produces and which regions it
  reports as unread.
- The wording of the decomposition prompt, which is #204, #205, #206 and #219.
- Reconciling a disposition against the requirements a call supplied, which
  #217 settled.
- Recovering the requirements a prior run dropped, or comparing counts against
  recorded transcripts.
- Nested content inside headings the parser does not recognise, which #202
  already reports through `unclaimed`.

## Completion expectations
- Implementation
- The reproduction in #216 yields five requirements, or two requirements plus
  three unread blocks.
- A list item containing a nested bullet list contributes no unaccounted region.
- A list item containing two paragraphs contributes no unaccounted region.
- A test asserts region-level total coverage over the repository's committed
  task files.
- A test asserts region-level total coverage over the decompose-stability
  corpus.
- The decision between nested-as-requirement and nested-as-unread is recorded in
  the repository.
