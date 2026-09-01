"""The repository's committed task-file corpus (#258).

Every dogfood run commits the exact task file it was given, alongside the output
it produced, and never edits it again. That makes `dogfood-logs/*/current-task.md`
a stable corpus: it only grows, and each entry is governed by a commit.

The repository-root `current-task.md` is deliberately **not** part of it. That
file is a scratch input — rewritten for every task, and edited mid-task by the
Gate 1 procedure — so a test reading it has an outcome that depends on work in
flight rather than on the code. Worse, a parametrize built from it computes its
case list at collection time, so the *number of tests and their ids* moved with
an uncommitted working file, and the suite could not be compared across runs.
A fresh clone with no `current-task.md` at all failed outright.

**The corpus is filtered to structurally distinct files, and that is new.** Two
tests are parametrised over it, so every dogfood run used to add two tests
permanently: 169 files and 338 tests, 20.7% of a 1,636-test suite, growing with
process history rather than with the software. Runtime was never the problem —
the two together take 2.8 seconds — but three other things were. The marginal
file bought nothing, because both tests only assert that the markdown parser
handled it and file 170 exercises the same shapes as file 169. Suite *size*
became a function of which process artifacts were committed, which is what made
a ten-test gap between a branch and CI take a worktree and a diff to explain.
And a fifth of the suite being one parse corpus distorts any reading of test
counts as coverage.

So the corpus keeps the first file of each distinct markdown *shape* rather than
every file. See `_signature`.
"""

from __future__ import annotations

from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode

REPO_ROOT = Path(__file__).resolve().parents[2]

# Run directories kept whatever their shape. Empty by design, and the mechanism
# matters more than the current contents: a file kept as a NAMED regression —
# the reproduction for a specific defect — must survive even when some earlier
# file happens to share its shape, and without this there is no way to say so.
# Add the run directory's name, e.g. "216-gate1-run1", with a comment naming the
# defect it reproduces.
ALWAYS_KEEP: frozenset[str] = frozenset()


def _signature(text: str) -> tuple:
    """What makes one task file a structurally different parse from another.

    **Built from markdown-it, and deliberately NOT from `parse_task_file`.** The
    tests this corpus feeds are tests *of* `requirement/task_file.py`. Building
    the case list by running that parser would mean a parser regression could
    shrink the corpus, and the suite would quietly stop covering the thing that
    broke. markdown-it is a level below: `task_file.py` reads its tree, this
    reads its tree, and neither reads the other. If markdown-it's own behaviour
    moved, both would move together, which is honest coupling rather than a
    parser grading its own homework. `test_region_coverage.py::_has_nested_blocks`
    already reaches for markdown-it the same way.

    Four features, each chosen because a consumer is sensitive to it:

    - **the set of block token types present**, which is what
      `test_the_repositorys_own_task_files_are_fully_covered` is really testing
      — an unrecognised construct is what leaves a region unread. A hand-rolled
      regex scan would have to enumerate constructs in advance and would miss
      the one nobody thought of, which is the whole failure mode;
    - **heading text**, because `task_file.py` keys its sections off heading
      names and anything else becomes an unread region;
    - **list nesting depth**;
    - **whether any list item holds more than one block**, the construct the
      pre-#216 parser dropped.
    """
    root = SyntaxTreeNode(MarkdownIt("commonmark").enable("table").parse(text))
    kinds: set[str] = set()
    headings: list[str] = []
    depth = 0
    multi_block_item = False

    def walk(node: SyntaxTreeNode, list_depth: int) -> None:
        nonlocal depth, multi_block_item
        for child in node.children:
            kinds.add(child.type)
            here = list_depth
            if child.type in ("bullet_list", "ordered_list"):
                here = list_depth + 1
                depth = max(depth, here)
            elif child.type == "heading":
                headings.append(
                    "".join(c.content for c in child.walk() if c.type == "text").lower()
                )
            elif child.type == "list_item" and len(child.children) > 1:
                multi_block_item = True
            walk(child, here)

    walk(root, 0)
    return (tuple(sorted(kinds)), tuple(headings), depth, multi_block_item)


def committed_task_files(root: Path = REPO_ROOT) -> list[Path]:
    """One committed dogfood task file per distinct markdown shape, in stable order.

    Order is the glob's, so "first of each shape" means the earliest path, which
    keeps the selection stable as the directory grows: a new run adds a case only
    when it brings a shape no earlier run had, and never displaces an existing
    one. Every path in `ALWAYS_KEEP` is kept regardless.

    `is_file()` is belt-and-braces, and measured to be so: `glob` resolves a
    literal final component through `exists()`, so a pruned entry or a symlink
    whose target is gone never reaches this filter in the first place. Removing
    the filter changes no result — verified by injection, not assumed. It is
    kept because it costs nothing and states the intent, but it is **not** what
    makes the "an absent path is not a case" property hold, and no test here
    discriminates it.
    """
    kept: list[Path] = []
    seen: set[tuple] = set()
    for path in sorted(root.glob("dogfood-logs/*/current-task.md")):
        if not path.is_file():
            continue
        if path.parent.name in ALWAYS_KEEP:
            kept.append(path)
            continue
        try:
            signature = _signature(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            # Unreadable is not "no shape": keep it, so the parse test reports
            # the problem rather than the corpus silently dropping the file.
            kept.append(path)
            continue
        if signature in seen:
            continue
        seen.add(signature)
        kept.append(path)
    return kept
