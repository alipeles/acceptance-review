"""M3.2 acceptance: archetype #8 -> the unmentioned public-interface change is
flagged as an unrequested change.

Detection is a schema-constrained model call; per the replay-first invariant
these tests inject the recorded response via completion_fn — no live calls.
Detection *accuracy* is measured by the benchmark (M3.3)."""

from pathlib import Path

from acceptance.benchmark.fixtures import materialize_archetype
from acceptance.change.diff import extract_change_set
from acceptance.coverage.unrequested import (
    UnrequestedChange,
    UnrequestedChangeKind,
    detect_unrequested_changes,
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


def test_archetype_8_public_interface_change_is_flagged(tmp_path):
    change_set = _archetype_change_set("08-unrequested-change", tmp_path)
    cart = _source_file(change_set, "cart.py")

    # The task only asked for apply_discount; leave-existing forbids changing
    # unrelated behavior. checkout's signature change is unrequested.
    obligations = [
        _obligation("apply-discount", "Add apply_discount(total, percent)", ObligationType.FUNCTIONAL),
        _obligation("leave-existing", "Leave existing behavior as-is", ObligationType.COMPATIBILITY),
    ]
    response = {
        "unrequested_changes": [
            {
                "kind": "public_interface",
                "rationale": "checkout gained a tax_rate parameter and rounding; not requested.",
                "diff_refs": [f"{cart}#0"],
                "requested_by_obligation": False,
            }
        ]
    }

    changes = detect_unrequested_changes(obligations, change_set, _client_returning(response))

    assert len(changes) == 1
    assert changes[0].kind == UnrequestedChangeKind.PUBLIC_INTERFACE
    assert changes[0].diff_refs
    assert changes[0].diff_refs[0].file == cart
    assert changes[0].diff_refs[0].hunk_header.startswith("@@")


def test_nothing_flagged_when_all_changes_are_requested(tmp_path):
    change_set = _archetype_change_set("01-missed-obligation", tmp_path)
    obligations = [_obligation("x", "obligation", ObligationType.FUNCTIONAL)]

    changes = detect_unrequested_changes(
        obligations, change_set, _client_returning({"unrequested_changes": []})
    )
    assert changes == []


def test_unknown_hunk_labels_are_dropped(tmp_path):
    # A finding with no resolvable location is noise a human can't act on
    # (#121) -- dropped entirely, not surfaced with an empty diff_refs.
    change_set = _archetype_change_set("08-unrequested-change", tmp_path)
    obligations = [_obligation("x", "obligation", ObligationType.FUNCTIONAL)]
    response = {
        "unrequested_changes": [
            {
                "kind": "dependency",
                "rationale": "...",
                "diff_refs": ["ghost.py#9"],
                "requested_by_obligation": False,
            }
        ]
    }
    changes = detect_unrequested_changes(obligations, change_set, _client_returning(response))
    assert changes == []


def test_change_the_model_judges_requested_is_not_emitted(tmp_path):
    # #121: a detection whose own requested_by_obligation re-check comes back
    # true must not be emitted, even though the model also included it in the
    # list -- guards against exactly the self-contradictory finding seen in
    # dogfooding (rationale concluding "not unrequested" but still reported).
    change_set = _archetype_change_set("08-unrequested-change", tmp_path)
    cart = _source_file(change_set, "cart.py")
    obligations = [_obligation("x", "obligation", ObligationType.FUNCTIONAL)]
    response = {
        "unrequested_changes": [
            {
                "kind": "adjacent_behavior",
                "rationale": "...the exact implementation choice is requested, so this is not unrequested.",
                "diff_refs": [f"{cart}#0"],
                "requested_by_obligation": True,
            }
        ]
    }
    changes = detect_unrequested_changes(obligations, change_set, _client_returning(response))
    assert changes == []


def test_unrequested_change_round_trips_through_persistence(tmp_path):
    change_set = _archetype_change_set("08-unrequested-change", tmp_path)
    cart = _source_file(change_set, "cart.py")
    obligations = [_obligation("apply-discount", "Add apply_discount", ObligationType.FUNCTIONAL)]
    response = {
        "unrequested_changes": [
            {
                "kind": "public_interface",
                "rationale": "checkout signature changed",
                "diff_refs": [f"{cart}#0"],
                "requested_by_obligation": False,
            }
        ]
    }
    change = detect_unrequested_changes(obligations, change_set, _client_returning(response))[0]
    assert UnrequestedChange.from_dict(change.to_dict()) == change
