"""The installed litellm can build a response on the live-call path (#278).

Replay is the default everywhere, so the suite and CI never reach
`litellm.completion` — and a litellm release that cannot construct its own
`ModelResponse` (1.97.0 against pydantic 2.13) passed every check while
breaking the first recording run in each new environment. These tests drive the
real call path with litellm's `mock_response`, which builds the response
exactly as a provider reply would, but answers locally. Sockets are blocked so a
regression in that short-circuit fails here instead of reaching a provider.
"""

import socket

import pytest
from pydantic import BaseModel

from acceptance.llm import Mode, ModelClient, TranscriptStore, _default_completion_fn


class Verdict(BaseModel):
    supported: bool
    rationale: str


MESSAGES = [{"role": "user", "content": "Does the test discriminate?"}]
REPLY = '{"supported": true, "rationale": "boundary case asserted"}'


@pytest.fixture
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("the smoke test tried to open a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def test_litellm_builds_a_model_response_on_the_default_completion_path(no_network):
    response = _default_completion_fn(
        model="openai/gpt-5.4-mini", messages=MESSAGES, mock_response=REPLY
    )

    assert response.choices[0].message.content == REPLY


def test_a_recording_run_completes_through_the_installed_litellm(no_network, tmp_path):
    """The whole record path, not just litellm: the request `ModelClient`
    builds, litellm's response object, and the extraction that turns it into a
    transcript."""

    def completion_fn(**kwargs):
        return _default_completion_fn(mock_response=REPLY, **kwargs)

    client = ModelClient(
        model="openai/gpt-5.4-mini",
        mode=Mode.RECORD,
        store=TranscriptStore(tmp_path / "transcripts"),
        completion_fn=completion_fn,
    )

    verdict = client.complete(MESSAGES, Verdict)

    assert verdict == Verdict(supported=True, rationale="boundary case asserted")
