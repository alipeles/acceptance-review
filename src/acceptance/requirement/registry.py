"""The requirement registry (M1.2.r1, DR-202 decision 4).

Turns a `ParsedTaskFile` into the identified list of requirements the
decomposer is asked to account for. The list comes from `markdown-it` via
`parse_task_file`, never from the model: the work list has to be built by
something other than the attention pass whose recall is the defect, or a
requirement the model failed to read is also a requirement it never has to
report on.

Ids are `section + ordinal` in parse order, zero-padded so that lexical order
is document order. See `RequirementRef` for why this interim scheme was chosen
over a content hash, and #209 for the semantic aligner that would give
requirement identity ACROSS task-file versions.
"""

from __future__ import annotations

from acceptance.requirement.task_file import ParsedTaskFile
from acceptance.review_state import RequirementRef, RequirementSection
from acceptance.source_ref import TextSpan

__all__ = ["build_registry", "requirement_id"]


def requirement_id(section: RequirementSection, ordinal: int) -> str:
    """The id for one requirement. Zero-padded to two digits so ids sort in
    document order; a task file with more than 99 bullets in one section simply
    gets a wider field rather than an id that sorts wrongly."""
    if section is RequirementSection.TASK:
        return section.value
    return f"{section.value}-{ordinal:02d}"


def build_registry(parsed: ParsedTaskFile) -> list[RequirementRef]:
    """Every requirement in the task file, identified, in document order.

    Section order is fixed here rather than taken from the file, so two task
    files with the same bullets in differently-ordered sections produce the same
    ids. `parse_task_file` already normalizes the sections themselves.
    """
    registry: list[RequirementRef] = []

    if parsed.behavior is not None:
        registry.append(_ref(RequirementSection.TASK, 1, parsed.behavior))

    for section, spans in (
        (RequirementSection.CONSTRAINT, parsed.constraints),
        (RequirementSection.EXCLUSION, parsed.scope_exclusions),
        (RequirementSection.COMPLETION, parsed.completion_expectations),
    ):
        for ordinal, span in enumerate(spans, start=1):
            registry.append(_ref(section, ordinal, span))

    return registry


def _ref(section: RequirementSection, ordinal: int, span: TextSpan) -> RequirementRef:
    return RequirementRef(
        id=requirement_id(section, ordinal),
        section=section,
        ordinal=ordinal,
        span=span,
    )
