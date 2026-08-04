"""Persisted review-state store (M0.6).

The CLAUDE.md invariant is that review state is structured and persisted, not
an unstructured transcript — and that the store exists early so later
components write into it rather than inventing their own persistence. This is
that store: it writes a Review to disk in the canonical byte-stable form
(serialization.py) and reads it back, keyed by the reviewed revision so a
re-run against the same head overwrites in place (the incremental-rerun
scenario, M7.5).
"""

from __future__ import annotations

import json
from pathlib import Path

from acceptance.review_state import Review

DEFAULT_REVIEW_ROOT = Path(".acceptance/cache/reviews")


class ReviewStore:
    def __init__(self, root: Path | str = DEFAULT_REVIEW_ROOT) -> None:
        self.root = Path(root)

    def path_for(self, reviewed_revision: str) -> Path:
        return self.root / f"{reviewed_revision}.json"

    def write(self, review: Review) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.path_for(review.reviewed_revision)
        path.write_text(review.to_canonical_json() + "\n")
        return path

    def read(self, reviewed_revision: str) -> Review | None:
        path = self.path_for(reviewed_revision)
        if not path.is_file():
            return None
        return Review.from_dict(json.loads(path.read_text()))

    def latest(self) -> Review | None:
        """The most recently written review, or None when the store is empty.

        Keyed on the file's own mtime rather than anything inside the review:
        reviews are keyed by revision, and revisions carry no order the store
        can see — a re-run against an older head is legitimately the newest
        review. What a caller who names no review means is "the one I just
        produced", which is exactly write order (M7.3.r1).
        """
        paths = [path for path in self.root.glob("*.json") if path.is_file()]
        if not paths:
            return None
        newest = max(paths, key=lambda path: path.stat().st_mtime)
        return Review.from_dict(json.loads(newest.read_text()))
