"""M0.5 acceptance: two consecutive recorded runs over the same input produce
byte-identical review state.

The strong version of this claim is that determinism comes from *transcript
reuse*, not from the model happening to agree with itself. These tests use a
provider stub that returns a DIFFERENT answer on every live call, then show
the second run still matches the first byte-for-byte because it replayed the
first run's transcript.
"""

import json
from types import SimpleNamespace

from pydantic import BaseModel

from acceptance.config import RunConfig
from acceptance.llm import Mode
from acceptance.review_state import Component, EvidenceTier, Finding, Link, Review


class Judgment(BaseModel):
    supported: bool
    rationale: str


MESSAGES = [{"role": "user", "content": "Is obligation 1 supported?"}]


def _drifting_provider():
    """A provider whose answer changes on every call — the adversary for a
    determinism guarantee. If review state ever depends on the live call
    instead of the transcript, two runs diverge and the test fails."""
    counter = {"n": 0}

    def completion_fn(**kwargs):
        counter["n"] += 1
        content = json.dumps({"supported": True, "rationale": f"call #{counter['n']}"})
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )

    completion_fn.counter = counter
    return completion_fn


def _produce_review(config: RunConfig, completion_fn) -> Review:
    """A stand-in review flow: consult the model, fold the answer into a
    Finding, stamp provenance. Mirrors what the real M0.6+ pipeline will do."""
    client = config.build_client(completion_fn=completion_fn)
    judgment = client.complete(MESSAGES, Judgment)
    finding = Finding(
        type="obligation_support",
        severity="info",
        description=judgment.rationale,
        evidence_tier=EvidenceTier.STATIC,
        produced_by=Component.STATIC_ANALYZER,
        links=[Link(kind="requirement", ref="task.md:1")],
    )
    return Review(
        mode="local",
        reviewed_revision="deadbeef",
        provenance=config.provenance(),
        findings=[finding],
    )


def test_two_recorded_runs_are_byte_identical(tmp_path):
    config = RunConfig(
        model="anthropic/claude-sonnet-5",
        mode=Mode.RECORD,
        transcript_root=tmp_path / "transcripts",
    )
    provider = _drifting_provider()

    first = _produce_review(config, provider).to_canonical_json()
    second = _produce_review(config, provider).to_canonical_json()

    # Byte-identical despite the provider drifting — run 2 replayed run 1.
    assert first == second
    assert provider.counter["n"] == 1


def test_replay_reproduces_a_recorded_run_with_no_live_call(tmp_path):
    root = tmp_path / "transcripts"
    record_cfg = RunConfig(mode=Mode.RECORD, transcript_root=root)
    recorded = _produce_review(record_cfg, _drifting_provider()).to_canonical_json()

    def forbidden(**kwargs):
        raise AssertionError("replay issued a live call")

    replay_cfg = RunConfig(mode=Mode.REPLAY, transcript_root=root)
    replayed = _produce_review(replay_cfg, forbidden).to_canonical_json()

    # Provenance differs by mode (record vs replay), so the review state is not
    # expected to be byte-identical here — but the model-derived content is.
    assert json.loads(replayed)["findings"] == json.loads(recorded)["findings"]


def test_canonical_json_is_sorted_and_stable():
    review = Review(mode="local", reviewed_revision="abc", provenance=None)
    once = review.to_canonical_json()
    twice = review.to_canonical_json()

    assert once == twice
    # Sorted keys: `findings` precedes `mode` precedes `reviewed_revision`.
    assert once.index('"findings"') < once.index('"mode"') < once.index('"reviewed_revision"')
