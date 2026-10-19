"""A transient provider failure is retried and leaves no trace (#356).

A review makes hundreds of live calls, so one 502 or 429 on any of them must
not discard the run. These tests pin three things: a call that fails once and
then succeeds records exactly what a first-time success records, for both a
completion and an embedding; a call that keeps failing becomes one `LLMError`
naming the stage, the model and the status; and the CLI prints that as a single
`acceptance: model error:` line rather than a traceback.
"""

import json
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from acceptance import cli
from acceptance.config import RunConfig
from acceptance.llm import LLMError, Mode, ModelClient, TranscriptStore

MESSAGES = [{"role": "user", "content": "Does the test discriminate?"}]
CONTENT = '{"supported": true, "rationale": "boundary case asserted"}'


class Verdict(BaseModel):
    supported: bool
    rationale: str


class ProviderError(Exception):
    """Shaped like LiteLLM's exceptions, which carry the HTTP status they map."""

    def __init__(self, status_code: int, message: str = "upstream said no") -> None:
        super().__init__(message)
        self.status_code = status_code


def _fake_response(content: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=11, completion_tokens=7, total_tokens=18),
    )


def _fake_embedding(**kwargs):
    return {"data": [{"embedding": [0.1, 0.2]} for _ in kwargs["input"]]}


def _failing_then(succeed, failures):
    """A provider function that raises each of `failures` in turn, then answers."""
    pending = list(failures)
    calls = []

    def fn(**kwargs):
        calls.append(kwargs)
        if pending:
            raise pending.pop(0)
        return succeed(**kwargs)

    fn.calls = calls
    return fn


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    """Backoff is real time; the tests record the waits instead of sleeping them."""
    waits = []
    monkeypatch.setattr("acceptance.llm.time.sleep", waits.append)
    return waits


def _transcripts(root):
    return {path.name: path.read_bytes() for path in sorted(root.rglob("*.json"))}


def _complete(root, completion_fn):
    client = ModelClient(
        model="openai/gpt-test",
        mode=Mode.RECORD,
        store=TranscriptStore(root),
        completion_fn=completion_fn,
    )
    return client.complete(MESSAGES, Verdict, stage="decompose")


def _embed(root, embedding_fn):
    client = ModelClient(
        model="openai/gpt-test",
        mode=Mode.RECORD,
        store=TranscriptStore(root),
        embedding_model="voyage/voyage-test",
        embedding_fn=embedding_fn,
    )
    return client.embed(["one", "two"], stage="obligation linking")


@pytest.mark.parametrize(
    "failure",
    [
        ProviderError(502, "Bad Gateway"),
        ProviderError(503, "Service Unavailable"),
        ProviderError(429, "rate limited"),
        ProviderError(408, "timed out"),
        ConnectionError("connection reset by peer"),
        TimeoutError("read timed out"),
    ],
    ids=["502", "503", "429", "408", "connection", "timeout"],
)
def test_a_completion_that_fails_transiently_once_records_a_first_time_success(
    tmp_path, failure, no_waiting
):
    first_time = _complete(tmp_path / "first", lambda **kw: _fake_response(CONTENT))
    flaky = _failing_then(lambda **kw: _fake_response(CONTENT), [failure])

    retried = _complete(tmp_path / "retried", flaky)

    assert retried == first_time
    assert len(flaky.calls) == 2
    assert flaky.calls[0] == flaky.calls[1]
    assert _transcripts(tmp_path / "retried") == _transcripts(tmp_path / "first")
    assert len(no_waiting) == 1


def test_an_embedding_that_fails_transiently_once_records_a_first_time_success(
    tmp_path, no_waiting
):
    first_time = _embed(tmp_path / "first", _fake_embedding)
    flaky = _failing_then(_fake_embedding, [ProviderError(502, "Bad Gateway")])

    retried = _embed(tmp_path / "retried", flaky)

    assert retried == first_time
    assert len(flaky.calls) == 2
    assert _transcripts(tmp_path / "retried") == _transcripts(tmp_path / "first")
    assert len(no_waiting) == 1


def test_a_retried_call_replays_without_a_provider(tmp_path):
    flaky = _failing_then(lambda **kw: _fake_response(CONTENT), [ProviderError(500)])
    recorded = _complete(tmp_path, flaky)

    def explode(**kwargs):
        raise AssertionError("replay reached the provider")

    client = ModelClient(
        model="openai/gpt-test",
        mode=Mode.REPLAY,
        store=TranscriptStore(tmp_path),
        completion_fn=explode,
    )
    assert client.complete(MESSAGES, Verdict, stage="decompose") == recorded


def test_retries_are_bounded_and_back_off(tmp_path, no_waiting):
    always = _failing_then(lambda **kw: _fake_response(CONTENT), [ProviderError(502)] * 100)

    with pytest.raises(LLMError):
        _complete(tmp_path, always)

    assert 1 < len(always.calls) < 10
    assert len(no_waiting) == len(always.calls) - 1
    assert no_waiting == sorted(no_waiting)
    assert no_waiting[-1] > no_waiting[0]
    assert not list(tmp_path.rglob("*.json"))


def test_a_call_that_keeps_failing_names_stage_model_and_status_on_one_line(tmp_path):
    always = _failing_then(
        lambda **kw: _fake_response(CONTENT),
        [ProviderError(502, "Bad Gateway\n<html>\n</html>")] * 100,
    )

    with pytest.raises(LLMError) as raised:
        _complete(tmp_path, always)

    message = str(raised.value)
    assert "\n" not in message
    assert "decompose" in message
    assert "openai/gpt-test" in message
    assert "502" in message


def test_an_embedding_that_keeps_failing_names_its_stage(tmp_path):
    always = _failing_then(_fake_embedding, [ProviderError(503)] * 100)

    with pytest.raises(LLMError) as raised:
        _embed(tmp_path, always)

    message = str(raised.value)
    assert "obligation linking" in message
    assert "voyage/voyage-test" in message
    assert "503" in message


def test_a_non_transient_provider_error_is_not_retried_but_is_an_llm_error(tmp_path):
    rejected = _failing_then(
        lambda **kw: _fake_response(CONTENT), [ProviderError(401, "bad key")] * 100
    )

    with pytest.raises(LLMError) as raised:
        _complete(tmp_path, rejected)

    assert len(rejected.calls) == 1
    assert "401" in str(raised.value)


def test_a_failure_that_is_not_a_provider_error_is_neither_retried_nor_wrapped(tmp_path):
    broken = _failing_then(lambda **kw: _fake_response(CONTENT), [KeyError("bug")] * 100)

    with pytest.raises(KeyError):
        _complete(tmp_path, broken)

    assert len(broken.calls) == 1


def test_the_cli_reports_a_call_that_keeps_failing_as_one_line(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    task = tmp_path / "task.md"
    task.write_text("# Task: x\n\n## Task\n\nThe parser accepts empty input.\n")
    always = _failing_then(
        lambda **kw: _fake_response(json.dumps({})),
        [ProviderError(502, "Bad Gateway\nfrom upstream")] * 100,
    )
    client = ModelClient(
        model="openai/gpt-test",
        mode=Mode.RECORD,
        store=TranscriptStore(tmp_path / "transcripts"),
        completion_fn=always,
    )
    monkeypatch.setattr(RunConfig, "build_client", lambda self, completion_fn=None: client)

    status = cli.main(["decompose", "--task", str(task)])

    err = capsys.readouterr().err
    error_lines = [line for line in err.splitlines() if line.strip()]
    assert status == 1
    assert len(error_lines) == 1
    assert error_lines[0].startswith("acceptance: model error:")
    assert "decompose" in error_lines[0]
    assert "502" in error_lines[0]
