"""Sandboxed execution of a named subset of a project's tests (§8.3, §17).

The tier above static inference is reached only by observing a test run, never
by predicting one (`docs/DR-170-feasibility-probe.md`, Decision 1). This package
is where that observation happens, which makes its two safety properties — no
network reachable from a test, and a time budget that stops the run — the only
rail between the review and someone else's repository.

Nothing here elevates an evidence tier. Choosing which tests to run belongs to
the feasibility probe (M8.1) and reading a coverage map belongs to the
coverage-confirmed tier (M8.3); this package runs what it is given and reports
what happened.
"""

from __future__ import annotations

from acceptance.execution.outcome import (
    COMPLETED_KINDS,
    SandboxRunResult,
    TestOutcome,
    TestOutcomeKind,
)
from acceptance.execution.sandbox import SandboxConfig, run_tests

__all__ = [
    "COMPLETED_KINDS",
    "SandboxConfig",
    "SandboxRunResult",
    "TestOutcome",
    "TestOutcomeKind",
    "run_tests",
]
