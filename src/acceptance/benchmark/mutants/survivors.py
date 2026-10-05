"""The survivor spot-check and the aggregate report for a label set (#372).

A survivor is a case whose test passed with the edit in place. Most mean the
test missed a real change, but an edit can also be equivalent to the original
(`x + 0`, a constant nothing reads), and then the survival says nothing about
the test. A person checks a seeded random sample; the report gives the sample
size and the share that turned out to change no behaviour.

The report holds only counts and rates, so it is the one output of a build that
may be committed (DR-168).
"""

from __future__ import annotations

import random
from collections import Counter

from acceptance.benchmark.mutants.labels import (
    MutantCase,
    MutantLabelSet,
    SurvivorCheck,
    SurvivorSample,
)

__all__ = ["draw_survivor_sample", "render_sample", "summarise"]


def draw_survivor_sample(labels: MutantLabelSet, size: int, seed: int) -> SurvivorSample:
    """A seeded random sample of survivors, one per edit.

    One per edit, not per case: several tests survive the same edit, and whether
    the edit changes behaviour is a property of the edit, so sampling cases
    would spend the person's time judging one edit several times.
    """
    by_edit: dict[tuple, MutantCase] = {}
    for case in labels.cases:
        if not case.killed:
            by_edit.setdefault(_edit_key(case), case)
    population = sorted(by_edit.values(), key=lambda c: c.case_id)
    chosen = random.Random(seed).sample(population, min(size, len(population)))
    return SurvivorSample(
        seed=seed,
        population=len(population),
        checks=[SurvivorCheck(case_id=c.case_id) for c in sorted(chosen, key=lambda c: c.case_id)],
    )


def render_sample(labels: MutantLabelSet, sample: SurvivorSample) -> str:
    """The sample as a page a person can read without opening the label file."""
    cases = {c.case_id: c for c in labels.cases}
    parts = [
        "# Survivor spot-check",
        "",
        "For each edit below, decide one thing: **does the edited code behave differently",
        "from the original for some input?** Set `changes_behaviour` in",
        "`survivor-sample.json` to `true` (it does, so the test really missed it) or",
        "`false` (the edit is equivalent, so the survival says nothing about the test).",
        "",
    ]
    for number, check in enumerate(sample.checks, 1):
        case = cases[check.case_id]
        parts += [
            f"## {number}. `{check.case_id}`",
            "",
            case.defect_description,
            "",
            "```diff",
            f"- {case.edit.original}",
            f"+ {case.edit.replacement}",
            "```",
            "",
            "The code it sits in:",
            "",
            "```python",
            case.implementation_hunk,
            "```",
            "",
        ]
    return "\n".join(parts)


def summarise(labels: MutantLabelSet, sample: SurvivorSample | None = None) -> dict:
    """Counts and rates only — nothing derived from BugsInPy's content."""
    cases = labels.cases
    killed = sum(c.killed for c in cases)
    per_project: dict[str, dict[str, int]] = {}
    for project, count in sorted(Counter(c.project for c in cases).items()):
        project_killed = sum(c.killed for c in cases if c.project == project)
        per_project[project] = {
            "cases": count,
            "killed": project_killed,
            "survived": count - project_killed,
        }
    summary: dict = {
        "bugsinpy_commit": labels.bugsinpy_commit,
        "pinned_bugs": len(labels.bugs),
        "bugs_with_cases": len({(c.project, c.bug_id) for c in cases}),
        "skipped_bugs": len(labels.skipped_bugs),
        "edits": len({_edit_key(c) for c in cases}),
        "cases": len(cases),
        "killed": killed,
        "survived": len(cases) - killed,
        "killed_share": _share(killed, len(cases)),
        "survived_share": _share(len(cases) - killed, len(cases)),
        "per_project": per_project,
        "operators": dict(sorted(Counter(c.edit.operator for c in cases).items())),
        "set_aside_tests": len(labels.set_aside_tests),
        "set_aside_mutants": len(labels.set_aside_mutants),
    }
    if sample is not None:
        judged = [c for c in sample.checks if c.changes_behaviour is not None]
        unchanged = sum(1 for c in judged if c.changes_behaviour is False)
        summary["survivor_check"] = {
            "population": sample.population,
            "sample_size": len(sample.checks),
            "checked": len(judged),
            "no_behaviour_change": unchanged,
            "no_behaviour_change_share": _share(unchanged, len(judged)),
        }
    return summary


def _edit_key(case: MutantCase) -> tuple:
    return (case.project, case.bug_id, case.edit.path, case.edit.start_line, case.edit.replacement)


def _share(part: int, whole: int) -> float | None:
    return round(part / whole, 4) if whole else None
