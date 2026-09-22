"""The one model call in the mutation stage, driven by a fake client.

What matters here is the shape of the exchange rather than any model's
judgement: the call is offered only this defect's own regions, its answer is
converted to a descriptor or to a decline, and a malformed answer becomes a
decline rather than an exception. The prompt's quality is a separate question
that only a recorded transcript can settle.
"""

from __future__ import annotations

import pytest

from acceptance.mutation.attempt import AlreadyDefective, DeclineKind, DescriptorDecline
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
        "code_currently_does": "expected",
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
        "code_currently_does": "expected",
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
        "kind", [DeclineKind.NOT_A_CODE_PROPERTY, DeclineKind.NOT_ONE_CONTIGUOUS_EDIT]
    )
    def test_a_named_decline_is_kept_with_its_kind_and_reason(self, kind):
        client = FakeClient(_decline(reason="no span does this", kind=kind.value))
        built = build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        assert built["d1"] == DescriptorDecline(kind=kind, reason="no span does this")

    def test_a_named_decline_wins_over_an_edit_in_the_same_answer(self):
        """The model said no edit makes the defect true; an edit it also sent
        is one it does not stand behind."""
        client = FakeClient(_edit(decline="not_a_code_property", reason="a process"))
        built = build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        assert isinstance(built["d1"], DescriptorDecline)

    def test_cannot_tell_is_a_decline_whatever_edit_came_with_it(self):
        client = FakeClient(_edit(code_currently_does="cannot_tell", reason="caller not shown"))
        built = build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        assert built["d1"] == DescriptorDecline(
            kind=DeclineKind.CANNOT_TELL, reason="caller not shown"
        )


class TestTheCodeAlreadyDoesTheDefectiveBehaviour:
    """`code_currently_does` is read before the edit, and "defective" makes the
    answer a finding with its edit kept as a repair — never an injection."""

    def test_it_is_a_claim_not_an_injection(self):
        client = FakeClient(
            _edit(code_currently_does="defective", reason="line 2 ignores interest")
        )
        built = build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        assert isinstance(built["d1"], AlreadyDefective)
        assert built["d1"].reason == "line 2 ignores interest"

    def test_its_edit_is_kept_as_the_repair(self):
        client = FakeClient(_edit(code_currently_does="defective", reason="line 2"))
        built = build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        assert built["d1"].repair is not None
        assert built["d1"].repair.replacement == "    payment = principal / months * 3\n"

    def test_it_wins_over_a_decline_in_the_same_answer(self):
        client = FakeClient(
            _decline(reason="line 2 ignores interest", kind="not_one_contiguous_edit")
            | {"code_currently_does": "defective"}
        )
        built = build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        assert isinstance(built["d1"], AlreadyDefective)
        assert built["d1"].repair is None

    def test_the_field_comes_first_in_the_schema(self):
        """So the model commits to what the code does before writing an edit."""
        client = FakeClient(_edit())
        build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        fields = list(client.calls[0]["constrained"].model_fields)
        assert fields[0] == "code_currently_does"


class TestMalformedAnswers:
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

    def test_both_behaviours_are_shown_on_their_own_labelled_lines(self):
        """The direction of the edit comes from these, not from the wording of
        the description."""
        defect = _defect().model_copy(
            update={
                "expected_behavior": "the payment includes interest",
                "defective_behavior": "the payment is principal divided by months",
            }
        )
        client = FakeClient(_edit())
        build_descriptors([defect], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        subject = "\n".join(message["content"] for message in client.calls[0]["messages"])
        assert "EXPECTED: the payment includes interest" in subject
        assert "DEFECTIVE: the payment is principal divided by months" in subject

    def test_a_defect_recorded_without_behaviours_shows_no_empty_labels(self):
        client = FakeClient(_edit())
        build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, client)
        subject = "\n".join(message["content"] for message in client.calls[0]["messages"])
        assert "EXPECTED:" not in subject.split("## The defect", 1)[1]

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


class TestAskingAgainAfterARefusal:
    """#334. The live builder shows the model the candidates already refused,
    and nothing about what the tests did under any of them."""

    def _subject(self, client) -> str:
        return "\n".join(str(message["content"]) for message in client.calls[-1]["messages"])

    def _refused(self, cause, reason: str = "a reason"):
        from acceptance.mutation.attempt import MutationDescriptor, SetAsideCandidate

        return SetAsideCandidate(
            cause=cause,
            reason=reason,
            descriptor=MutationDescriptor(
                path="loan.py",
                start_line=2,
                end_line=2,
                replacement="    payment = principal / months  # tweak\n",
                region_label="loan.py#0",
            ),
        )

    def test_a_first_request_is_unchanged_so_its_recordings_still_replay(self):
        """No earlier candidates, no new block: the request, and so its key, is
        exactly what it was before #334."""
        from acceptance.mutation.descriptor import LiveDescriptorBuilder

        old = FakeClient(_edit())
        build_descriptors([_defect()], {"d1": [_region()]}, {"loan.py": SOURCE}, old)
        new = FakeClient(_edit())
        LiveDescriptorBuilder(new)(_defect(), [_region()], {"loan.py": SOURCE}, ())
        assert new.calls[0]["messages"] == old.calls[0]["messages"]
        assert "Earlier edits" not in self._subject(new)

    def test_a_later_request_shows_the_refused_edit_and_why(self):
        from acceptance.mutation.attempt import CandidateCause
        from acceptance.mutation.descriptor import LiveDescriptorBuilder

        client = FakeClient(_edit())
        previous = (self._refused(CandidateCause.CHANGED_NOTHING),)
        LiveDescriptorBuilder(client)(_defect(), [_region()], {"loan.py": SOURCE}, previous)
        subject = self._subject(client)
        assert "Earlier edits for this defect" in subject
        assert "# tweak" in subject
        assert "changed nothing" in subject

    def test_a_mechanical_refusal_is_shown_with_its_own_reason(self):
        from acceptance.mutation.attempt import CandidateCause
        from acceptance.mutation.descriptor import LiveDescriptorBuilder

        client = FakeClient(_edit())
        previous = (self._refused(CandidateCause.FAILED_CHECK, "falls outside the region"),)
        LiveDescriptorBuilder(client)(_defect(), [_region()], {"loan.py": SOURCE}, previous)
        assert "falls outside the region" in self._subject(client)

    def test_a_refusal_after_the_tests_ran_says_nothing_about_the_tests(self):
        """Its recorded reason is built from what the tests did under the edit,
        and that may reach no model."""
        from acceptance.mutation.attempt import CandidateCause
        from acceptance.mutation.descriptor import LiveDescriptorBuilder

        client = FakeClient(_edit())
        leaked = "every one of the 7 tests that failed under the edit failed with NameError"
        previous = (self._refused(CandidateCause.REFUSED_AFTER_RUN, leaked),)
        LiveDescriptorBuilder(client)(_defect(), [_region()], {"loan.py": SOURCE}, previous)
        subject = self._subject(client)
        assert "Earlier edits for this defect" in subject
        assert "NameError" not in subject
        assert "7 tests" not in subject

    def test_unusable_answers_are_recorded_in_a_fixed_order(self):
        """Candidates are asked for from concurrent attempts, so recording as
        they arrive would make two runs differ."""
        from acceptance.mutation.descriptor import LiveDescriptorBuilder

        recorded = []

        class Log:
            def record(self, answers):
                recorded.append(answers)

        builder = LiveDescriptorBuilder(FakeClient(_edit(), _edit(), _edit()))
        # Asked in an order no sort would produce: d2's second candidate, then
        # d1's first, then d2's first.
        from acceptance.mutation.attempt import CandidateCause

        earlier = (self._refused(CandidateCause.CHANGED_NOTHING),)
        builder(_defect("d2"), [_region()], {"loan.py": SOURCE}, earlier)
        builder(_defect("d1"), [_region()], {"loan.py": SOURCE}, ())
        builder(_defect("d2"), [_region()], {"loan.py": SOURCE}, ())
        # Tag each slot so the recording order is visible.
        for key in builder._unusable:
            builder._unusable[key] = [key]
        builder.record_unusable(Log())
        assert recorded == [[("d1", 0)], [("d2", 0)], [("d2", 1)]]
