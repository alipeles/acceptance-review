"""#259 — obligation pairs too far apart in embedding space are never asked about.

The prefilter's whole risk is that it removes questions silently, so these tests
are mostly about what is *not* sent and what the run says it dropped. Distances
come from hand-placed vectors rather than a real embedding model: the threshold
is calibrated to `voyage-3.5-lite` and this suite is about the mechanism, not
about that calibration, which #211 is the way to settle.
"""

from __future__ import annotations

import json
import math
import tempfile

import pytest

from acceptance.config import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_LINK_DISTANCE_THRESHOLD,
    RunConfig,
    provenance_for,
)
from acceptance.llm import (
    LLMError,
    Mode,
    ModelClient,
    TranscriptNotFoundError,
    TranscriptStore,
    request_key,
)
from acceptance.requirement.linking import (
    _pairs,
    _Verdicts,
    cosine_distance,
    embedding_text,
    link_duplicate_obligations,
)
from acceptance.requirement.obligations import Decomposition
from acceptance.review_state import (
    Disposition,
    Obligation,
    ObligationType,
    RequirementDisposition,
    RequirementMap,
    RequirementRef,
    RequirementSection,
)
from acceptance.source_ref import TextSpan
from tests.support import constant_embedding_fn, embedding_fn_for


# Unit vectors at chosen angles, so a test states the distance it wants.
# cosine_distance(_at(0), _at(theta)) == 1 - cos(theta).
def _at(radians: float) -> list[float]:
    return [math.cos(radians), math.sin(radians)]


def _vector_for_distance(distance: float) -> list[float]:
    """A vector whose cosine distance from `_at(0)` is exactly `distance`."""
    return _at(math.acos(1.0 - distance))


def _obligation(obligation_id: str, description: str, typ=ObligationType.FUNCTIONAL) -> Obligation:
    return Obligation(
        id=obligation_id,
        description=description,
        type=typ,
        importance="critical",
        explicit=True,
        observable_behavior=f"{obligation_id}() holds",
        source_spans=[TextSpan(text=description, start=0, end=len(description))],
    )


def _decomposition(*obligations: Obligation) -> Decomposition:
    requirements = [
        RequirementRef(
            id=f"constraint-{index:02d}",
            section=RequirementSection.CONSTRAINT,
            ordinal=index,
            span=TextSpan(text=obligation.description, start=0, end=len(obligation.description)),
        )
        for index, obligation in enumerate(obligations)
    ]
    dispositions = [
        RequirementDisposition(
            requirement_id=f"constraint-{index:02d}",
            disposition=Disposition.YIELDED,
            obligation_ids=[obligation.id],
        )
        for index, obligation in enumerate(obligations)
    ]
    return Decomposition(
        obligations=list(obligations),
        requirement_map=RequirementMap(requirements=requirements, dispositions=dispositions),
    )


def _client_recording_pairs(vectors_by_text, asked: list[str]):
    """A client that answers `false` to everything and records the pair ids asked."""

    def completion_fn(**kwargs):
        from types import SimpleNamespace

        schema = kwargs["response_format"]["json_schema"]["schema"]
        found: list[str] = []

        def walk(node, key=None):
            if isinstance(node, dict):
                if key == "pair_id" and isinstance(node.get("enum"), list):
                    found.extend(v for v in node["enum"] if v not in found)
                for name, value in node.items():
                    walk(value, name if name not in ("properties", "$defs", "items") else key)
            elif isinstance(node, list):
                for item in node:
                    walk(item, key)

        walk(schema)
        asked.extend(found)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(
                            {
                                "verdicts": [
                                    {"pair_id": p, "same_requirement": False, "reason": "no"}
                                    for p in found
                                ]
                            }
                        )
                    )
                )
            ],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )


    return ModelClient(
        model="openai/gpt-5.4-mini",
        mode=Mode.RECORD,
        store=TranscriptStore(tempfile.mkdtemp()),
        completion_fn=completion_fn,
        embedding_model=DEFAULT_EMBEDDING_MODEL,
        embedding_fn=embedding_fn_for(vectors_by_text),
    )


def _near_and_far():
    """Three obligations: `near` sits 0.05 from `origin`, `far` sits 0.5."""
    origin = _obligation("origin", "the origin obligation")
    near = _obligation("near", "a near obligation")
    far = _obligation("far", "a distant obligation")
    vectors = {
        embedding_text(origin): _at(0.0),
        embedding_text(near): _vector_for_distance(0.05),
        embedding_text(far): _vector_for_distance(0.5),
    }
    return _decomposition(origin, near, far), vectors


# --- the two headline behaviours -------------------------------------------


def test_a_pair_beyond_the_threshold_is_never_sent_to_the_model():
    decomposition, vectors = _near_and_far()
    asked: list[str] = []
    client = _client_recording_pairs(vectors, asked)

    link_duplicate_obligations(decomposition, client, distance_threshold=0.10)

    pair_ids = {p: (a, b) for p, a, b in _pairs(["origin", "near", "far"])}
    asked_pairs = {frozenset(pair_ids[p]) for p in asked}
    assert frozenset(("origin", "far")) not in asked_pairs
    assert frozenset(("near", "far")) not in asked_pairs


def test_a_pair_within_the_threshold_is_sent_to_the_model():
    decomposition, vectors = _near_and_far()
    asked: list[str] = []
    client = _client_recording_pairs(vectors, asked)

    link_duplicate_obligations(decomposition, client, distance_threshold=0.10)

    pair_ids = {p: (a, b) for p, a, b in _pairs(["origin", "near", "far"])}
    asked_pairs = {frozenset(pair_ids[p]) for p in asked}
    assert frozenset(("origin", "near")) in asked_pairs


# --- what the run says it dropped ------------------------------------------


def test_the_number_of_pairs_excluded_by_distance_reaches_review_state():

    decomposition, vectors = _near_and_far()
    client = _client_recording_pairs(vectors, [])

    link_duplicate_obligations(decomposition, client, distance_threshold=0.10)

    prefilter = provenance_for(client).link_prefilter
    assert prefilter is not None
    # Three obligations, three pairs, of which two involve `far`.
    assert prefilter.pairs_considered == 3
    assert prefilter.pairs_excluded == 2


def test_the_threshold_in_force_reaches_review_state():

    decomposition, vectors = _near_and_far()
    client = _client_recording_pairs(vectors, [])

    link_duplicate_obligations(decomposition, client, distance_threshold=0.17)

    prefilter = provenance_for(client).link_prefilter
    assert prefilter is not None
    assert prefilter.distance_threshold == 0.17
    assert prefilter.embedding_model == DEFAULT_EMBEDDING_MODEL


def test_a_filter_that_excluded_nothing_still_reports_a_record():
    """`pairs_excluded == 0` and "no filter ran" are different claims, and only
    the second is `None`. Without this the reader cannot tell a complete sweep
    from one that happened to drop nothing."""

    decomposition, vectors = _near_and_far()
    client = _client_recording_pairs(vectors, [])

    link_duplicate_obligations(decomposition, client, distance_threshold=2.0)

    prefilter = provenance_for(client).link_prefilter
    assert prefilter is not None
    assert prefilter.pairs_excluded == 0


def test_no_prefilter_reports_none_rather_than_a_zero_record():

    decomposition, vectors = _near_and_far()
    client = _client_recording_pairs(vectors, [])

    link_duplicate_obligations(decomposition, client, distance_threshold=None)

    assert provenance_for(client).link_prefilter is None


# --- composition with the type gate ----------------------------------------


def test_a_pair_excluded_for_stating_a_different_kind_of_demand_stays_excluded():
    """The two rules compose; neither can readmit what the other excluded.

    Placed at distance 0 so the prefilter would admit it on distance alone —
    the exclusion here can only come from the type gate."""
    behaviour = _obligation("behaviour", "the thing happens", ObligationType.FUNCTIONAL)
    demand = _obligation("demand", "a test asserts the thing happens", ObligationType.TEST_DEMAND)
    vectors = {embedding_text(behaviour): _at(0.0), embedding_text(demand): _at(0.0)}
    decomposition = _decomposition(behaviour, demand)

    assert cosine_distance(vectors[embedding_text(behaviour)], vectors[embedding_text(demand)]) == 0

    asked: list[str] = []
    client = _client_recording_pairs(vectors, asked)
    link_duplicate_obligations(decomposition, client, distance_threshold=0.10)

    assert asked == []


def test_pairs_excluded_counts_only_the_distance_exclusions():
    """The denominator is the type-gated set, so `pairs_excluded` means
    "excluded by DISTANCE" rather than "excluded by either rule" — two numbers
    that would otherwise be silently conflated."""

    behaviour = _obligation("behaviour", "the thing happens", ObligationType.FUNCTIONAL)
    demand = _obligation("demand", "a test asserts it", ObligationType.TEST_DEMAND)
    far = _obligation("far", "something else entirely", ObligationType.FUNCTIONAL)
    vectors = {
        embedding_text(behaviour): _at(0.0),
        embedding_text(demand): _at(0.0),
        embedding_text(far): _vector_for_distance(0.5),
    }
    client = _client_recording_pairs(vectors, [])

    link_duplicate_obligations(
        _decomposition(behaviour, demand, far), client, distance_threshold=0.10
    )

    prefilter = provenance_for(client).link_prefilter
    # Of three pairs, behaviour+demand is type-gated out before distance is
    # consulted, leaving two considered; behaviour+far is the one dropped on
    # distance. demand+far is type-gated too.
    assert prefilter.pairs_considered == 1
    assert prefilter.pairs_excluded == 1


# --- determinism ------------------------------------------------------------


def _key_under(client, controls) -> str:
    """The request key one linking call would get under `controls`, holding the
    prompt fixed so only the control can move it."""
    return request_key(
        client.build_request(
            [{"role": "user", "content": "identical prompt"}], _Verdicts, None, controls
        )
    )


def test_changing_the_threshold_invalidates_the_recorded_linking_requests():
    """The threshold reaches the hashed request, so a moved control cannot
    replay as though nothing moved — even when the surviving pair set is
    identical, which is exactly when the prompt alone would not show it."""
    _, vectors = _near_and_far()
    client = _client_recording_pairs(vectors, [])
    base = {"distance_threshold": 0.10, "embedding_model": DEFAULT_EMBEDDING_MODEL}

    assert _key_under(client, base) != _key_under(client, {**base, "distance_threshold": 0.12})


def test_changing_the_embedding_model_invalidates_the_recorded_linking_requests():
    _, vectors = _near_and_far()
    client = _client_recording_pairs(vectors, [])
    base = {"distance_threshold": 0.10, "embedding_model": "voyage/voyage-3.5-lite"}

    assert _key_under(client, base) != _key_under(
        client, {**base, "embedding_model": "openai/text-embedding-3-small"}
    )


def test_the_linking_call_actually_carries_the_prefilter_controls():
    """The two tests above prove the harness hashes `stage_controls`; this one
    proves the linking stage supplies them. Without it they would pass over a
    mechanism nothing uses."""
    decomposition, vectors = _near_and_far()
    client = _client_recording_pairs(vectors, [])

    link_duplicate_obligations(decomposition, client, distance_threshold=0.10)

    recorded = [
        json.loads(path.read_text())["request"] for path in client.store.root.glob("*.json")
    ]
    linking = [r for r in recorded if r.get("kind") != "embedding"]
    assert linking, "no linking request was recorded"
    for request in linking:
        assert request["stage_controls"] == {
            "distance_threshold": 0.10,
            "embedding_model": DEFAULT_EMBEDDING_MODEL,
        }


def test_two_runs_over_the_same_obligation_set_choose_the_same_pairs():
    decomposition, vectors = _near_and_far()

    def chosen():
        asked: list[str] = []
        link_duplicate_obligations(
            decomposition, _client_recording_pairs(vectors, asked), distance_threshold=0.10
        )
        return asked

    assert chosen() == chosen()


# --- the embedding call itself ---------------------------------------------


def test_an_embedding_request_is_replayed_from_its_recording_rather_than_issued_again():
    calls: list[list[str]] = []

    def counting_embedding_fn(**kwargs):
        calls.append(list(kwargs["input"]))
        return constant_embedding_fn(**kwargs)


    store = TranscriptStore(tempfile.mkdtemp())
    texts = ["alpha text", "beta text"]

    def fresh(mode):
        return ModelClient(
            model="openai/gpt-5.4-mini",
            mode=mode,
            store=store,
            completion_fn=lambda **kw: None,
            embedding_model=DEFAULT_EMBEDDING_MODEL,
            embedding_fn=counting_embedding_fn,
        )

    recorded = fresh(Mode.RECORD).embed(texts)
    assert len(calls) == 1

    # A second client, sharing only the store, in REPLAY — so nothing but the
    # transcript can answer it.
    replayed = fresh(Mode.REPLAY).embed(texts)

    assert replayed == recorded
    assert len(calls) == 1, "replay issued a second live embedding call"


def test_replay_without_a_recording_raises_rather_than_calling_a_provider():

    client = ModelClient(
        model="openai/gpt-5.4-mini",
        mode=Mode.REPLAY,
        store=TranscriptStore(tempfile.mkdtemp()),
        completion_fn=lambda **kw: None,
        embedding_model=DEFAULT_EMBEDDING_MODEL,
        embedding_fn=lambda **kw: pytest.fail("REPLAY reached the provider"),
    )

    with pytest.raises(TranscriptNotFoundError):
        client.embed(["never recorded"])


def test_a_client_with_no_embedding_model_says_so_rather_than_skipping_the_filter():
    """Silently returning "no vectors" would disable the prefilter without
    anyone noticing, which is the failure mode this whole issue is about."""

    client = ModelClient(
        model="openai/gpt-5.4-mini",
        mode=Mode.RECORD,
        store=TranscriptStore(tempfile.mkdtemp()),
        completion_fn=lambda **kw: None,
    )

    with pytest.raises(LLMError, match="no embedding model"):
        client.embed(["anything"])


def test_embedding_nothing_makes_no_call():
    def exploding(**kwargs):
        raise AssertionError("embedded an empty input list")


    client = ModelClient(
        model="openai/gpt-5.4-mini",
        mode=Mode.RECORD,
        store=TranscriptStore(tempfile.mkdtemp()),
        completion_fn=lambda **kw: None,
        embedding_model=DEFAULT_EMBEDDING_MODEL,
        embedding_fn=exploding,
    )

    assert client.embed([]) == []


# --- the wiring, not just the function --------------------------------------


def test_the_configured_threshold_reaches_the_linking_stage():
    """`RunConfig`'s default is what a real run uses. A prefilter with a perfect
    unit test that the pipeline never passes a threshold to is the exact shape of
    hole defect injection keeps finding here."""
    assert RunConfig().link_distance_threshold == DEFAULT_LINK_DISTANCE_THRESHOLD
    assert RunConfig().embedding_model == DEFAULT_EMBEDDING_MODEL
    assert RunConfig().build_client().embedding_model == DEFAULT_EMBEDDING_MODEL


def test_embedding_text_is_description_and_observable_behavior():
    """The threshold is calibrated against exactly this string (DR-259), so a
    change here silently invalidates the default without changing it."""
    obligation = _obligation("alpha", "the description")
    assert embedding_text(obligation) == "the description alpha() holds"


def test_cosine_distance_matches_the_definition():
    assert cosine_distance([1.0, 0.0], [1.0, 0.0]) == pytest.approx(0.0)
    assert cosine_distance([1.0, 0.0], [0.0, 1.0]) == pytest.approx(1.0)
    assert cosine_distance([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(2.0)
    # A zero vector has no direction; treated as maximally far, the under-merging
    # direction, rather than dividing by zero.
    assert cosine_distance([0.0, 0.0], [1.0, 0.0]) == 2.0


def test_a_pair_missing_a_vector_is_asked_rather_than_dropped():
    """An embedding failure must not quietly shrink the sweep — that is the one
    outcome the filter's accounting exists to prevent."""
    ordered = ["alpha", "beta"]
    vectors = {"alpha": _at(0.0)}  # beta has none

    assert len(_pairs(ordered, None, vectors, 0.10)) == 1
