"""#293 acceptance: a criterion is re-judged only when its own inputs changed.

The defect this replaces is `rerun.py::stale_obligation_ids`, which marked an
obligation stale whenever any file it cited was touched. Appending a test to a
module leaves every existing test in it byte-identical and tripped that rule
anyway — and re-judging is not free: 33 obligations came back a tier lower in
#269's Gate 2 on exactly that, and two more in #291's on a nine-line append.

So the three inputs a rating depends on are compared at the level they are
stated: the criterion's requirement text, the set of tests mapped to it, and the
CONTENTS of those tests.
"""

from acceptance.carry import Refusal
from acceptance.evidence.discovery import DiscoveredTest
from acceptance.evidence.rejudge import (
    apply_carry_keys,
    carried_ids,
    carried_strengths,
    decide_rating_carry,
    label_carried_ratings,
    mapped_test_digests,
    sources_by_test_id,
)
from acceptance.rerun import task_source_for
from acceptance.review_state import Obligation, ObligationType, Review
from tests.support import client_dispatching

TASK = "# Task\nProrate a partial month.\n"

_PRORATES = "def test_prorates():\n    assert prorate(1) == 1\n"
_APPENDED = "def test_appended_later():\n    assert True\n"

_WIRING_TASK = "# Task\nProrate a partial month.\n\n## Constraints\n- Prorate a partial month\n"

_WIRING_JUDGEMENTS = {
    "_Decomposition": {
        "obligations": [
            {
                "id": "prorate",
                "description": "Prorate a partial month",
                "type": "functional",
                "importance": "critical",
                "explicit": True,
                "observable_behavior": "prorate(1) == 1",
                "source_quote": "Prorate a partial month",
            }
        ],
        "open_questions": [],
        "requirement_dispositions": [],
    },
    # `test_appended_later` is deliberately mapped to nothing. Mapping it to
    # `prorate` would change that criterion's mapped SET, which is a real change
    # and would correctly force a re-judgement — and this test would then pass
    # for the wrong reason.
    "_Mappings": {
        "mappings": [
            {
                "test_id": "test_billing.py::test_prorates",
                "obligation_ids": ["prorate"],
                "rationale": "Asserts prorate(1) == 1.",
            }
        ]
    },
    "_Discrimination": {
        "obligations": [
            {
                "obligation_id": "prorate",
                "defects": [
                    {
                        "description": "returns days + 1",
                        "would_be_caught": True,
                        "reason": "prorate(1) == 1 pins it.",
                    }
                ],
            }
        ]
    },
    "_Coverage": {
        "classifications": [
            {
                "obligation_id": "prorate",
                "status": "addressed",
                "rationale": "billing.py implements it.",
                "diff_refs": [],
            }
        ]
    },
    "_Detections": {"unrequested_changes": []},
    "_Judgments": {"resolutions": []},
    "_Recommendations": {"recommendations": []},
    "_Mismatches": {"mismatches": []},
}


def _obligation(obligation_id: str = "prorate", **kwargs) -> Obligation:
    kwargs.setdefault("description", "Prorate a partial month")
    return Obligation(
        id=obligation_id,
        type=ObligationType.FUNCTIONAL,
        importance="critical",
        explicit=True,
        observable_behavior="...",
        **kwargs,
    )


def _tests(*pairs: tuple[str, str]) -> list[DiscoveredTest]:
    return [
        DiscoveredTest(test_id=test_id, file=test_id.split("::", 1)[0], source=source)
        for test_id, source in pairs
    ]


def _client():
    """A client only for its determinism controls — nothing here calls a model."""
    return client_dispatching({})


def _prior(obligations: list[Obligation], revision: str = "old") -> Review:
    return Review(
        mode="local",
        reviewed_revision=revision,
        task_source=task_source_for(TASK, "task.md"),
        obligation_map=obligations,
    )


def _rated(tests: list[DiscoveredTest], obligation_id: str = "prorate", **kwargs) -> Obligation:
    """A prior obligation carrying the rating AND the inputs it was rated from.

    Built by running the real `apply_carry_keys`, not by hand: a fixture that
    computed the stored key its own way could agree with a broken implementation.
    """
    kwargs.setdefault("evidence_class", "strongly_supported")
    return apply_carry_keys([_obligation(obligation_id, **kwargs)], tests, _client())[0]


# --- the three inputs -------------------------------------------------------


def test_a_criterion_with_all_three_inputs_unchanged_keeps_its_stored_rating():
    tests = _tests(("test_billing.py::test_prorates", _PRORATES))
    prior = _prior([_rated(tests, test_evidence=["test_billing.py::test_prorates"])])
    fresh = _obligation(test_evidence=["test_billing.py::test_prorates"])

    decisions = decide_rating_carry(prior, [fresh], tests, _client())

    assert decisions["prorate"].carried is True
    assert carried_ids(decisions) == {"prorate"}


def test_a_test_appended_to_the_same_file_does_not_disturb_the_rating():
    """The #291 Gate 2 regression, and this issue's third acceptance item.

    The file holding the mapped test gains a test. The mapped test itself is
    byte-identical, so the criterion keeps its rating — where the deleted
    file-level rule would have re-judged it and, measurably, downgraded it.
    """
    before = _tests(("test_billing.py::test_prorates", _PRORATES))
    after = _tests(
        ("test_billing.py::test_prorates", _PRORATES),
        ("test_billing.py::test_appended_later", _APPENDED),
    )
    prior = _prior([_rated(before, test_evidence=["test_billing.py::test_prorates"])])
    fresh = _obligation(test_evidence=["test_billing.py::test_prorates"])

    decisions = decide_rating_carry(prior, [fresh], after, _client())

    assert decisions["prorate"].carried is True


def test_editing_a_mapped_test_forces_a_re_judgement():
    before = _tests(("test_billing.py::test_prorates", _PRORATES))
    after = _tests(("test_billing.py::test_prorates", "def test_prorates():\n    assert False\n"))
    prior = _prior([_rated(before, test_evidence=["test_billing.py::test_prorates"])])
    fresh = _obligation(test_evidence=["test_billing.py::test_prorates"])

    decisions = decide_rating_carry(prior, [fresh], after, _client())

    assert decisions["prorate"].carried is False
    assert decisions["prorate"].refusal is Refusal.REQUEST_MOVED


def test_editing_one_criterions_test_leaves_another_criterion_alone():
    """This issue's fourth acceptance item. Both criteria's tests live in one
    file, and only one of them is edited."""
    before = _tests(
        ("test_billing.py::test_prorates", _PRORATES),
        ("test_billing.py::test_rounds", "def test_rounds():\n    assert round(1) == 1\n"),
    )
    after = _tests(
        ("test_billing.py::test_prorates", _PRORATES),
        ("test_billing.py::test_rounds", "def test_rounds():\n    assert round(2) == 2\n"),
    )
    prior = _prior(
        [
            _rated(before, "prorate", test_evidence=["test_billing.py::test_prorates"]),
            _rated(before, "rounds", test_evidence=["test_billing.py::test_rounds"]),
        ]
    )
    fresh = [
        _obligation("prorate", test_evidence=["test_billing.py::test_prorates"]),
        _obligation("rounds", test_evidence=["test_billing.py::test_rounds"]),
    ]

    decisions = decide_rating_carry(prior, fresh, after, _client())

    assert carried_ids(decisions) == {"prorate"}


def test_a_gained_mapped_test_forces_a_re_judgement():
    tests = _tests(
        ("test_billing.py::test_prorates", _PRORATES),
        ("test_billing.py::test_partial", "def test_partial():\n    assert True\n"),
    )
    prior = _prior([_rated(tests, test_evidence=["test_billing.py::test_prorates"])])
    fresh = _obligation(
        test_evidence=["test_billing.py::test_prorates", "test_billing.py::test_partial"]
    )

    assert decide_rating_carry(prior, [fresh], tests, _client())["prorate"].carried is False


def test_a_lost_mapped_test_forces_a_re_judgement():
    tests = _tests(("test_billing.py::test_prorates", _PRORATES))
    prior = _prior([_rated(tests, test_evidence=["test_billing.py::test_prorates"])])
    fresh = _obligation(test_evidence=[])

    assert decide_rating_carry(prior, [fresh], tests, _client())["prorate"].carried is False


def test_a_reworded_requirement_forces_a_re_judgement():
    tests = _tests(("test_billing.py::test_prorates", _PRORATES))
    prior = _prior([_rated(tests, test_evidence=["test_billing.py::test_prorates"])])
    fresh = _obligation(
        description="Prorate any partial billing period",
        test_evidence=["test_billing.py::test_prorates"],
    )

    assert decide_rating_carry(prior, [fresh], tests, _client())["prorate"].carried is False


def test_a_mapped_test_that_vanished_from_discovery_is_not_treated_as_unchanged():
    """Under-invalidation is the one failure the deleted rule never had. A test
    that is still mapped but no longer discovered gets the empty digest, so the
    criterion's inputs move and it is judged again."""
    before = _tests(("test_billing.py::test_prorates", _PRORATES))
    prior = _prior([_rated(before, test_evidence=["test_billing.py::test_prorates"])])
    fresh = _obligation(test_evidence=["test_billing.py::test_prorates"])

    assert decide_rating_carry(prior, [fresh], [], _client())["prorate"].carried is False


# --- what carrying does and does not reuse ----------------------------------


def test_nothing_carries_without_a_prior_review():
    tests = _tests(("test_billing.py::test_prorates", _PRORATES))
    fresh = _obligation(test_evidence=["test_billing.py::test_prorates"])

    decisions = decide_rating_carry(None, [fresh], tests, _client())

    assert decisions["prorate"].carried is False
    assert decisions["prorate"].refusal is Refusal.NO_PRIOR


def test_a_criterion_the_prior_review_never_rated_has_nothing_to_carry():
    """Reusing its empty rating would present "not judged" as a judgement."""
    tests = _tests(("test_billing.py::test_prorates", _PRORATES))
    prior = _prior(
        [_rated(tests, test_evidence=["test_billing.py::test_prorates"], evidence_class=None)]
    )
    fresh = _obligation(test_evidence=["test_billing.py::test_prorates"])

    decisions = decide_rating_carry(prior, [fresh], tests, _client())

    assert decisions["prorate"].carried is False
    assert decisions["prorate"].refusal is Refusal.NOT_APPLICABLE


def test_a_prior_review_stored_before_this_feature_carries_nothing():
    """It recorded no inputs, so there is nothing to compare — which re-derives,
    the conservative direction."""
    tests = _tests(("test_billing.py::test_prorates", _PRORATES))
    prior = _prior(
        [
            _obligation(
                test_evidence=["test_billing.py::test_prorates"],
                evidence_class="strongly_supported",
            )
        ]
    )
    fresh = _obligation(test_evidence=["test_billing.py::test_prorates"])

    assert decide_rating_carry(prior, [fresh], tests, _client())["prorate"].carried is False


def test_a_carried_rating_is_written_back_with_this_runs_test_links():
    tests = _tests(("test_billing.py::test_prorates", _PRORATES))
    prior = _prior(
        [
            _rated(
                tests,
                test_evidence=["test_billing.py::test_prorates"],
                evidence_class="nominally_supported",
            )
        ]
    )
    fresh = _obligation(test_evidence=["test_billing.py::test_prorates"])
    decisions = decide_rating_carry(prior, [fresh], tests, _client())

    strengths = carried_strengths(decisions, [fresh])

    assert [s.obligation_id for s in strengths] == ["prorate"]
    assert strengths[0].evidence_class == "nominally_supported"
    assert strengths[0].test_links == ["test_billing.py::test_prorates"]


def test_a_carried_rating_is_labelled_with_the_revision_it_was_established_at():
    """A rating nobody asked about this run would otherwise read as fresh."""
    tests = _tests(("test_billing.py::test_prorates", _PRORATES))
    prior = _prior([_rated(tests, test_evidence=["test_billing.py::test_prorates"])], "abc123")
    fresh = _obligation(test_evidence=["test_billing.py::test_prorates"])
    decisions = decide_rating_carry(prior, [fresh], tests, _client())

    labelled = label_carried_ratings([fresh], decisions, prior)

    assert labelled[0].carried_forward_from == "abc123"


def test_carrying_a_carried_rating_again_keeps_the_original_revision():
    """Otherwise the label drifts to the last run that reused it, and a rating
    established five heads ago claims to be one head old."""
    tests = _tests(("test_billing.py::test_prorates", _PRORATES))
    previous = _rated(
        tests, test_evidence=["test_billing.py::test_prorates"], carried_forward_from="first"
    )
    prior = _prior([previous], "second")
    fresh = _obligation(test_evidence=["test_billing.py::test_prorates"])
    decisions = decide_rating_carry(prior, [fresh], tests, _client())

    labelled = label_carried_ratings([fresh], decisions, prior)

    assert labelled[0].carried_forward_from == "first"


def test_a_re_judged_criterion_is_not_labelled_as_carried():
    after = _tests(("test_billing.py::test_prorates", "def test_prorates():\n    assert False\n"))
    before = _tests(("test_billing.py::test_prorates", _PRORATES))
    prior = _prior([_rated(before, test_evidence=["test_billing.py::test_prorates"])])
    fresh = _obligation(test_evidence=["test_billing.py::test_prorates"])
    decisions = decide_rating_carry(prior, [fresh], after, _client())

    labelled = label_carried_ratings([fresh], decisions, prior)

    assert labelled[0].carried_forward_from is None


# --- what gets stored for the next run --------------------------------------


def test_the_stored_digests_are_per_test_and_not_per_file():
    tests = _tests(
        ("test_billing.py::test_prorates", _PRORATES),
        ("test_billing.py::test_appended_later", _APPENDED),
    )
    fresh = _obligation(test_evidence=["test_billing.py::test_prorates"])

    stored = apply_carry_keys([fresh], tests, _client())[0]

    assert list(stored.mapped_test_digests) == ["test_billing.py::test_prorates"]
    assert stored.evidence_carry_key is not None


def test_the_stored_key_is_computed_from_the_stored_digests():
    """If the two were computed independently they could disagree, and a carry
    decision that disagrees with the evidence recorded for it is worse than no
    carry at all."""
    tests = _tests(("test_billing.py::test_prorates", _PRORATES))
    fresh = _obligation(test_evidence=["test_billing.py::test_prorates"])

    stored = apply_carry_keys([fresh], tests, _client())[0]

    assert stored.mapped_test_digests == mapped_test_digests(fresh, sources_by_test_id(tests))


def test_the_pipeline_carries_the_rating_and_leaves_the_criterion_out_of_the_request(tmp_path):
    """The wiring, end to end — this issue's first three acceptance items.

    A helper the pipeline never calls is the hole this repo keeps finding, so
    the prior review here is produced by a real pipeline run rather than built by
    hand: a hand-built one would have to compute the stored key itself, and could
    agree with an implementation that stored the wrong thing.

    The second run's only change is a test appended to the file that already holds
    the mapped test. Under the deleted file-level rule that re-judged `prorate`
    and, measurably, downgraded it.
    """
    import subprocess

    from acceptance.change.diff import extract_change_set
    from acceptance.pipeline import run_review

    repo = tmp_path / "repo"
    repo.mkdir(parents=True)

    def git(*args):
        subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)

    def rev():
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
        ).stdout.strip()

    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    (repo / "README.md").write_text("start\n")
    git("add", "-A")
    git("commit", "-qm", "base")
    base = rev()

    (repo / "billing.py").write_text("def prorate(days):\n    return days\n")
    (repo / "test_billing.py").write_text(
        "from billing import prorate\n\n\ndef test_prorates():\n    assert prorate(1) == 1\n"
    )
    git("add", "-A")
    git("commit", "-qm", "first")
    first = rev()

    first_review = run_review(
        task_text=_WIRING_TASK,
        change_set=extract_change_set(repo, base, first),
        repo=repo,
        client=client_dispatching(_WIRING_JUDGEMENTS),
        reviewed_revision=first,
    )
    rated = next(o for o in first_review.obligation_map if o.id == "prorate")
    assert rated.evidence_class == "strongly_supported"
    assert rated.evidence_carry_key is not None, "the first run stored nothing to compare against"

    # The append. Every existing test in the file is byte-identical.
    (repo / "test_billing.py").write_text(
        "from billing import prorate\n\n\ndef test_prorates():\n    assert prorate(1) == 1\n"
        "\n\ndef test_appended_later():\n    assert True\n"
    )
    git("add", "-A")
    git("commit", "-qm", "second")
    second = rev()

    capture: list = []
    second_review = run_review(
        task_text=_WIRING_TASK,
        change_set=extract_change_set(repo, first, second),
        repo=repo,
        client=client_dispatching(_WIRING_JUDGEMENTS, capture=capture),
        reviewed_revision=second,
        prior=first_review,
    )

    carried = next(o for o in second_review.obligation_map if o.id == "prorate")
    assert carried.evidence_class == "strongly_supported"
    assert carried.carried_forward_from == first

    # ...and it cost no evidence-judgement request. `prorate` was the only
    # criterion with a mapped test, so with it carried there was nothing left to
    # judge and the call was not made at all.
    judged = [call for call in capture if call["schema"].endswith("Discrimination")]
    assert judged == [], "the criterion was asked about despite all three inputs being unchanged"


def test_two_runs_over_the_same_inputs_compute_the_same_key():
    """Byte-identical re-runs depend on it: a key built from a dict's iteration
    order would move between runs over identical input."""
    tests = _tests(
        ("test_billing.py::test_b", "def test_b():\n    assert True\n"),
        ("test_billing.py::test_a", _PRORATES),
    )
    reversed_tests = list(reversed(tests))
    fresh = _obligation(test_evidence=["test_billing.py::test_b", "test_billing.py::test_a"])
    other = _obligation(test_evidence=["test_billing.py::test_a", "test_billing.py::test_b"])

    first = apply_carry_keys([fresh], tests, _client())[0]
    second = apply_carry_keys([other], reversed_tests, _client())[0]

    assert first.evidence_carry_key == second.evidence_carry_key
