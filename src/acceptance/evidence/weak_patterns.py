"""Weak-evidence pattern detectors (M5.4, §9.4).

Names the six §9.4 anti-patterns wherever a test exhibits them. Structural,
no model call — three patterns are new AST shape-matching over a test's raw
source (`DiscoveredTest.source`); the other three are already computed by
M5.1-M5.3 and just need relabeling:

- CIRCULAR_EXPECTED_VALUE      <- M5.1's expected_value_provenance ("Circular...")
- REQUIREMENT_NOT_EXERCISED    <- M5.3 nominal (no defect caught), no mocks
                                   involved: the INPUT itself fails to
                                   discriminate (§9.4's calendar-aligned-dates
                                   example, archetype #4's shape)
- CRITICAL_BEHAVIOR_MOCKED     <- M5.3 nominal, WITH mocks involved: the
                                   behavior under review was bypassed
                                   (§9.4's rate-selection example, archetype
                                   #6's shape)

Mocks-present is the mechanical signal that distinguishes the latter two — a
nominal test that mocked nothing failed to discriminate because its INPUT
happened to coincide with a plausible defect; a nominal test that mocked the
behavior under review never exercised it at all. Both still nominally_supported
in M5.3; §9.4 wants the reader to know *why*.

New structural detection (over `DiscoveredTest.source`):
- NON_DISCRIMINATING_ASSERTION: `assert x is not None` / a bare truthy check —
  establishes only that *something* was returned, not that it was CORRECT.
- INCOMPLETE_ERROR_ASSERTION: `pytest.raises(Exception)` (too broad — matches
  almost any failure) or a raises-block with no assertion on the exception
  itself (type, message, or attributes).
- UNVALIDATED_SNAPSHOT: an assertion compares against something *named* like a
  stored/golden artifact (snapshot/golden/approved/expected-file) rather than
  an independently-derived value — a name heuristic, the same spirit as
  extraction.py's `_MOCK_NAMES`.

This is a reporting/advisory layer (feeds §9.5 recommendations, M7 territory)
— not wired into classify_case/scoring, same scope boundary as M5.1.
"""

from __future__ import annotations

import ast
from enum import Enum

from acceptance.evidence.discovery import DiscoveredTest
from acceptance.evidence.discrimination import ObligationDiscrimination
from acceptance.evidence.extraction import parse_test_function
from acceptance.model_base import PersistableModel
from acceptance.review_state import TestEvidence

_SNAPSHOT_NAME_MARKERS = ("snapshot", "golden", "approved")


class WeakEvidencePattern(str, Enum):
    NON_DISCRIMINATING_ASSERTION = "non_discriminating_assertion"
    CIRCULAR_EXPECTED_VALUE = "circular_expected_value"
    INCOMPLETE_ERROR_ASSERTION = "incomplete_error_assertion"
    REQUIREMENT_NOT_EXERCISED = "requirement_not_exercised"
    CRITICAL_BEHAVIOR_MOCKED = "critical_behavior_mocked"
    UNVALIDATED_SNAPSHOT = "unvalidated_snapshot"


class WeakEvidenceFinding(PersistableModel):
    test_id: str
    pattern: WeakEvidencePattern
    description: str


def _non_discriminating_assertion(func: ast.AST) -> str | None:
    for node in ast.walk(func):
        if not isinstance(node, ast.Assert):
            continue
        test = node.test
        # `assert x is not None` / `assert x is not False` etc.
        if (
            isinstance(test, ast.Compare)
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.IsNot)
        ):
            return ast.unparse(node)
        # `assert x` / `assert isinstance(x, T)` — no comparison to a specific
        # expected value, only a truthy/type check.
        if isinstance(test, ast.Call) and _call_name(test) == "isinstance":
            return ast.unparse(node)
        if isinstance(test, (ast.Name, ast.Attribute, ast.Call)):
            return ast.unparse(node)
    return None


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _incomplete_error_assertion(func: ast.AST) -> str | None:
    """A `pytest.raises` block whose exception type is too broad to mean
    anything, or whose exception is never inspected afterward. The exception
    is commonly checked in the statements AFTER the `with` block exits (not
    inside it) — a valid, common pytest style — so both are searched."""
    for body in _statement_lists(func):
        for i, node in enumerate(body):
            if not isinstance(node, ast.With):
                continue
            for item in node.items:
                call = item.context_expr
                if not (isinstance(call, ast.Call) and _call_name(call) == "raises"):
                    continue
                exc_type = ast.unparse(call.args[0]) if call.args else ""
                too_broad = exc_type in ("Exception", "BaseException")
                checks_exception = item.optional_vars is not None and (
                    _references(node.body, item.optional_vars)
                    or _references(body[i + 1 :], item.optional_vars)
                )
                if too_broad or not checks_exception:
                    return ast.unparse(node).splitlines()[0]
    return None


def _statement_lists(func: ast.AST) -> list[list[ast.stmt]]:
    """Every statement-list (function/if/for/while/with body, ...) in `func`,
    so callers can inspect a node's SIBLINGS, not just its descendants —
    `ast.walk` alone loses that structural context."""
    lists: list[list[ast.stmt]] = []

    def visit(node: ast.AST) -> None:
        for field in ("body", "orelse", "finalbody"):
            block = getattr(node, field, None)
            if isinstance(block, list) and block and isinstance(block[0], ast.stmt):
                lists.append(block)
                for stmt in block:
                    visit(stmt)

    visit(func)
    return lists


def _references(stmts: list[ast.stmt], target: ast.expr) -> bool:
    if not isinstance(target, ast.Name):
        return False
    for stmt in stmts:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Name) and node.id == target.id:
                return True
    return False


def _unvalidated_snapshot(func: ast.AST) -> str | None:
    for node in ast.walk(func):
        if not isinstance(node, ast.Assert) or not isinstance(node.test, ast.Compare):
            continue
        operands = [node.test.left, *node.test.comparators]
        for operand in operands:
            name = _operand_name(operand)
            if name and any(marker in name.lower() for marker in _SNAPSHOT_NAME_MARKERS):
                return ast.unparse(node)
    return None


def _operand_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _call_name(node)
    return None


def _from_test_evidence(evidence: TestEvidence) -> list[WeakEvidenceFinding]:
    findings = []
    if evidence.expected_value_provenance and evidence.expected_value_provenance.startswith(
        "Circular"
    ):
        findings.append(
            WeakEvidenceFinding(
                test_id=evidence.identifier,
                pattern=WeakEvidencePattern.CIRCULAR_EXPECTED_VALUE,
                description=evidence.expected_value_provenance,
            )
        )
    return findings


def _from_discrimination(
    evidence: TestEvidence, discriminations_by_obligation: dict[str, ObligationDiscrimination]
) -> list[WeakEvidenceFinding]:
    findings = []
    for obligation_id in evidence.mapped_obligations:
        discrimination = discriminations_by_obligation.get(obligation_id)
        if discrimination is None or not discrimination.defects:
            continue
        if any(d.would_be_caught for d in discrimination.defects):
            continue  # not nominal — some defect is caught
        if evidence.mocks:
            findings.append(
                WeakEvidenceFinding(
                    test_id=evidence.identifier,
                    pattern=WeakEvidencePattern.CRITICAL_BEHAVIOR_MOCKED,
                    description=(
                        f"Mocks {', '.join(sorted(evidence.mocks))} while claiming to "
                        f"establish {obligation_id}; every plausible defect survives."
                    ),
                )
            )
        else:
            findings.append(
                WeakEvidenceFinding(
                    test_id=evidence.identifier,
                    pattern=WeakEvidencePattern.REQUIREMENT_NOT_EXERCISED,
                    description=(
                        f"The test's inputs do not distinguish {obligation_id} from a "
                        f"plausible defect; every mapped defect survives."
                    ),
                )
            )
    return findings


def _from_source(test: DiscoveredTest) -> list[WeakEvidenceFinding]:
    func = parse_test_function(test.source)
    if func is None:
        return []
    findings = []
    if match := _non_discriminating_assertion(func):
        findings.append(
            WeakEvidenceFinding(
                test_id=test.test_id,
                pattern=WeakEvidencePattern.NON_DISCRIMINATING_ASSERTION,
                description=f"Establishes only that a value was returned, not that it was correct: `{match}`.",
            )
        )
    if match := _incomplete_error_assertion(func):
        findings.append(
            WeakEvidenceFinding(
                test_id=test.test_id,
                pattern=WeakEvidencePattern.INCOMPLETE_ERROR_ASSERTION,
                description=(f"Does not establish the error type, message, or content: `{match}`."),
            )
        )
    if match := _unvalidated_snapshot(func):
        findings.append(
            WeakEvidenceFinding(
                test_id=test.test_id,
                pattern=WeakEvidencePattern.UNVALIDATED_SNAPSHOT,
                description=(
                    f"Confirms output is unchanged with no evidence the stored value "
                    f"was correct: `{match}`."
                ),
            )
        )
    return findings


def detect_weak_patterns(
    discovered_tests: list[DiscoveredTest],
    test_evidence: list[TestEvidence],
    discriminations: list[ObligationDiscrimination],
) -> list[WeakEvidenceFinding]:
    """Flag each §9.4 weak-evidence pattern a test exhibits."""
    discriminations_by_obligation = {d.obligation_id: d for d in discriminations}
    findings: list[WeakEvidenceFinding] = []

    for evidence in test_evidence:
        findings.extend(_from_test_evidence(evidence))
        findings.extend(_from_discrimination(evidence, discriminations_by_obligation))

    for test in discovered_tests:
        findings.extend(_from_source(test))

    return findings
