"""The free baseline: does a test's discovery signal touch the defect's own file?

This is the filter to beat, and it is measured first on purpose. It costs
nothing — no model call, no embedding — because every signal it uses was already
computed to discover the test in the first place. If it excludes a large share
of pairs and loses no kill, an embedding filter has nothing left to buy.

## What it does, and the one thing it adds to discovery

`evidence/discovery.py` asks whether a test matched *anything* changed, and keeps
the test if so. It records `reasons` — the kinds of match — but not **which**
changed file each match came from, because it has no use for that.

This filter asks the sharper question. It recomputes the same four signals and
keeps the file each one landed in, giving every test a set of changed files it
demonstrably touches. A pair survives when that set meets the defect's own
files, and is excluded when the two are disjoint.

## What it is NOT

**Not a proof of unreachability**, and it must never be confused with
`defects/reachability.py`, which is. That module's docstring shows the case this
one gets wrong: a test that calls a helper which calls the defect's code
references no changed name, imports no changed module, and would still fail. One
hop cannot see the second edge.

That is exactly why this is measured rather than shipped on argument. The
recorded verdicts say how often the case that breaks it actually occurs.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from corpus import Corpus, Defect

from acceptance.evidence.discovery import (
    _imported_module_stems,
    _names_called,
    _names_referenced,
    _test_items,
)


@dataclass(frozen=True)
class Touched:
    """The changed files one test's discovery signal lands in, by signal.

    Kept apart rather than unioned so a lost kill can be attributed to the
    signal that failed to fire, which is the only way to tell "the baseline is
    wrong" from "one of its four parts is".
    """

    own_file: frozenset[str]
    called: frozenset[str]
    referenced: frozenset[str]
    imported: frozenset[str]
    name_match: frozenset[str]

    @property
    def all(self) -> frozenset[str]:
        return self.own_file | self.called | self.referenced | self.imported | self.name_match


def touched_files(corpus: Corpus, worktree: Path) -> dict[str, Touched]:
    """Per test id, the changed files its discovery signal touches.

    Re-parses each test module from the worktree because `DiscoveredTest.source`
    holds the test function alone, while imports are module-level — the same
    split `discovery.discover_tests` works with.
    """
    changed_paths = {file_change.path for file_change in corpus.change_set.files}
    by_file: dict[str, list] = {}
    for test in corpus.tests:
        by_file.setdefault(test.file, []).append(test)

    touched: dict[str, Touched] = {}
    for file, tests in by_file.items():
        module = _parse_module(worktree / file)
        imported = frozenset(
            path
            for stem in (_imported_module_stems(module) if module else frozenset())
            for path in corpus.stem_files.get(stem, ())
        )
        nodes = {item.name: item.node for item in _test_items(module)} if module else {}

        for test in tests:
            node = nodes.get(test.test_id.split("::")[-1])
            called_names = _names_called(node) if node is not None else frozenset()
            referenced_names = _names_referenced(node) if node is not None else frozenset()
            name = test.test_id.split("::")[-1]

            touched[test.test_id] = Touched(
                own_file=frozenset({test.file}) if test.file in changed_paths else frozenset(),
                called=_files_for(corpus, called_names),
                referenced=_files_for(corpus, referenced_names - called_names),
                imported=imported,
                name_match=_files_for(
                    corpus, {symbol for symbol in corpus.symbol_files if symbol in name}
                ),
            )
    return touched


def _files_for(corpus: Corpus, names) -> frozenset[str]:
    return frozenset(path for name in names for path in corpus.symbol_files.get(name, ()))


def _parse_module(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None


def keeps(defect: Defect, touched: Touched) -> bool:
    """Whether this filter keeps the pair.

    A defect naming no file is always kept: nothing is known about where it
    lives, so nothing about it can be excluded. `reachability.py` takes the same
    branch for the same reason.
    """
    if not defect.files:
        return True
    return bool(touched.all & defect.files)
