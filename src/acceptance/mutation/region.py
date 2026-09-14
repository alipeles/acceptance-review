"""Where a named defect is allowed to be injected.

A `Defect` cites its `code_refs` as `path#hunk` labels — the changed regions a
reader would have to inspect to tell whether the defect is present. This module
turns those labels into concrete line spans at head, which is what makes
DR-171 Decision 3's third validity check enforceable: the edit must land inside
a region the defect itself named, so a mutant cannot wander into unrelated code
and a red test cannot be credited to the wrong defect.

The span comes from the hunk's *new* side, because the mutation is applied to
the file as delivered, not as it was before the change.
"""

from __future__ import annotations

from acceptance.coverage.prompt import hunk_label
from acceptance.model_base import PersistableModel as _Model
from acceptance.review_state import ChangeSet, Defect

__all__ = ["Region", "regions_for"]


class Region(_Model):
    """One `path#hunk` label resolved to a line span in the file at head.

    `start_line` and `end_line` are 1-based and inclusive, matching how a diff
    hunk header counts and how a person reads a file.
    """

    label: str
    path: str
    start_line: int
    end_line: int

    def contains(self, start_line: int, end_line: int) -> bool:
        return self.start_line <= start_line and end_line <= self.end_line


def regions_for(defect: Defect, change_set: ChangeSet) -> list[Region]:
    """The regions `defect` named, resolved against `change_set`.

    A label naming no region in this change set is dropped rather than reported
    as absent. The caller sees a defect with fewer regions than labels, and a
    defect left with none is not mutable — which is the honest answer, since
    there is nowhere the edit would be allowed to land.

    A hunk that only deletes lines (`new_lines == 0`) yields no region for the
    same reason: there is no text at head to replace.
    """
    wanted = set(defect.code_refs)
    regions: list[Region] = []
    for file_change in change_set.files:
        for index, hunk in enumerate(file_change.hunks):
            label = hunk_label(file_change.path, index)
            if label not in wanted or hunk.new_lines <= 0:
                continue
            regions.append(
                Region(
                    label=label,
                    path=file_change.path,
                    start_line=hunk.new_start,
                    end_line=hunk.new_start + hunk.new_lines - 1,
                )
            )
    return regions
