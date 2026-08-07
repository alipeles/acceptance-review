# Nested-block task fixtures (#216, DR-216 decision 5)

Task files that exist to be *hard for the parser*, not to be realistic.

#216's Acceptance asks that the region-coverage assertion run over the
repository's own committed task files and over
`tests/fixtures/decompose-stability/`. It does, and those runs are worth
keeping as regression guards — but on their own they are **not evidence the
guard works**. Both corpora contain **zero nested bullets**: verified across
`current-task.md`, every `dogfood-logs/*/current-task.md`, and the whole
decompose-stability corpus. The assertion would pass over them under the
parser #216 reports, green on a corpus that cannot fail it.

That is the shape of hole #216 exists to close, and it is the caveat DR-202
§Measurement and CLAUDE.md already record about this repository: *one
repository, one author, unusually well-sectioned mandates.*

So these fixtures deliberately carry what the real corpora never do:

| fixture | exercises |
|---|---|
| `nested-bullets.md` | the #216 reproduction verbatim — nested bullets, and a second paragraph in a list item |
| `multi-paragraph-item.md` | two and three paragraphs inside one list item, in several sections |
| `nested-fence.md` | a code fence nested under a claimed bullet |
| `nested-table.md` | a table nested under a claimed bullet |
| `deeply-nested.md` | three levels of nesting, ordered lists, and blocks after a nested list |

Each one fails region coverage under the pre-#216 parser. They are checked in
`tests/requirement/test_region_coverage.py`.

**These are parser fixtures — nothing here calls the model**, so adding one
costs no transcript and invalidates no recorded run.
