"""Executed kill/survive labels for "would this test fail under this defect?" (#372).

Every label here comes from running a test against a mechanical edit, never
from a model. The edit *is* the defect: a fixed operator (flip a comparison,
change a constant) applied to one span of the code a real BugsInPy fix changed,
so the description can never claim more than was injected. That is the whole
reason the set exists — the checker's own mutation tier lets a model write the
edit, and DR-171's audits found only 52–60% of those introduced the defect they
named, which would make roughly 40% of its labels noise.

One case is one (edit, test) pair. The fields are the ones #371's experiment
hands a judge: the requirement the test is meant to check, the test's source,
the implementation hunk the edit landed in, the edit's description and exact
text, and the observed outcome.

**Nothing built from BugsInPy is committed.** BugsInPy declares no license and
this repository is public, so per DR-168 a label set lives only under the
gitignored `.acceptance/mutant-labels/` and is rebuilt from the pinned bug list.
The loader is tested on a synthetic fixture for the same reason.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from acceptance.model_base import PersistableModel

__all__ = [
    "MutantCase",
    "MutantEdit",
    "MutantLabelSet",
    "SetAsideMutant",
    "SetAsideTestRecord",
    "SkippedBug",
    "SurvivorCheck",
    "SurvivorSample",
    "load_mutant_labels",
    "load_survivor_sample",
]

#: Where a case came from. One value today; kept as a field so a second source
#: (the #45 audit edits, dropped from #372 at Gate 1) can be added and scored
#: separately without reshaping the file.
CaseSource = Literal["bugsinpy-operator"]


class MutantEdit(PersistableModel):
    """The exact text replaced, and where.

    `original` and `replacement` are whole lines, `start_line`..`end_line`
    inclusive and 1-based, so applying the edit is a line splice and reading it
    needs no column arithmetic.
    """

    path: str
    start_line: int
    end_line: int
    original: str
    replacement: str
    operator: str

    @model_validator(mode="after")
    def _is_an_edit(self) -> MutantEdit:
        if self.start_line < 1 or self.end_line < self.start_line:
            raise ValueError(f"line range {self.start_line}-{self.end_line} is not a range")
        if self.original == self.replacement:
            raise ValueError("an edit that replaces text with itself injects nothing")
        return self


class MutantCase(PersistableModel):
    """One test observed against one injected edit."""

    case_id: str
    source: CaseSource
    project: str
    bug_id: int
    fixed_commit: str
    requirement_text: str
    test_id: str
    test_source: str
    implementation_hunk: str
    defect_description: str
    edit: MutantEdit
    killed: bool


class SetAsideMutant(PersistableModel):
    """An edit that produced no label, and why — never silently dropped."""

    project: str
    bug_id: int
    edit: MutantEdit
    reason: str


class SetAsideTestRecord(PersistableModel):
    """A selected test that took part in no label, and why.

    Mirrors `mutation.baseline.SetAsideTest` in the fields a reader of the label
    file needs, without importing the checker's review-state types into it.
    """

    project: str
    bug_id: int
    test_id: str
    kind: str
    reason: str


class SkippedBug(PersistableModel):
    """A pinned bug that yielded no case at all, and why."""

    bug: str
    reason: str


class MutantLabelSet(PersistableModel):
    """A whole build: the cases, and everything that was tried and set aside.

    `bugsinpy_commit` and `bugs` are the pinned inputs; rebuilding from the same
    pair must reproduce this file byte for byte.
    """

    bugsinpy_commit: str
    bugs: list[str]
    cases: list[MutantCase] = Field(default_factory=list)
    set_aside_tests: list[SetAsideTestRecord] = Field(default_factory=list)
    set_aside_mutants: list[SetAsideMutant] = Field(default_factory=list)
    skipped_bugs: list[SkippedBug] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ids_are_unique(self) -> MutantLabelSet:
        seen: set[str] = set()
        for case in self.cases:
            if case.case_id in seen:
                raise ValueError(f"case id {case.case_id!r} appears twice")
            seen.add(case.case_id)
        return self


class SurvivorCheck(PersistableModel):
    """One sampled survivor, as a person fills it in.

    `changes_behaviour` starts `None` (not yet checked). `True` means the edit
    alters what the code does, so the surviving test genuinely missed it;
    `False` means the edit is equivalent to the original, so the survival says
    nothing about the test.
    """

    case_id: str
    changes_behaviour: bool | None = None
    note: str = ""


class SurvivorSample(PersistableModel):
    """The random sample of survivors drawn for a person to check."""

    seed: int
    population: int
    checks: list[SurvivorCheck]


def load_mutant_labels(path: Path) -> MutantLabelSet:
    """Read a label file written by the build, validating it on the way in."""
    return MutantLabelSet.from_dict(json.loads(path.read_text(encoding="utf-8")))


def load_survivor_sample(path: Path) -> SurvivorSample:
    return SurvivorSample.from_dict(json.loads(path.read_text(encoding="utf-8")))
