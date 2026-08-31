"""Reassemble #314's Gate 2 pair run into the inputs a prefilter would see.

Everything here is offline. The 12,450 recorded verdicts come from the committed
`verdicts.json.gz`; the change set and the 166 candidate tests are re-derived
from the two revisions with **no model call**, using the product's own
`extract_change_set` and `discover_tests` so the experiment measures what the
pipeline would actually have been handed.

Run it directly for a survey of what the corpus holds. Every experiment on this
data should start with that, exactly as `obligation-dedup/linking_corpus.py`
does for the linking stage.

## Why a worktree

`discover_tests` reads the working tree, not git blobs, so the tests must be
read at the reviewed head rather than at whatever is checked out now. Point
`--worktree` at a checkout of the head revision:

    git worktree add --detach ../314-prefilter-head 2945551

## The trap this module exists to close

The recorded verdicts name tests by pytest node id. If discovery here produces
an id the verdicts do not carry, that test's pairs silently vanish from every
score and each filter looks better than it is. `load()` therefore refuses to
return a corpus whose derived test ids do not match the recorded ones exactly.
"""

from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from acceptance.change.context import changed_definitions
from acceptance.change.diff import extract_change_set
from acceptance.coverage.prompt import hunk_label
from acceptance.evidence.discovery import DiscoveredTest, discover_tests
from acceptance.review_state import ChangeSet

HERE = Path(__file__).resolve().parent
VERDICTS = HERE / "verdicts.json.gz"


@dataclass(frozen=True)
class Defect:
    """One recorded way of failing, as the pair stage was given it."""

    id: str
    obligation_id: str
    type: str
    description: str
    code_refs: tuple[str, ...]

    @property
    def files(self) -> frozenset[str]:
        """The files the defect's `path#hunk` refs name.

        Matches `reachability._implicated_files`, deliberately: the free
        baseline is measured against the same notion of "the defect's own file"
        that the shipped prefilter uses.
        """
        return frozenset(ref.split("#", 1)[0] for ref in self.code_refs if ref)


@dataclass(frozen=True)
class Corpus:
    base_revision: str
    head_revision: str
    run_id: str
    defects: tuple[Defect, ...]
    tests: tuple[DiscoveredTest, ...]
    change_set: ChangeSet
    kills: frozenset[tuple[str, str]]
    judged: tuple[tuple[str, str], ...]
    #: Every changed symbol name, mapped to the files whose changed definitions
    #: introduce it. This is what discovery matched on, re-derived with the file
    #: it came from — discovery itself records only *that* a name matched.
    symbol_files: dict[str, frozenset[str]]
    #: Each changed module stem mapped to the files carrying it, same idea.
    stem_files: dict[str, frozenset[str]]
    #: `path#hunk` label -> that hunk's diff content.
    regions: dict[str, str]

    @property
    def defects_by_id(self) -> dict[str, Defect]:
        return {defect.id: defect for defect in self.defects}

    @property
    def tests_by_id(self) -> dict[str, DiscoveredTest]:
        return {test.test_id: test for test in self.tests}


def _read_verdicts() -> dict:
    with gzip.open(VERDICTS, "rt") as handle:
        return json.load(handle)


def _regions(change_set: ChangeSet) -> dict[str, str]:
    return {
        hunk_label(file_change.path, index): hunk.content
        for file_change in change_set.files
        for index, hunk in enumerate(file_change.hunks)
    }


def _symbol_and_stem_files(repo: Path, change_set: ChangeSet) -> tuple[dict, dict]:
    """Rebuild discovery's two match keys, keeping the file each came from.

    `discovery._changed_symbol_names` folds every changed definition into one
    flat set of names, and `_changed_module_stems` does the same for module
    stems. That is all discovery needs — it only asks whether a test matched
    *anything*. The free baseline asks the sharper question of whether the
    match lands in the defect's own file, so the provenance has to be kept.
    """
    symbol_files: dict[str, set[str]] = {}
    for definition in changed_definitions(repo, change_set):
        name = definition.qualname.rsplit(".", 1)[-1]
        symbol_files.setdefault(name, set()).add(definition.file)

    stem_files: dict[str, set[str]] = {}
    for file_change in change_set.files:
        if file_change.path.endswith(".py"):
            stem = Path(file_change.path).stem
            stem_files.setdefault(stem, set()).add(file_change.path)

    return (
        {name: frozenset(files) for name, files in symbol_files.items()},
        {stem: frozenset(files) for stem, files in stem_files.items()},
    )


def load(worktree: Path) -> Corpus:
    """The corpus, with the derived test set checked against the recorded one."""
    data = _read_verdicts()
    base, head = data["base_revision"], data["head_revision"]

    # The mandate file is ignored, as every review ignores it: `run_review` passes
    # the task path as an extra ignore pattern. Without this the derived change
    # set carries one file the judged run did not see. It is inert here — no
    # defect refs it and discovery reads only Python — but a corpus that differs
    # from the judged run in any way invites a reader to wonder where else.
    change_set = extract_change_set(worktree, base, head, extra_ignore_patterns=["current-task.md"])
    discovered = discover_tests(worktree, change_set)

    recorded_ids = {verdict["test_id"] for verdict in data["verdicts"]}
    derived_ids = {test.test_id for test in discovered.tests}
    if derived_ids != recorded_ids:
        missing = sorted(recorded_ids - derived_ids)[:5]
        extra = sorted(derived_ids - recorded_ids)[:5]
        raise SystemExit(
            f"discovery at {worktree} produced {len(derived_ids)} tests but the recorded "
            f"verdicts name {len(recorded_ids)}. Every score would be computed over a "
            f"different test set than the one judged.\n"
            f"  recorded but not derived (first 5): {missing}\n"
            f"  derived but not recorded (first 5): {extra}\n"
            f"Check the worktree is at {head}."
        )

    symbol_files, stem_files = _symbol_and_stem_files(worktree, change_set)

    return Corpus(
        base_revision=base,
        head_revision=head,
        run_id=data["run_id"],
        defects=tuple(
            Defect(
                id=record["id"],
                obligation_id=record["obligation_id"],
                type=record["type"],
                description=record["description"],
                code_refs=tuple(record["code_refs"]),
            )
            for record in sorted(data["defects"], key=lambda r: r["id"])
        ),
        tests=tuple(discovered.tests),
        change_set=change_set,
        kills=frozenset(
            (verdict["defect_id"], verdict["test_id"])
            for verdict in data["verdicts"]
            if verdict["kills"]
        ),
        judged=tuple(
            sorted((verdict["defect_id"], verdict["test_id"]) for verdict in data["verdicts"])
        ),
        symbol_files=symbol_files,
        stem_files=stem_files,
        regions=_regions(change_set),
    )


def _survey(corpus: Corpus) -> None:
    print(f"run {corpus.run_id}, {corpus.base_revision[:8]}..{corpus.head_revision[:8]}")
    print(f"{len(corpus.defects)} defects x {len(corpus.tests)} tests = {len(corpus.judged)} pairs")
    print(f"{len(corpus.kills)} kills ({100 * len(corpus.kills) / len(corpus.judged):.2f}%)")

    print(f"\ndefect types: {dict(Counter(d.type for d in corpus.defects))}")
    print(f"defects with no code refs: {sum(1 for d in corpus.defects if not d.files)}")
    print(f"changed files: {len(corpus.change_set.files)}, hunk regions: {len(corpus.regions)}")
    print(f"changed symbol names: {len(corpus.symbol_files)}")

    per_defect = Counter(defect_id for defect_id, _ in corpus.kills)
    print(f"\ndefects with at least one kill: {len(per_defect)} of {len(corpus.defects)}")
    print(f"most kills on one defect: {max(per_defect.values())}")
    per_test = Counter(test_id for _, test_id in corpus.kills)
    print(f"tests killing at least one defect: {len(per_test)} of {len(corpus.tests)}")

    empty = [t.test_id for t in corpus.tests if not t.source.strip()]
    print(f"tests with empty source: {len(empty)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--worktree",
        type=Path,
        required=True,
        help="a checkout of the reviewed head revision",
    )
    _survey(load(parser.parse_args().worktree.resolve()))


if __name__ == "__main__":
    main()
