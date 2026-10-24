"""Provider keys come from the working directory's `.env`, and a missing one is
named before any call is sent (#398).

Installed as a standalone tool and run in another project, the CLI used to see
no keys at all: it had no `.env` loading of its own, and LiteLLM's search starts
from LiteLLM's install location. A provider that then received no key answered
as if it had received a bad one, so the user went looking for a key that was
fine. These tests pin the load, the precedence of the shell over the file, the
startup warning, the stop before a live call, and that a run needing no live
call still needs no key.
"""

import os
from types import SimpleNamespace

# Imported for its side effect, before any test clears a key: LiteLLM loads a
# `.env` it finds above its own install location the first time it is imported,
# which inside this checkout is the checkout's own. Importing it first makes that
# happen now, so a key a test deletes stays deleted.
import litellm  # noqa: F401
import pytest
from pydantic import BaseModel

from acceptance import cli
from acceptance.llm import MissingKeyError, Mode, ModelClient, TranscriptStore, missing_keys

PROVIDER_KEYS = ("OPENAI_API_KEY", "VOYAGE_API_KEY", "ANTHROPIC_API_KEY")
MESSAGES = [{"role": "user", "content": "Does the test discriminate?"}]
CONTENT = '{"supported": true}'


class Verdict(BaseModel):
    supported: bool


def _fake_response(**kwargs):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=CONTENT))],
        usage=SimpleNamespace(prompt_tokens=3, completion_tokens=2, total_tokens=5),
    )


def _spy(answer):
    calls = []

    def fn(**kwargs):
        calls.append(kwargs)
        return answer(**kwargs)

    fn.calls = calls
    return fn


@pytest.fixture
def no_keys(monkeypatch):
    """No provider key anywhere: not in the environment, and no `.env` in cwd."""
    for name in PROVIDER_KEYS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def elsewhere(tmp_path, monkeypatch):
    """A working directory that is not this checkout, as for an installed tool."""
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    return project


def test_the_cli_loads_the_working_directorys_env(elsewhere, no_keys):
    (elsewhere / ".env").write_text("VOYAGE_API_KEY=from-dotenv\n")

    cli.main(["recommendation", "--criterion", "anything"])

    assert os.environ["VOYAGE_API_KEY"] == "from-dotenv"


def test_a_variable_already_set_wins_over_the_env_file(elsewhere, no_keys, monkeypatch):
    (elsewhere / ".env").write_text("VOYAGE_API_KEY=from-dotenv\n")
    monkeypatch.setenv("VOYAGE_API_KEY", "from-shell")

    cli.main(["recommendation", "--criterion", "anything"])

    assert os.environ["VOYAGE_API_KEY"] == "from-shell"


def test_no_env_file_is_not_an_error(elsewhere, no_keys, capsys):
    status = cli.main(["recommendation", "--criterion", "anything"])

    # The command's own answer, unchanged: there is no stored review here.
    assert status == 1
    assert capsys.readouterr().err.startswith("acceptance: error: no stored review found")


def test_missing_keys_names_each_providers_variable(no_keys):
    assert missing_keys("openai/gpt-5.4-mini") == ["OPENAI_API_KEY"]
    assert missing_keys("voyage/voyage-3.5-lite") == ["VOYAGE_API_KEY"]
    assert missing_keys("anthropic/claude-sonnet-4-5") == ["ANTHROPIC_API_KEY"]


def test_missing_keys_is_silent_and_empty_for_an_unknown_model(no_keys, capsys):
    assert missing_keys("no-such-provider/model") == []
    assert capsys.readouterr().out == ""


def test_a_missing_key_stops_the_completion_before_it_is_sent(tmp_path):
    provider = _spy(_fake_response)
    client = ModelClient(
        model="openai/gpt-test",
        mode=Mode.RECORD,
        store=TranscriptStore(tmp_path),
        completion_fn=provider,
        key_check=lambda model: ["OPENAI_API_KEY"],
    )

    with pytest.raises(MissingKeyError) as raised:
        client.complete(MESSAGES, Verdict, stage="decompose")

    message = str(raised.value)
    assert "OPENAI_API_KEY" in message
    assert "openai/gpt-test" in message
    assert "decompose" in message
    assert provider.calls == []
    assert not list(tmp_path.rglob("*.json"))


def test_a_missing_key_stops_the_embedding_before_it_is_sent(tmp_path):
    provider = _spy(lambda **kw: {"data": [{"embedding": [0.1]} for _ in kw["input"]]})
    client = ModelClient(
        model="openai/gpt-test",
        mode=Mode.RECORD,
        store=TranscriptStore(tmp_path),
        embedding_model="voyage/voyage-test",
        embedding_fn=provider,
        key_check=lambda model: ["VOYAGE_API_KEY"],
    )

    with pytest.raises(MissingKeyError) as raised:
        client.embed(["one"], stage="obligation linking")

    assert "VOYAGE_API_KEY" in str(raised.value)
    assert "voyage/voyage-test" in str(raised.value)
    assert provider.calls == []


def test_a_recorded_request_needs_no_key_in_either_mode(tmp_path):
    ModelClient(
        model="openai/gpt-test",
        mode=Mode.RECORD,
        store=TranscriptStore(tmp_path),
        completion_fn=_fake_response,
    ).complete(MESSAGES, Verdict, stage="decompose")

    for mode in (Mode.RECORD, Mode.REPLAY):
        client = ModelClient(
            model="openai/gpt-test",
            mode=mode,
            store=TranscriptStore(tmp_path),
            completion_fn=_spy(_fake_response),
            key_check=lambda model: ["OPENAI_API_KEY"],
        )
        assert client.complete(MESSAGES, Verdict, stage="decompose").supported is True


def test_an_injected_provider_is_not_checked_for_a_key(tmp_path, no_keys):
    client = ModelClient(
        model="openai/gpt-test",
        mode=Mode.RECORD,
        store=TranscriptStore(tmp_path),
        completion_fn=_fake_response,
    )

    assert client.complete(MESSAGES, Verdict, stage="decompose").supported is True
    assert client.missing_keys_by_model() == {}


def test_replay_reports_no_missing_keys(tmp_path, no_keys):
    client = ModelClient(
        model="openai/gpt-test",
        mode=Mode.REPLAY,
        store=TranscriptStore(tmp_path),
        embedding_model="voyage/voyage-3.5-lite",
    )

    assert client.missing_keys_by_model() == {}


def test_record_mode_names_every_configured_models_missing_key(tmp_path, no_keys):
    client = ModelClient(
        model="openai/gpt-5.4-mini",
        mode=Mode.RECORD,
        store=TranscriptStore(tmp_path),
        embedding_model="voyage/voyage-3.5-lite",
        stage_models={"decompose-summary": "anthropic/claude-sonnet-4-5"},
    )

    assert client.missing_keys_by_model() == {
        "anthropic/claude-sonnet-4-5": ["ANTHROPIC_API_KEY"],
        "openai/gpt-5.4-mini": ["OPENAI_API_KEY"],
        "voyage/voyage-3.5-lite": ["VOYAGE_API_KEY"],
    }


def test_the_cli_warns_at_startup_then_stops_before_the_first_live_call(
    elsewhere, no_keys, monkeypatch, capsys
):
    """Through `main`, with the real client and the real key check: only the
    provider function is replaced, by one that fails the test if it is reached."""
    task = elsewhere / "task.md"
    task.write_text("# Task: x\n\n## Task\n\nThe parser accepts empty input.\n")
    provider = _spy(_fake_response)
    monkeypatch.setattr("acceptance.llm._default_completion_fn", provider)

    status = cli.main(["decompose", "--task", str(task)])

    err = capsys.readouterr().err
    assert status == 1
    assert provider.calls == []
    warnings = [line for line in err.splitlines() if line.startswith("acceptance: warning:")]
    assert any(
        "ANTHROPIC_API_KEY" in line and "anthropic/claude-sonnet-5-5" in line for line in warnings
    )
    assert any("VOYAGE_API_KEY" in line and "voyage/voyage-3.5-lite" in line for line in warnings)
    errors = [line for line in err.splitlines() if line.startswith("acceptance: model error:")]
    assert len(errors) == 1
    assert "ANTHROPIC_API_KEY" in errors[0]
    assert "was not sent" in errors[0]
    assert "invalid" not in err.lower()


def test_the_cli_finds_a_key_in_the_working_directorys_env(elsewhere, no_keys, monkeypatch, capsys):
    """The #398 scenario end to end: the key is only in the project's `.env`."""
    (elsewhere / ".env").write_text("ANTHROPIC_API_KEY=sk-ant-test\nVOYAGE_API_KEY=pa-test\n")
    task = elsewhere / "task.md"
    task.write_text("# Task: x\n\n## Task\n\nThe parser accepts empty input.\n")
    provider = _spy(_fake_response)
    monkeypatch.setattr("acceptance.llm._default_completion_fn", provider)

    cli.main(["decompose", "--task", str(task)])

    err = capsys.readouterr().err
    assert "acceptance: warning:" not in err
    assert "is not set" not in err
    # The key was found, so the call went out.
    assert provider.calls


def test_a_client_on_the_default_embedding_path_names_the_embedding_models_key(tmp_path, no_keys):
    """Built as the CLI builds it — no embedding function passed — the client
    checks the embedding model's key even when its completions are injected."""
    client = ModelClient(
        model="openai/gpt-test",
        mode=Mode.RECORD,
        store=TranscriptStore(tmp_path),
        completion_fn=_fake_response,
        embedding_model="voyage/voyage-3.5-lite",
    )

    assert client.missing_keys_by_model() == {"voyage/voyage-3.5-lite": ["VOYAGE_API_KEY"]}


def test_the_classify_command_warns_then_stops_before_the_first_live_call(
    git_repo, no_keys, monkeypatch, capsys
):
    """`classify` builds its clients inside `run_classify`, so its warning is
    issued separately from `check`'s and `decompose`'s and is tested separately."""
    task = git_repo["path"] / "task.md"
    task.write_text("# Task: x\n\n## Task\n\nThe parser accepts empty input.\n")
    provider = _spy(_fake_response)
    monkeypatch.setattr("acceptance.llm._default_completion_fn", provider)

    status = cli.main(["classify", "--task", str(task), "--base", git_repo["base"]])

    err = capsys.readouterr().err
    assert status == 1
    assert provider.calls == []
    warnings = [line for line in err.splitlines() if line.startswith("acceptance: warning:")]
    assert any(
        "ANTHROPIC_API_KEY" in line and "anthropic/claude-sonnet-5-5" in line for line in warnings
    )
    assert any("VOYAGE_API_KEY" in line and "voyage/voyage-3.5-lite" in line for line in warnings)
    errors = [line for line in err.splitlines() if line.startswith("acceptance: model error:")]
    assert len(errors) == 1
    assert "ANTHROPIC_API_KEY" in errors[0]
    assert "invalid" not in err.lower()
