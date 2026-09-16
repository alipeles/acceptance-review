"""The one model call in the mutation stage, driven by a fake client.

What matters here is the shape of the exchange rather than any model's
judgement: the call is offered only this defect's own regions, its answer is
converted to a descriptor or to a decline, and a malformed answer becomes a
decline rather than an exception. The prompt's quality is a separate question
that only a recorded transcript can settle.
"""

from __future__ import annotations

import pytest

from acceptance.mutation.attempt import DeclineKind, DescriptorDecline
from acceptance.mutation.descriptor import build_descriptors, from_mapping
from acceptance.mutation.region import Region
from acceptance.review_state import Defect, DefectType

SOURCE = "def amortize(principal, months):\n    payment = principal / months\n    return payment\n"


class FakeClient:
    """Returns a queued answer per call and records what it was asked."""

    def __init__(self, *answers):
        self._answers = list(answers)
        self.calls = []

    def complete(self, messages, constrained, partition, parse_as, stage):
        self.calls.append(
            {
                "messages": messages,
                "constrained": constrained,
                "partition": partition,
                "stage": stage,
            }
        )
        return parse_as(**self._answers.pop(0))


def _defect(defect_id: str = "d1") -> Defect:
    return Defect(
        id=defect_id,
        obligation_id="o1",
        type=DefectType.OTHER,
        description="the payment ignores interest",
        code_refs=["loan.py#0"],
    )


def _region(label: str = "loan.py#0") -> Region:
    return Region(label=label, path="loan.py", start_line=1, end_line=3)


def _edit(**overrides) -> dict:
    answer = {
        "region_label": "loan.py#0",
        "start_line": 2,
        "end_line": 2,
        "replacement": "    payment = principal / months * 3\n",
        "decline": "none",
        "reason": "",
    }
    answer.update(overrides)
    return answer


def _decline(
    reason: str = "the behaviour is absent, so there is no span",
    kind: str = "not_one_contiguous_edit",
) -> dict:
    return {
        "region_label": "",
        "start_line": 0,
        "end_line": 0,
        "replacement": "",
        "decline": kind,
        "reason": reason,
    }


class TestAnEditingAnswer:
    def test_becomes_a_descriptor_on_the_named_region_s_file(self):
        client = FakeClient(_edit())
        built = build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        descriptor = built["d1"]
        assert descriptor is not None
        assert descriptor.path == "loan.py"
        assert (descriptor.start_line, descriptor.end_line) == (2, 2)
        assert descriptor.region_label == "loan.py#0"

    def test_the_replacement_is_carried_verbatim(self):
        client = FakeClient(_edit())
        built = build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        assert built["d1"].replacement == "    payment = principal / months * 3\n"

    def test_the_lines_it_replaces_are_recorded_from_the_source(self):
        """A deletion's replacement is empty, so without the original a reader
        would see nothing of what was removed."""
        client = FakeClient(_edit(start_line=2, end_line=3, replacement=""))
        built = build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        assert built["d1"].original == "".join(SOURCE.splitlines(keepends=True)[1:3])
        assert built["d1"].original


class TestDecliningIsARealAnswer:
    @pytest.mark.parametrize(
        "kind",
        [
            DeclineKind.ALREADY_PRESENT,
            DeclineKind.NOT_A_CODE_PROPERTY,
            DeclineKind.NOT_ONE_CONTIGUOUS_EDIT,
        ],
    )
    def test_a_named_decline_is_kept_with_its_kind_and_reason(self, kind):
        client = FakeClient(_decline(reason="line 2 already does this", kind=kind.value))
        built = build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        assert built["d1"] == DescriptorDecline(kind=kind, reason="line 2 already does this")

    def test_a_named_decline_wins_over_an_edit_in_the_same_answer(self):
        """The model said no edit makes the defect true; an edit it also sent
        is one it does not stand behind."""
        client = FakeClient(_edit(decline="already_present", reason="line 2"))
        built = build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        assert isinstance(built["d1"], DescriptorDecline)

    def test_a_decline_with_no_reason_still_carries_one(self):
        """An unsettled attempt must carry a reason, so a blank one from the
        model is replaced rather than allowed to fail validation later."""
        client = FakeClient(_decline(reason="  ", kind="not_a_code_property"))
        built = build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        assert built["d1"].reason

    def test_an_empty_region_with_no_decline_named_is_unusable(self):
        client = FakeClient(_edit(region_label=""))
        built = build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        assert built["d1"] is None

    def test_a_backwards_span_declines_rather_than_raising(self):
        """The stage's contract to the runner is a descriptor or nothing. An
        answer the mechanical checks would refuse a moment later lands as
        `not_mutable` either way, and raising here would break the contract."""
        client = FakeClient(_edit(start_line=5, end_line=2))
        built = build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        assert built["d1"] is None

    def test_a_zero_start_line_declines(self):
        client = FakeClient(_edit(start_line=0, end_line=0))
        built = build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        assert built["d1"] is None

    def test_a_label_that_was_not_offered_declines(self):
        client = FakeClient(_edit(region_label="other.py#3"))
        built = build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        assert built["d1"] is None


class TestWhatTheCallIsOffered:
    def test_only_this_defect_s_own_regions_are_representable(self):
        """Containment starts before the answer exists: a label outside the
        defect's own regions is not in the narrowed schema at all."""
        client = FakeClient(_edit())
        build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        constrained = client.calls[0]["constrained"]
        allowed = constrained.model_fields["region_label"].annotation
        assert "loan.py#0" in str(allowed)
        assert "other.py" not in str(allowed)

    def test_the_source_is_shown_with_absolute_line_numbers(self):
        client = FakeClient(_edit())
        build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        subject = "\n".join(message["content"] for message in client.calls[0]["messages"])
        assert "2 |     payment = principal / months" in subject

    def test_the_defect_s_own_text_is_shown(self):
        client = FakeClient(_edit())
        build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        subject = "\n".join(message["content"] for message in client.calls[0]["messages"])
        assert "the payment ignores interest" in subject

    def test_the_stage_is_named_for_attribution(self):
        client = FakeClient(_edit())
        build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        assert client.calls[0]["stage"] == "mutation descriptor"


class TestDefectsThatAreNotAskedAbout:
    def test_a_defect_with_no_region_costs_no_call(self):
        """One request per absence defect on every review is a real cost, and
        there is nothing the call could be offered or could answer."""
        client = FakeClient()
        built = build_descriptors([_defect()], {"d1": []}, {"loan.py": SOURCE}, client)
        assert built["d1"] is None
        assert client.calls == []

    def test_every_defect_appears_in_the_result(self):
        client = FakeClient(_edit())
        built = build_descriptors(
            [_defect("d1"), _defect("d2")],
            {"d1": [_region()], "d2": []},
            {"loan.py": SOURCE},
            client,
        )
        assert set(built) == {"d1", "d2"}
        assert built["d2"] is None


class TestFromMapping:
    def test_it_hands_the_runner_the_prebuilt_answer(self):
        client = FakeClient(_edit())
        built = build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        build = from_mapping(built)
        assert build(_defect(), [_region()], {"loan.py": SOURCE}) is built["d1"]

    def test_a_defect_the_stage_never_saw_is_a_decline(self):
        build = from_mapping({})
        assert build(_defect("unknown"), [], {}) is None
