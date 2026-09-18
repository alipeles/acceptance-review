"""The review decides whether running the project's tests is worth doing.

Nobody is asked to switch it on — the human's ruling of 2026-09-18, which
retired the `--execute` flag. `mutation/settings.py::decide_execution` is that
decision and it is recorded with its reason, because "we did not run the tests"
and "we ran them and found nothing" are different facts about a review.

Gate 2 run 3 reported the criteria around this decision as only partially
supported; the gap it named was the absence of any direct test of the decision
itself, which these close.
"""

from __future__ import annotations

from acceptance.mutation.settings import ExecutionSettings, decide_execution


class TestWhenItDeclines:
    def test_no_settings_at_all_is_not_a_run(self):
        """A caller that configured nothing has not decided against running;
        it has withheld the configuration a run needs, and the reason says so."""
        decision = decide_execution(None, 5)
        assert decision.run is False
        assert "no execution settings" in decision.reason

    def test_nothing_would_consume_the_result(self):
        """The case the ruling is about: with edit verification off every
        observation is recorded as not counted, so a run earns nothing."""
        decision = decide_execution(ExecutionSettings(), 5)
        assert decision.run is False
        assert "no result could have counted" in decision.reason
        assert "#335" in decision.reason, "the reason should name what would change it"

    def test_no_defect_can_be_edited(self):
        """Verification is on, so a result could count — but there is nothing to
        inject, so there is nothing to observe a test against."""
        decision = decide_execution(ExecutionSettings(verify_edits=True), 0)
        assert decision.run is False
        assert "no enumerated defect names a changed region" in decision.reason


class TestWhenItRuns:
    def test_a_result_could_count_and_there_is_something_to_inject(self):
        decision = decide_execution(ExecutionSettings(verify_edits=True), 3)
        assert decision.run is True

    def test_the_reason_says_what_made_it_worth_doing(self):
        """Both conditions named, so a reader can see which one to change."""
        decision = decide_execution(ExecutionSettings(verify_edits=True), 3)
        assert "3 enumerated defect(s)" in decision.reason
        assert "verification is on" in decision.reason


class TestTheDecisionIsAlwaysExplained:
    def test_every_outcome_carries_a_reason(self):
        """A decision nobody can see reads the same as a stage that silently did
        nothing, which is what the report block exists to prevent."""
        for settings, editable in (
            (None, 0),
            (ExecutionSettings(), 5),
            (ExecutionSettings(verify_edits=True), 0),
            (ExecutionSettings(verify_edits=True), 5),
        ):
            assert decide_execution(settings, editable).reason.strip()
