"""The four prompt variants: {no context, context} x {description, mutant code}.

- ``context`` adds what was being proposed: the commit message the change
  was made for, the file path, and the original implementation hunk.
- ``mutant`` replaces the defect description with the mutated code: the
  implementation hunk with the edit applied, and no description of the edit.

The same parts go to Jev (as a structured ``state``) and to Mini (as text), so
the two see identical content.

Run:  .venv/bin/python docs/experiments/jev/m52/prompts.py   (checks every case builds)
"""

from __future__ import annotations

import sys
from collections import Counter
from itertools import product

from acceptance.benchmark.mutants.labels import MutantCase

VARIANTS = [
    f"{ctx}+{form}" for ctx, form in product(("bare", "context"), ("description", "mutant"))
]

QUESTION = "Would this test fail when it runs against the code with the defect in place?"
QUESTION_MUTANT = "Would this test fail when it runs against the mutated code?"


class CannotBuild(ValueError):
    """The edit's original line cannot be located once in the hunk."""


def commit_message(case: MutantCase) -> str:
    """The commit message, without the diff that follows it."""
    return case.requirement_text.split("\n---\n", 1)[0].strip()


def mutated_hunk(case: MutantCase) -> str:
    """The implementation hunk with the edit applied, as a whole-line splice."""
    original = case.edit.original.splitlines()
    lines = case.implementation_hunk.splitlines()
    width = len(original)
    hits = [
        i
        for i in range(len(lines) - width + 1)
        if [ln.strip() for ln in lines[i : i + width]] == [o.strip() for o in original]
    ]
    if len(hits) != 1:
        raise CannotBuild(f"{case.case_id}: original found {len(hits)} times in the hunk")
    i = hits[0]
    indent = lines[i][: len(lines[i]) - len(lines[i].lstrip())]
    replacement = [
        indent + r.strip() if r.strip() else r for r in case.edit.replacement.splitlines()
    ]
    # Keep the replacement's own relative indentation beyond the first line.
    if len(case.edit.replacement.splitlines()) > 1:
        base = case.edit.original.splitlines()[0]
        base_indent = len(base) - len(base.lstrip())
        replacement = [
            indent + r[base_indent:] if r.strip() else r for r in case.edit.replacement.splitlines()
        ]
    return "\n".join(lines[:i] + replacement + lines[i + width :])


def parts(case: MutantCase, variant: str) -> dict[str, str]:
    """The named pieces of content a variant shows, in display order."""
    ctx, form = variant.split("+")
    out: dict[str, str] = {}
    if ctx == "context":
        out["change_request"] = commit_message(case)
        out["file"] = case.edit.path
        out["original_code"] = case.implementation_hunk
    out["test_source"] = case.test_source
    if form == "description":
        out["defect"] = case.defect_description
    else:
        out["mutated_code"] = mutated_hunk(case)
    return out


def question(variant: str) -> str:
    return QUESTION_MUTANT if variant.endswith("+mutant") else QUESTION


INTRO = {
    "bare+description": (
        "A test was written for some code. A small defect is then injected into that code."
    ),
    "bare+mutant": (
        "A test was written for some code. The code has since been mutated by one small "
        "mechanical edit; the mutated code is shown."
    ),
    "context+description": (
        "A developer made a change in response to a change request; the original code and the "
        "test are shown. A small defect is then injected into that code."
    ),
    "context+mutant": (
        "A developer made a change in response to a change request; the original code and the "
        "test are shown. The code has since been mutated by one small mechanical edit; the "
        "mutated code is shown too."
    ),
}

LABELS = {
    "change_request": "Change request",
    "file": "File",
    "original_code": "Original code",
    "test_source": "Test",
    "defect": "Defect",
    "mutated_code": "Mutated code",
}


def mini_messages(case: MutantCase, variant: str) -> list[dict[str, str]]:
    body = "\n\n".join(f"{LABELS[k]}:\n{v}" for k, v in parts(case, variant).items())
    return [
        {"role": "system", "content": "Answer with exactly one word: yes or no."},
        {"role": "user", "content": f"{INTRO[variant]}\n\n{body}\n\n{question(variant)}"},
    ]


def jev_body(case: MutantCase, variant: str) -> dict:
    return {
        "model": "jev-latest",
        "state": {"situation": INTRO[variant], **parts(case, variant)},
        "questions": {
            "fails": {
                "type": "noul",
                "instructions": question(variant),
                "criteria": {
                    "true": "Running the test against this code raises an error or fails an "
                    "assertion.",
                    "false": "The test still passes against this code.",
                },
            }
        },
    }


def main() -> int:
    from split import cases

    failures = Counter()
    for case in cases():
        try:
            mutated_hunk(case)
        except CannotBuild as exc:
            failures[str(exc).split(": ", 1)[1]] += 1
    total = len(cases())
    print(f"mutated code built for {total - sum(failures.values())} of {total} cases")
    for reason, n in failures.items():
        print(f"  {n}: {reason}")
    no_sep = sum("\n---\n" not in c.requirement_text for c in cases())
    print(f"cases with no diff separator in requirement_text: {no_sep}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
