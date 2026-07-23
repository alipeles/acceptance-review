"""M3.1 acceptance: archetype #1 -> missing instruction classified Not
addressed; #2 -> missing qualifier classified Partially addressed; both link to
exact code or record "no corresponding change".

Classification is a schema-constrained model call; per the replay-first
invariant these tests inject the recorded response (a hand-authored fixture)
via completion_fn — no live calls. The response is what a good model returns;
the test verifies the pipeline turns it into ImplementationCoverage with real
diff-region links. Classification *accuracy* is measured by the benchmark (M3.3).
"""

from pathlib import Path

from acceptance.change.diff import extract_change_set
from acceptance.benchmark.fixtures import materialize_archetype
from acceptance.coverage.classify import (
    CoverageStatus,
    ImplementationCoverage,
    classify_coverage,
)
from acceptance.review_state import ChangeSet, ObligationType
from tests.support import client_returning as _client_returning
from tests.support import make_obligation as _obligation

ARCHETYPES = Path(__file__).resolve().parents[1] / "fixtures" / "archetypes"


def _archetype_change_set(name: str, tmp_path: Path) -> ChangeSet:
    fixture = materialize_archetype(ARCHETYPES / name, tmp_path / "repo")
    return extract_change_set(fixture.repo_path, fixture.base_sha, fixture.head_sha)


def _source_file(change_set: ChangeSet, suffix: str) -> str:
    return next(f.path for f in change_set.files if f.path.endswith(suffix))


def test_archetype_1_missing_instruction_is_not_addressed(tmp_path):
    change_set = _archetype_change_set("01-missed-obligation", tmp_path)
    receipt = _source_file(change_set, "receipt.py")

    obligations = [
        _obligation("show-fields", "Show item name, quantity, unit price", ObligationType.FUNCTIONAL),
        _obligation(
            "returns-in-parens",
            "Show negative-quantity returns in parentheses",
            ObligationType.BOUNDARY,
        ),
    ]
    response = {
        "classifications": [
            {
                "obligation_id": "show-fields",
                "status": "addressed",
                "rationale": "format_line renders name/qty/price.",
                "diff_refs": [f"{receipt}#0"],
            },
            {
                "obligation_id": "returns-in-parens",
                "status": "not_addressed",
                "rationale": "No code handles negative quantities.",
                "diff_refs": [],
            },
        ]
    }

    coverages = classify_coverage(obligations, change_set, _client_returning(response))
    by_id = {c.obligation_id: c for c in coverages}

    # The missing instruction is Not addressed, with no corresponding change.
    assert by_id["returns-in-parens"].status == CoverageStatus.NOT_ADDRESSED
    assert by_id["returns-in-parens"].diff_refs == []
    # The addressed one links to an exact hunk in a real file.
    assert by_id["show-fields"].status == CoverageStatus.ADDRESSED
    assert by_id["show-fields"].diff_refs
    assert by_id["show-fields"].diff_refs[0].file == receipt
    assert by_id["show-fields"].diff_refs[0].hunk_header.startswith("@@")


def test_archetype_2_missing_qualifier_is_partially_addressed(tmp_path):
    change_set = _archetype_change_set("02-qualifier-missed", tmp_path)
    pricing = _source_file(change_set, "pricing.py")

    obligations = [
        _obligation(
            "parse-symbol", "Parse a leading currency symbol to ISO", ObligationType.FUNCTIONAL
        ),
        _obligation(
            "backward-compat",
            "Plain numeric strings keep working and default to USD",
            ObligationType.COMPATIBILITY,
        ),
    ]
    response = {
        "classifications": [
            {
                "obligation_id": "parse-symbol",
                "status": "addressed",
                "rationale": "SYMBOLS maps the prefix to an ISO code.",
                "diff_refs": [f"{pricing}#0"],
            },
            {
                "obligation_id": "backward-compat",
                "status": "partially_addressed",
                "rationale": "parse_price was changed but the no-symbol branch is missing.",
                "diff_refs": [f"{pricing}#0"],
            },
        ]
    }

    coverages = classify_coverage(obligations, change_set, _client_returning(response))
    by_id = {c.obligation_id: c for c in coverages}

    # The missing qualifier is Partially addressed (relevant behavior present,
    # a branch missing) — and links to the exact code that is incomplete.
    assert by_id["backward-compat"].status == CoverageStatus.PARTIALLY_ADDRESSED
    assert by_id["backward-compat"].diff_refs
    assert by_id["backward-compat"].diff_refs[0].file == pricing


def test_missing_classification_defaults_to_unclear(tmp_path):
    change_set = _archetype_change_set("01-missed-obligation", tmp_path)
    obligations = [_obligation("only", "Some obligation", ObligationType.FUNCTIONAL)]
    # Model returned no classification for this obligation.
    coverages = classify_coverage(obligations, change_set, _client_returning({"classifications": []}))

    assert len(coverages) == 1
    assert coverages[0].status == CoverageStatus.UNCLEAR


def test_unknown_hunk_labels_are_dropped(tmp_path):
    change_set = _archetype_change_set("01-missed-obligation", tmp_path)
    obligations = [_obligation("x", "obligation", ObligationType.FUNCTIONAL)]
    response = {
        "classifications": [
            {
                "obligation_id": "x",
                "status": "addressed",
                "rationale": "...",
                "diff_refs": ["nonexistent.py#7"],  # not a real hunk
            }
        ]
    }
    coverages = classify_coverage(obligations, change_set, _client_returning(response))
    assert coverages[0].diff_refs == []  # unknown label dropped, not crashed


def test_coverage_round_trips_through_persistence(tmp_path):
    change_set = _archetype_change_set("01-missed-obligation", tmp_path)
    receipt = _source_file(change_set, "receipt.py")
    obligations = [_obligation("show-fields", "Show fields", ObligationType.FUNCTIONAL)]
    response = {
        "classifications": [
            {
                "obligation_id": "show-fields",
                "status": "addressed",
                "rationale": "ok",
                "diff_refs": [f"{receipt}#0"],
            }
        ]
    }
    coverage = classify_coverage(obligations, change_set, _client_returning(response))[0]
    assert ImplementationCoverage.from_dict(coverage.to_dict()) == coverage
