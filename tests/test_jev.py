"""Jev as a recorded, replayed provider (#385)."""

from __future__ import annotations

import pytest

from acceptance import jev as jev_module
from acceptance.jev import JEV_KEY, JEV_PRICE_PER_INPUT_TOKEN, JevProvider
from acceptance.llm import (
    LLMError,
    MissingKeyError,
    Mode,
    ModelClient,
    SchemaValidationError,
    TranscriptNotFoundError,
    TranscriptStore,
)

QUESTIONS = {"fails": {"type": "noul", "instructions": "Would it fail?", "criteria": {}}}
STATE = {"test": "def test_x():\n    assert f() == 1\n", "code": "def f():\n    return 1\n"}


def _reply(probability=0.8, **extra):
    return {
        "answers": {"fails": {"noul": probability}},
        "model": "jev-1.13.0",
        "usage": {"input_tokens": 1000, "output_tokens": 20},
        **extra,
    }


class _Post:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, url, body, headers):
        self.calls.append(body)
        return self.replies.pop(0)


def _client(tmp_path, mode=Mode.RECORD):
    return ModelClient(model="fake", mode=mode, store=TranscriptStore(tmp_path))


def test_a_recorded_answer_replays_with_no_call(tmp_path):
    post = _Post((200, _reply(0.3)))
    first = JevProvider(post).ask(_client(tmp_path), STATE, QUESTIONS, "stage")
    assert first["fails"].probability == 0.3
    assert len(post.calls) == 1

    never = _Post()
    replayed = JevProvider(never).ask(_client(tmp_path, Mode.REPLAY), STATE, QUESTIONS, "stage")
    assert replayed["fails"].probability == 0.3
    assert never.calls == []


def test_replay_with_nothing_recorded_does_not_go_live(tmp_path):
    never = _Post()
    with pytest.raises(TranscriptNotFoundError):
        JevProvider(never).ask(_client(tmp_path, Mode.REPLAY), STATE, QUESTIONS, "stage")
    assert never.calls == []


def test_two_recordings_of_the_same_input_are_byte_identical(tmp_path):
    # Different request ids and timings in the reply: neither may reach the file.
    first_root, second_root = tmp_path / "a", tmp_path / "b"
    JevProvider(_Post((200, _reply(request_id="r-1", elapsed_ms=512)))).ask(
        _client(first_root), STATE, QUESTIONS, "stage"
    )
    JevProvider(_Post((200, _reply(request_id="r-2", elapsed_ms=730)))).ask(
        _client(second_root), STATE, QUESTIONS, "stage"
    )
    (first,) = sorted(first_root.iterdir())
    (second,) = sorted(second_root.iterdir())
    assert first.name == second.name
    assert first.read_bytes() == second.read_bytes()


def test_cost_is_priced_from_input_tokens_and_reaches_the_usage_log(tmp_path):
    client = _client(tmp_path)
    answer = JevProvider(_Post((200, _reply()))).ask(client, STATE, QUESTIONS, "jev stage", "d1")
    assert answer["fails"].usage["cost_usd"] == pytest.approx(1000 * JEV_PRICE_PER_INPUT_TOKEN)
    (call,) = client.observed_calls
    assert call["stage"] == "jev stage"
    assert call["label"] == "d1"
    assert call["model"] == "jev-latest"
    assert call["usage"]["cost_usd"] == pytest.approx(1000 * JEV_PRICE_PER_INPUT_TOKEN)


@pytest.mark.parametrize("bad", [1.5, -0.1, "0.4", True, None])
def test_an_answer_that_is_not_a_probability_is_refused_and_not_kept(tmp_path, bad):
    with pytest.raises(SchemaValidationError):
        JevProvider(_Post((200, _reply(bad)))).ask(_client(tmp_path), STATE, QUESTIONS, "stage")
    assert not tmp_path.exists() or list(tmp_path.iterdir()) == []


def test_a_reply_missing_the_question_is_refused(tmp_path):
    reply = {"answers": {}, "usage": {}}
    with pytest.raises(SchemaValidationError):
        JevProvider(_Post((200, reply))).ask(_client(tmp_path), STATE, QUESTIONS, "stage")


def test_a_transient_failure_is_retried(tmp_path, monkeypatch):
    monkeypatch.setattr(jev_module.time, "sleep", lambda _seconds: None)
    post = _Post((529, "overloaded"), (429, "slow down"), (200, _reply(0.1)))
    answer = JevProvider(post).ask(_client(tmp_path), STATE, QUESTIONS, "stage")
    assert answer["fails"].probability == 0.1
    assert len(post.calls) == 3


def test_a_permanent_failure_is_one_typed_error(tmp_path):
    with pytest.raises(LLMError, match="status 401"):
        JevProvider(_Post((401, "bad key"))).ask(_client(tmp_path), STATE, QUESTIONS, "stage")


def test_the_live_path_stops_before_sending_without_a_key(tmp_path, monkeypatch):
    monkeypatch.delenv(JEV_KEY, raising=False)
    sent = []
    monkeypatch.setattr(jev_module, "_default_post", lambda *args: sent.append(args))
    with pytest.raises(MissingKeyError, match=JEV_KEY):
        JevProvider().ask(_client(tmp_path), STATE, QUESTIONS, "stage")
    assert sent == []
