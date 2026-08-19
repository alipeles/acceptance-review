"""#248: a one-obligation response that echoes the required field yields one.

`_Yielded` encodes a non-empty obligation list as a required `obligation` plus
`more_obligations`, because strict mode rejects `minItems` and the split is the
only way to make "at least one" a property of the shape (#217). The two fields
carry no stated relationship and the prompt never names them, so in the
ONE-obligation case the model may fill the required slot and then emit the same
object again as the whole list. `_unique` then renamed the echo to `-2` and the
requirement was recorded as having yielded two obligations.

Measured over all 1,055 recorded transcripts: four duplicate-bearing
dispositions, every one a byte-identical head versus `more_obligations[0]` with
exactly one entry in the remainder, and zero duplicates anywhere else.

The tests therefore concentrate on WHERE the repeat sits and on how exactly it
matches, because those are the two axes that separate the schema echo — which
must collapse — from the model genuinely restating itself, which must not.

Responses are injected through the harness, per the replay-first invariant — no
live calls.
"""

from __future__ import annotations

import pytest

from acceptance.requirement import obligations as obligations_module
from acceptance.requirement.obligations import decompose
from acceptance.requirement.task_file import parse_task_file
from acceptance.serialization import canonical_json
from acceptance.supplied_ids import UnusableAnswerLog
from tests.support import client_returning

# Non-overlapping wording, so a quotation identifies its requirement and a
# collapsed obligation cannot be a coincidence of phrasing.
TASK = """# Task
Render each invoice line.

## Constraints
- Format money as USD with two decimals.
- Keep the existing CSV export unchanged.

## Completion expectations
- A test covers the rounding boundary at half a cent.
"""


def _obligation(oid: str, description: str, quote: str, **overrides) -> dict:
    return {
        "id": oid,
        "description": description,
        "type": "functional",
        "importance": "normal",
        "explicit": True,
        "observable_behavior": "...",
        "source_quote": quote,
        # Requiring both is the safe default the stage itself applies (#266);
        # a fixture silent about which evidence is owed is not narrowing.
        "required_evidence": "code_and_tests",
        "required_evidence_reason": "",
        **overrides,
    }


def _yielded(rid: str, *obligation_ids: str) -> dict:
    return {
        "requirement_id": rid,
        "disposition": "yielded",
        "obligation_id": obligation_ids[0],
        "more_obligation_ids": list(obligation_ids[1:]),
    }


def _declined(rid: str) -> dict:
    return {
        "requirement_id": rid,
        "disposition": "no_obligation",
        "reason": "Not applicable.",
    }


USD = ("usd", "Format money as USD.", "Format money as USD")


def _decompose(obligations: list[dict], dispositions: list[dict], log=None):
    response = {
        "obligations": obligations,
        "open_questions": [],
        "requirement_dispositions": dispositions,
    }
    return decompose(parse_task_file(TASK), client_returning(response), log)


def _echo_response(log=None, *, extra: list[dict] | None = None, ids=("usd", "usd")):
    """`constraint-01` yields one obligation, emitted twice.

    The two dicts are separate objects with identical contents, which is what
    the wire carries — the adapter consumes them positionally, so this is a
    genuine byte-identical echo and not one object referenced twice.
    """
    carried = [_obligation(*USD), _obligation(*USD), *(extra or [])]
    return _decompose(
        carried,
        [
            _declined("task-01"),
            _yielded("constraint-01", *ids),
            _declined("constraint-02"),
            _declined("completion-01"),
        ],
        log,
    )


# --- the echo collapses -----------------------------------------------------


def test_an_echoed_required_obligation_yields_one_obligation():
    """The acceptance criterion. Before #248 this produced two obligations, the
    second renamed `usd-2`, and the requirement was recorded as yielding both."""
    result = _echo_response()

    assert [o.id for o in result.obligations] == ["usd"]
    assert result.requirement_map.disposition_for("constraint-01").obligation_ids == ["usd"]


def test_collapsing_an_echo_is_recorded():
    """Silence here would be indistinguishable from the model having answered
    once, and the frequency of the echo is the evidence #256 is waiting on."""
    log = UnusableAnswerLog()
    _echo_response(log)

    echoes = [a for a in log.answers if a.field == "more_obligations"]
    assert len(echoes) == 1
    assert echoes[0].returned_id == "usd"
    assert echoes[0].stage == "decompose"
    assert "constraint-01" in (echoes[0].reason or "")


def test_the_record_attributes_the_echo_to_the_response_shape():
    """Not to a faulty answer. The model filled an ambiguous schema in a
    defensible way, and a reason blaming it would send the reader to the wrong
    fix — the prompt rather than the shape (#256)."""
    log = UnusableAnswerLog()
    _echo_response(log)

    reason = next(a for a in log.answers if a.field == "more_obligations").reason or ""
    assert "shape" in reason
    assert "single-obligation" in reason


def test_the_surviving_obligation_carries_no_suffix_earned_by_the_echo():
    """`_unique` is what turned the echo into a second obligation, so an id
    still carrying `-2` would mean the collapse ran too late to matter."""
    result = _echo_response()

    assert [o.id for o in result.obligations] == ["usd"]
    assert not any(o.id.endswith("-2") for o in result.obligations)


def test_the_surviving_obligation_keeps_its_content():
    result = _echo_response()

    (survivor,) = result.obligations
    assert survivor.description == "Format money as USD."
    assert survivor.observable_behavior == "..."
    assert survivor.source_spans  # the quotation still resolves


def test_a_requirement_that_yielded_is_never_emptied_by_the_collapse():
    """The head always survives, so this holds by construction — pinned because
    a `_Yielded` requirement carrying nothing raises out of `_requirement_map`,
    which would turn a benign echo into a failed review."""
    result = _echo_response()

    assert result.requirement_map.disposition_for("constraint-01").obligation_ids == ["usd"]


# --- what must NOT collapse -------------------------------------------------


@pytest.mark.parametrize(
    "field, value",
    [
        ("description", "Format money as USD, rounding half up."),
        ("type", "boundary"),
        ("observable_behavior", "Half a cent rounds up."),
        ("source_quote", "two decimals"),
        ("importance", "high"),
    ],
)
def test_a_remainder_differing_in_any_single_field_is_kept(field, value):
    """Whole-object equality, so one differing field is a second obligation.

    The two differ in exactly ONE field and share even their id, so this is the
    narrowest possible miss. Parametrised deliberately: a guard comparing only
    `description` — which is what #248 originally prescribed — collapses four of
    these five and would report the requirement as yielding one obligation when
    it yielded two.
    """
    second = _obligation(*USD)
    second[field] = value
    result = _decompose(
        [_obligation(*USD), second],
        [
            _declined("task-01"),
            _yielded("constraint-01", "usd", "usd"),
            _declined("constraint-02"),
            _declined("completion-01"),
        ],
    )

    assert [o.id for o in result.obligations] == ["usd", "usd-2"]


def test_an_identical_entry_later_than_position_zero_is_kept():
    """Position 0 only. A repeat further down is the model restating itself,
    which is the linking stage's call — and a guard that dropped repeats
    anywhere would destroy the signal that something upstream is wrong."""
    csv = ("csv", "Preserve the CSV export.", "existing CSV export")
    result = _decompose(
        [_obligation(*USD), _obligation(*csv), _obligation(*USD)],
        [
            _declined("task-01"),
            _yielded("constraint-01", "usd", "csv", "usd"),
            _declined("constraint-02"),
            _declined("completion-01"),
        ],
    )

    assert len(result.obligations) == 3
    assert [o.id for o in result.obligations] == ["usd", "csv", "usd-2"]


def test_an_echo_surrounded_by_genuine_obligations_collapses_only_the_echo():
    """The echo is not always the whole remainder.

    Every other echo test here uses the shape actually observed in the
    transcripts — one obligation, emitted twice, nothing else. That leaves
    `more_obligations[1:]` exercised only when it is empty, so an
    implementation that collapsed the whole remainder rather than its head
    would pass all of them. Here the remainder carries a real obligation behind
    the echo, and it must survive.
    """
    csv = ("csv", "Preserve the CSV export.", "existing CSV export")
    result = _decompose(
        [_obligation(*USD), _obligation(*USD), _obligation(*csv)],
        [
            _declined("task-01"),
            _yielded("constraint-01", "usd", "usd", "csv"),
            _declined("constraint-02"),
            _declined("completion-01"),
        ],
    )

    assert [o.id for o in result.obligations] == ["usd", "csv"]


def test_two_requirements_each_echoing_are_both_collapsed():
    """One echo per disposition, not one per response. The guard runs inside
    the per-disposition loop, so a second echoing requirement in the same
    response must collapse too."""
    csv = ("csv", "Preserve the CSV export.", "existing CSV export")
    log = UnusableAnswerLog()
    result = _decompose(
        [_obligation(*USD), _obligation(*USD), _obligation(*csv), _obligation(*csv)],
        [
            _declined("task-01"),
            _yielded("constraint-01", "usd", "usd"),
            _yielded("constraint-02", "csv", "csv"),
            _declined("completion-01"),
        ],
        log,
    )

    assert [o.id for o in result.obligations] == ["usd", "csv"]
    assert len([a for a in log.answers if a.field == "more_obligations"]) == 2


def test_a_requirement_yielding_two_genuinely_different_obligations_keeps_both():
    """The unchanged majority path, and the one that must not regress."""
    csv = ("csv", "Preserve the CSV export.", "existing CSV export")
    result = _decompose(
        [_obligation(*USD), _obligation(*csv)],
        [
            _declined("task-01"),
            _yielded("constraint-01", "usd", "csv"),
            _declined("constraint-02"),
            _declined("completion-01"),
        ],
    )

    assert [o.id for o in result.obligations] == ["usd", "csv"]


# --- wiring and determinism -------------------------------------------------


def test_decompose_routes_obligations_through_the_guard(monkeypatch):
    """The wiring, not the helper. A correct `_decode_obligations` that
    `decompose` never calls is the exact hole defect injection keeps finding, and
    every behavioural test above would still pass if the stage read the raw
    `derived()` while some other caller used the guard.
    """
    calls = []
    original = obligations_module._decode_obligations

    def spy(entry, unusable_answers):
        calls.append(entry.requirement_id)
        return original(entry, unusable_answers)

    monkeypatch.setattr(obligations_module, "_decode_obligations", spy)
    _echo_response()

    assert calls == ["constraint-01"]


def test_derived_still_reports_the_response_as_received():
    """`derived()` stays raw so the echo remains observable. If the collapse
    were done there, nothing could tell a one-obligation answer from an echoed
    one, and #256 would lose the evidence it is waiting on."""
    from acceptance.requirement.obligations import _Yielded

    entry = _Yielded(
        requirement_id="constraint-01",
        disposition="yielded",
        obligation=_obligation(*USD),
        more_obligations=[_obligation(*USD)],
    )

    assert len(entry.derived()) == 2
    assert entry.echoes_head()
    assert len(obligations_module._decode_obligations(entry, None)) == 1


def test_two_runs_over_identical_task_text_produce_identical_review_state():
    """Collapsing must not introduce order- or identity-dependence: the guard
    compares whole models and keeps the head, both of which are deterministic."""
    first = _echo_response()
    second = _echo_response()

    assert canonical_json(first.model_dump()) == canonical_json(second.model_dump())
