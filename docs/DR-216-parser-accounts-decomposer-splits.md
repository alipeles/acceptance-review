# Decision Record 216 — The parser accounts for blocks; the decomposer splits and declines

*Relates to issue #216 and the #181 umbrella (decomposition). Status: **accepted
and built**. Track: checker. Stage: 1. Consistent with DR-202 and DR-204.*

---

## The decisions

**1. Every leaf block becomes an accountable region.** Each non-whitespace,
non-heading block in a §7.1 task file is inside a registry span or inside an
`unclaimed` span, never neither. Blocks are markdown-it AST nodes — list items,
paragraphs, fences, tables, nested lists — so enumerating them and proving their
spans tile the source is deterministic and provable.

**2. Nested content under a claimed list item becomes its own requirement**, with
its own id and disposition, rather than widening its parent's span. This covers
nested bullets and second or subsequent paragraphs inside a list item.

**3. The parser never judges block type or semantic content.** A nested fence, a
nested table and a nested bullet are treated alike. There is no rule that fences
are illustrative or that tables are cases.

**4. The decomposer splits and declines.** One requirement yields one obligation,
several, or none with a stated reason. The judgment about what a block *means*
lives there, and it is already there.

**5. The coverage assertion runs over purpose-built fixtures**, not only over the
repository's real task files. See *Measurement* below.

## Why the parser stops at block boundaries

Two jobs are easy to conflate, and only one is the parser's:

| job | deterministic? | whose |
|---|---|---|
| carve the source into accountable regions | **yes** — AST leaf blocks | parser |
| find the independent requirements *inside* a region | **no** | decomposer |

There is no deterministic way to find the independent requirements inside a
paragraph or a table. A paragraph reading *"The parser widens the span and
reports what it cannot claim, unless the block is a fence"* is two or three
requirements; markdown structure gives no signal, sentence-splitting both over-
and under-splits, and a table is sometimes one requirement with rows as cases and
sometimes one requirement per row.

#216's invariant does not require that. It requires that every region be
accountable, not that every region be one requirement. Decision 3 follows: a
parser that cannot reliably identify requirements should not be identifying block
roles either.

## Why the splitting job is already handled

**The registry's unit is a source block, not a semantic requirement, and always
has been.** In `dogfood-logs/216-gate1-run2/`, `task-01` is a seven-line prose
paragraph that yielded four obligations:

```
[task-01] `parse_task_file` walks the top-level nodes ...
    -> obligation-parse-nested-content-as-own-or-unread
    -> obligation-second-paragraph-as-own-or-unread
    -> obligation-no-unaccounted-region-for-nested-bullet-item
    -> obligation-no-unaccounted-region-for-multi-paragraph-item
```

DR-204 preserves this deliberately — *a call may split one requirement into
several obligations* — while forbidding only linking.

Declining works too, in the same run:

```
[completion-01] Implementation
    -- no obligation, deliberately
       Section marker only; it does not add a checkable requirement by itself.
```

So a nested table needs no parser rule. It becomes one accountable block, and the
decomposer yields one obligation, or five, or declines it as illustrative with a
reason. #217 made that decline honest — it now carries its reason rather than
being downgraded.

## Why nested content gets its own requirement rather than widening its parent

Both satisfy the coverage invariant. Decision 2 rests on the ground DR-204
settled: **lossy versus noisy.**

Widening the parent's span makes a nested bullet that is a real requirement
disappear inside it — no id, no disposition, no separate obligation — and a
parent declined `no_obligation` silently declines everything nested under it.
That is #223's shape: content present in the input, absent from the accountable
set, under a clean count.

Giving it its own requirement makes a nested bullet that is merely an elaboration
cost one redundant requirement yielding a duplicate obligation, which #144 now
merges. Noisy and recoverable, against silent and not.

## Measurement

**The repository's own task files contain zero nested bullets** — verified across
`current-task.md`, every `dogfood-logs/*/current-task.md`, and the whole
`tests/fixtures/decompose-stability/` corpus.

So #216's Acceptance item *"the coverage assertion runs over the repository's own
committed task files"* would pass **vacuously**: green on a corpus that cannot
fail it. That is the shape of hole #216 exists to close, and CLAUDE.md already
records the caveat as *"one repository, one author, unusually well-sectioned
mandates"*.

Hence decision 5. The fixtures must exercise nested bullets, multi-paragraph list
items, nested fences and nested tables. Running the assertion over the real
corpora stays worthwhile as a regression guard; it is not evidence the guard
works.

**As built:** the fixtures are `tests/fixtures/nested-blocks/`, the assertion is
`tests/requirement/region_coverage.py`, and both corpora are still asserted over
in `tests/requirement/test_region_coverage.py`. The vacuity argument is itself
tested — `test_each_purpose_built_fixture_actually_exercises_nesting` fails a
fixture that could not distinguish the fixed parser from the reported one. Run
against the pre-#216 parser, all five fixtures fail and both real corpora pass,
which is the measurement claim above confirmed rather than asserted.

The assertion is stated over source **characters**, not over the blocks the
parser descends into. Enumerating the parser's own blocks would be circular: it
would pass for any self-consistent parser, including the one #216 reports.

## A contradiction in #216 to fix

The issue describes two different pairs of alternatives:

- Its `Open:` paragraph asks whether nested content is a requirement in its own
  right **or a continuation of its parent**.
- Its Acceptance requires the reproduction to yield five requirements **or two
  requirements plus three unread blocks**.

Treating nested content as a continuation satisfies the invariant but yields two
requirements and nothing unread, which the Acceptance does not admit. Under this
record the Acceptance stands as written — five requirements — and the `Open:`
paragraph is resolved by decision 2.

## What this does not settle

**Nothing detects when the decomposer under-splits a block.** Block-level
coverage proves the *parser* lost nothing; it proves nothing about whether every
requirement inside a block was found. A paragraph holding three requirements
where the model notices two yields a `yielded` disposition, a complete-looking
count, and an invisible third.

This is pre-existing rather than introduced here — `constraint-09` in run 2 is a
compound requirement that yielded a single obligation — and it is not closable by
the parser, which is why it is out of #216's scope. Filed as #224, a child of
#181.

Related: #216, #181, #202, #204, #217, #223, #224, #117, #193, #211, DR-202,
DR-204.
