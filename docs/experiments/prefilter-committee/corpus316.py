"""Build a pair-prefilter Corpus from the #316 review, digest-verified.

The #314 corpus is rebuilt from committed verdicts + two revisions; the #316
review carries everything directly: defects with code_refs, the change set, and
1053-per... no: 23,808 pair verdicts naming tests by node id with a sha256 of
each test's own source. Sources are re-extracted from the worktree by AST and
verified against that digest, so the corpus is exactly what the judge saw.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import paths

paths.on_path()

from corpus import Corpus, Defect, _regions, _symbol_and_stem_files

from acceptance.evidence.discovery import DiscoveredTest
from acceptance.review_state import ChangeSet


def _extract_source(path: Path, test_id: str) -> str | None:
    """The test function's own source, as DiscoveredTest carries it."""
    parts = test_id.split("::")[1:]
    try:
        text = path.read_text()
        tree = ast.parse(text)
    except (OSError, SyntaxError, UnicodeDecodeError):
        # Unreadable or not parseable Python. Returning None fails the digest
        # check below, which is the point: `load` refuses the whole corpus
        # rather than quietly scoring a test whose source it could not recover.
        return None
    body = tree.body
    for i, name in enumerate(parts):
        found = None
        for node in body:
            if (
                isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
                and node.name == name
            ):
                found = node
                break
        if found is None:
            return None
        if i == len(parts) - 1:
            # Match discovery._node_source exactly: lineno..end_lineno, joined
            # with "\n", decorators excluded (lineno is the def line).
            lines = text.splitlines()
            end = getattr(found, "end_lineno", found.lineno)
            return "\n".join(lines[found.lineno - 1 : end])
        body = found.body
    return None


def load() -> Corpus:
    worktree = paths.head316()
    d = json.loads(paths.review316().read_text())
    change_set = ChangeSet.model_validate(d["change_set"])

    defects = []
    for ds in d["defect_sets"]:
        for df in ds["defects"]:
            defects.append(
                Defect(
                    id=df["id"],
                    obligation_id=df["obligation_id"],
                    type=df["type"],
                    description=df["description"],
                    code_refs=tuple(df["code_refs"]),
                )
            )

    verdicts = d["pair_verdicts"]
    judged = tuple((v["defect_id"], v["test_id"]) for v in verdicts)
    kills = frozenset(p for p, v in zip(judged, verdicts) if v["kills"])

    digests = {}
    for v in verdicts:
        digests[v["test_id"]] = v["test_digest"]

    tests, mismatched = [], []
    for test_id, digest in sorted(digests.items()):
        file = test_id.split("::", 1)[0]
        source = _extract_source(worktree / file, test_id)
        got = hashlib.sha256((source or "").encode()).hexdigest()
        if got != digest:
            mismatched.append(test_id)
            continue
        tests.append(DiscoveredTest(test_id=test_id, file=file, source=source or ""))
    if mismatched:
        raise SystemExit(
            f"{len(mismatched)} of {len(digests)} test sources fail digest check, "
            f"e.g. {mismatched[:3]} — worktree does not match the reviewed revision"
        )

    judged_defect_ids = {v["defect_id"] for v in verdicts}
    defects = [df for df in defects if df.id in judged_defect_ids]
    symbol_files, stem_files = _symbol_and_stem_files(worktree, change_set)

    return Corpus(
        base_revision=d["change_set"].get("base_revision", ""),
        head_revision=d["reviewed_revision"],
        run_id="316-gate2",
        defects=tuple(defects),
        tests=tuple(tests),
        change_set=change_set,
        kills=kills,
        judged=judged,
        symbol_files=symbol_files,
        stem_files=stem_files,
        regions=_regions(change_set),
    )


if __name__ == "__main__":
    corpus = load()
    print(
        f"corpus: {len(corpus.defects)} defects x {len(corpus.tests)} tests = "
        f"{len(corpus.judged)} pairs, {len(corpus.kills)} kills"
    )
    print(
        f"regions named by defects: "
        f"{len({r for df in corpus.defects for r in df.code_refs if r in corpus.regions})}"
    )
