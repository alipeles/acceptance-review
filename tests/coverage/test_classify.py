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
from acceptance.review_state import (
    AdmissibleEvidence,
    ChangeSet,
    Obligation,
    ObligationType,
)
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
        _obligation(
            "show-fields", "Show item name, quantity, unit price", ObligationType.FUNCTIONAL
        ),
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


def test_preserve_obligation_not_violated_is_addressed_with_no_refs(tmp_path):
    # #133: a preserve/maintain obligation is "addressed" (evidence reviewed,
    # invariant confirmed not violated) even when nothing in the diff responds
    # to it -- empty diff_refs. Under the old rubric this could only be
    # `not_addressed`, which every consumer reads as a gap.
    change_set = _archetype_change_set("01-missed-obligation", tmp_path)
    obligations = [
        _obligation(
            "preserve-auth",
            "Preserve the existing authentication behavior",
            ObligationType.COMPATIBILITY,
        ),
    ]
    response = {
        "classifications": [
            {
                "obligation_id": "preserve-auth",
                "status": "addressed",
                "rationale": "No diff region touches authentication; the invariant is not violated.",
                "diff_refs": [],
            }
        ]
    }

    coverages = classify_coverage(obligations, change_set, _client_returning(response))

    assert coverages[0].status == CoverageStatus.ADDRESSED
    assert coverages[0].diff_refs == []  # satisfied by the absence of a violating change


def test_violated_preserve_obligation_is_not_addressed_but_cites_the_breach(tmp_path):
    # #133: a preserve obligation the diff VIOLATES is not_addressed AND cites
    # the offending hunk -- the old rubric forbade this ("not_addressed MUST be
    # empty"), leaving a reviewer no pointer to the breach.
    change_set = _archetype_change_set("08-unrequested-change", tmp_path)
    cart = _source_file(change_set, "cart.py")
    obligations = [
        _obligation(
            "preserve-checkout",
            "Preserve the existing checkout behavior",
            ObligationType.COMPATIBILITY,
        ),
    ]
    response = {
        "classifications": [
            {
                "obligation_id": "preserve-checkout",
                "status": "not_addressed",
                "rationale": "checkout gained a tax_rate parameter; the existing behavior was changed.",
                "diff_refs": [f"{cart}#0"],
            }
        ]
    }

    coverages = classify_coverage(obligations, change_set, _client_returning(response))

    assert coverages[0].status == CoverageStatus.NOT_ADDRESSED
    assert coverages[0].diff_refs  # cites the violating change, not empty
    assert coverages[0].diff_refs[0].file == cart


def test_missing_classification_defaults_to_unclear(tmp_path):
    change_set = _archetype_change_set("01-missed-obligation", tmp_path)
    obligations = [_obligation("only", "Some obligation", ObligationType.FUNCTIONAL)]
    # Model returned no classification for this obligation.
    coverages = classify_coverage(
        obligations, change_set, _client_returning({"classifications": []})
    )

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


# --- #153: a boundary obligation is confirmed by non-violation ----------------


def _boundary_obligation():
    return Obligation(
        id="pagination",
        description="The change does not alter how the invoice list is paginated",
        type=ObligationType.INVARIANT,
        importance="critical",
        explicit=True,
        observable_behavior="pagination code appearing in the diff",
        admissible_evidence=AdmissibleEvidence.CODE_ONLY,
    )


def test_a_respected_boundary_records_the_scope_examined_not_the_changes(tmp_path):
    """#153's acceptance: non-violation is a completeness claim over the
    examined change set, not a listing of every change in it.

    `diff_refs` must stay empty — no hunk supports the obligation — while
    `scope_examined` records what "none of them" ranged over. That is what keeps
    the typed-and-linked invariant satisfied for a finding whose evidence is an
    absence: it links to the scope compared, since there are no lines to link.
    """
    change_set = _archetype_change_set("01-missed-obligation", tmp_path)
    hunk_count = sum(len(f.hunks) for f in change_set.files)
    client = _client_returning(
        {
            "classifications": [
                {
                    "obligation_id": "pagination",
                    "status": "addressed",
                    "rationale": "No change touches pagination.",
                    "diff_refs": [],
                }
            ]
        }
    )

    [coverage] = classify_coverage([_boundary_obligation()], change_set, client)

    assert coverage.status is CoverageStatus.ADDRESSED
    assert coverage.diff_refs == []
    assert len(coverage.scope_examined) == hunk_count


def test_the_scope_examined_comes_from_the_diff_not_from_the_model(tmp_path):
    """Evidence-tier discipline. A completeness claim asserted by the thing
    whose completeness is in question is worth nothing, so `scope_examined` is
    populated in code from the hunks actually rendered into the prompt.

    The model here returns a `diff_refs` list naming ONE hunk; the recorded
    scope must still be the whole change set, because what was examined is a
    fact about the request rather than about the answer.
    """
    change_set = _archetype_change_set("01-missed-obligation", tmp_path)
    hunk_count = sum(len(f.hunks) for f in change_set.files)
    assert hunk_count > 1, "fixture must have several hunks for this to mean anything"
    client = _client_returning(
        {
            "classifications": [
                {
                    "obligation_id": "pagination",
                    "status": "addressed",
                    "rationale": "checked",
                    "diff_refs": [],
                }
            ]
        }
    )

    [coverage] = classify_coverage([_boundary_obligation()], change_set, client)

    assert len(coverage.scope_examined) == hunk_count


def test_an_ordinary_obligation_records_no_scope_examined(tmp_path):
    """The boundary of the feature: for an ordinary obligation the evidence IS
    the cited hunks, so recording the whole diff alongside them would say
    nothing and would make every obligation look like a completeness claim."""
    change_set = _archetype_change_set("01-missed-obligation", tmp_path)
    client = _client_returning(
        {
            "classifications": [
                {
                    "obligation_id": "ordinary",
                    "status": "addressed",
                    "rationale": "done",
                    "diff_refs": [],
                }
            ]
        }
    )

    [coverage] = classify_coverage(
        [_obligation("ordinary", "Totals are rounded to two places", ObligationType.FUNCTIONAL)],
        change_set,
        client,
    )

    assert coverage.scope_examined == []


def test_a_breached_boundary_cites_where_it_crosses(tmp_path):
    """#153's acceptance: a breach DOES have a location even though respect does
    not, and citing it is the whole value of the finding."""
    change_set = _archetype_change_set("01-missed-obligation", tmp_path)
    receipt = _source_file(change_set, "receipt.py")
    client = _client_returning(
        {
            "classifications": [
                {
                    "obligation_id": "pagination",
                    "status": "not_addressed",
                    "rationale": "This change rewrites the pagination helper.",
                    "diff_refs": [f"{receipt}#0"],
                }
            ]
        }
    )

    [coverage] = classify_coverage([_boundary_obligation()], change_set, client)

    assert coverage.status is CoverageStatus.NOT_ADDRESSED
    assert [ref.file for ref in coverage.diff_refs] == [receipt]


def test_a_respected_boundary_drops_hunks_the_model_cited_anyway(tmp_path):
    """The defect #153's own Gate 2 caught, and the one the tests above could
    not: every other case here feeds a COMPLIANT response, so they all pass
    against an implementation that simply trusts the model.

    The prompt tells the classifier to leave `diff_refs` empty for a respected
    boundary. On #153's Gate 2 the model returned hunks anyway for 3 of 7
    exclusions, and the report rendered them as a listing — reading as evidence
    FOR the obligation, which is precisely what the acceptance forbids.

    A respected boundary has no supporting hunks by construction, so this is
    enforced in code rather than asked for.
    """
    change_set = _archetype_change_set("01-missed-obligation", tmp_path)
    receipt = _source_file(change_set, "receipt.py")
    client = _client_returning(
        {
            "classifications": [
                {
                    "obligation_id": "pagination",
                    "status": "addressed",
                    "rationale": "Nothing here touches pagination.",
                    # Non-compliant: the prompt forbids these for a respected boundary.
                    "diff_refs": [f"{receipt}#0"],
                }
            ]
        }
    )

    [coverage] = classify_coverage([_boundary_obligation()], change_set, client)

    assert coverage.status is CoverageStatus.ADDRESSED
    assert coverage.diff_refs == []
    # The scope claim survives — dropping the citations must not drop the claim.
    assert coverage.scope_examined


def test_a_breached_boundary_keeps_the_hunks_the_model_cited(tmp_path):
    """The boundary of the rule above. Enforcement applies to `addressed` only:
    a breach DOES have a location, and stripping it would leave a violation
    finding with nothing to point at — worse than the listing it fixes."""
    change_set = _archetype_change_set("01-missed-obligation", tmp_path)
    receipt = _source_file(change_set, "receipt.py")
    client = _client_returning(
        {
            "classifications": [
                {
                    "obligation_id": "pagination",
                    "status": "not_addressed",
                    "rationale": "This change rewrites the pagination helper.",
                    "diff_refs": [f"{receipt}#0"],
                }
            ]
        }
    )

    [coverage] = classify_coverage([_boundary_obligation()], change_set, client)

    assert [ref.file for ref in coverage.diff_refs] == [receipt]
