"""Sending a run's live calls through the Message Batches API (#414).

Every test here goes through the real LiteLLM path, not an injected completion
function, because that path is what batching changes: the batcher replaces the
HTTP client underneath LiteLLM. Nothing reaches the network. A direct call is
answered by a stand-in for LiteLLM's own HTTP client, and a batch by a stand-in
for the Anthropic SDK's batch endpoints; both answer from one fake provider, so
a direct call and a batched one can be compared request for request.
"""

from __future__ import annotations

import ast
import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from litellm.llms.custom_httpx.http_handler import HTTPHandler
from pydantic import BaseModel

from acceptance import cli, llm, llm_batch
from acceptance.benchmark import instability
from acceptance.benchmark.fixtures import build_benchmark_case
from acceptance.benchmark.instability import measure_instability
from acceptance.benchmark.runner import run_case
from acceptance.change.diff import extract_change_set
from acceptance.concurrency import DEFAULT_MAX_IN_FLIGHT, map_calls
from acceptance.config import DEFAULT_MODEL, RunConfig, provenance_for
from acceptance.llm import LLMError, Mode, ModelClient, request_key
from acceptance.llm_batch import BATCH_CALLS_IN_FLIGHT, MessageBatcher
from acceptance.pipeline import run_review
from acceptance.requirement.obligations import decompose
from acceptance.requirement.task_file import parse_task_file
from acceptance.review_state import Component, EvidenceTier, Finding, Link, Review
from acceptance.usage import summarize as summarize_usage
from tests.support import (
    _EMPTY_BY_SCHEMA,
    _completed,
    client_dispatching,
    constant_embedding_fn,
)
from tests.test_pipeline_request_openings import _JUDGMENTS, _TASK, _repo


class Verdict(BaseModel):
    supported: bool
    rationale: str


MESSAGES = [{"role": "user", "content": "Is obligation 1 supported?"}]

ARCHETYPES_DIR = Path(__file__).resolve().parent / "fixtures" / "archetypes"

_DIRECT_FIELDS = {"request", "response", "usage", "stop_reason", "controls_applied"}


class FakeProvider:
    """Answers direct calls and batches alike, differently every time.

    The answer drifts so a test can tell a replayed answer from a fresh one,
    as `test_determinism.py`'s provider does.
    """

    def __init__(self) -> None:
        self.calls = 0
        # Answers a native request body with the reply's text; unset, the
        # provider answers every call as a `Verdict`.
        self.responder = None
        self.direct: list[dict] = []
        self.direct_headers: list[dict] = []
        self.batches: list[dict] = []
        # custom_id -> how each result should come back; absent means succeeded.
        self.outcomes: list = []
        self.batches_api = SimpleNamespace(
            create=self._create, retrieve=self._retrieve, results=self._results
        )
        self.sdk = SimpleNamespace(messages=SimpleNamespace(batches=self.batches_api))

    def message(self, body: dict) -> dict:
        self.calls += 1
        if self.responder is not None:
            text = self.responder(body)
        else:
            text = json.dumps({"supported": True, "rationale": f"answer #{self.calls}"})
        return {
            "id": f"msg_{self.calls}",
            "type": "message",
            "role": "assistant",
            "model": body["model"],
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {
                "input_tokens": 1000,
                "output_tokens": 200,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
            },
        }

    def direct_transport(self) -> HTTPHandler:
        provider = self

        class Direct(HTTPHandler):
            def post(self, url, data=None, headers=None, **_):  # type: ignore[override]
                import httpx

                body = json.loads(data)
                provider.direct.append(body)
                provider.direct_headers.append(dict(headers or {}))
                return httpx.Response(
                    200,
                    content=json.dumps(provider.message(body)).encode(),
                    request=httpx.Request("POST", url),
                )

        return Direct()

    def _create(self, requests, extra_headers=None):
        batch = {
            "id": f"batch_{len(self.batches)}",
            "requests": list(requests),
            "headers": extra_headers,
        }
        self.batches.append(batch)
        return SimpleNamespace(id=batch["id"], processing_status="in_progress")

    def _retrieve(self, batch_id):
        return SimpleNamespace(id=batch_id, processing_status="ended")

    def _results(self, batch_id):
        batch = next(b for b in self.batches if b["id"] == batch_id)
        outcome = self.outcomes.pop(0) if self.outcomes else "succeeded"
        for request in batch["requests"]:
            if outcome == "missing":
                continue
            if outcome == "succeeded":
                result = SimpleNamespace(type="succeeded", message=self.message(request["params"]))
            elif outcome in ("expired", "canceled"):
                result = SimpleNamespace(type=outcome)
            else:
                error = SimpleNamespace(type=outcome, message="the provider said no")
                result = SimpleNamespace(type="errored", error=SimpleNamespace(error=error))
            yield SimpleNamespace(custom_id=request["custom_id"], result=result)

    def batched_bodies(self) -> list[dict]:
        return [request["params"] for batch in self.batches for request in batch["requests"]]


@pytest.fixture
def provider(monkeypatch) -> FakeProvider:
    fake = FakeProvider()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-never-sent")
    monkeypatch.setattr(
        "litellm.llms.anthropic.chat.handler.get_httpx_client",
        lambda *args, **kwargs: fake.direct_transport(),
    )
    monkeypatch.setattr(llm_batch, "_default_sdk_client", lambda: fake.sdk)
    monkeypatch.setattr(llm_batch, "GATHER_SECONDS", 0.05)
    monkeypatch.setattr(llm_batch, "POLL_SECONDS", 0.01)
    monkeypatch.setattr(llm, "_FIRST_BACKOFF_SECONDS", 0.0)
    return fake


def _client(root, batch: bool, mode: Mode = Mode.RECORD) -> ModelClient:
    return RunConfig(mode=mode, transcript_root=root, batch=batch).build_client()


def _record(client: ModelClient, messages=MESSAGES) -> dict:
    key = request_key(client.build_request(messages, Verdict))
    return json.loads(client.store.path_for(key).read_text())


def test_a_batched_call_is_recorded_under_the_key_of_the_same_call_sent_directly(
    tmp_path, provider
):
    batched = _client(tmp_path / "batched", batch=True)
    direct = _client(tmp_path / "direct", batch=False)

    batched.complete(MESSAGES, Verdict)

    assert len(provider.batches) == 1 and provider.direct == []
    key = request_key(direct.build_request(MESSAGES, Verdict))
    assert batched.store.path_for(key).is_file()


def test_the_batch_carries_the_request_a_direct_call_sends(tmp_path, provider):
    """What was asked does not depend on how it was sent: the body in the batch
    is the body LiteLLM posts on a direct call, breakpoints and schema included."""
    _client(tmp_path / "direct", batch=False).complete(MESSAGES, Verdict)
    _client(tmp_path / "batched", batch=True).complete(MESSAGES, Verdict)

    assert provider.batched_bodies() == provider.direct
    beta = provider.direct_headers[0].get("anthropic-beta")
    assert provider.batches[0]["headers"] == ({"anthropic-beta": beta} if beta else None)


def test_a_batched_recording_replays_with_no_live_call(tmp_path, provider):
    recorded = _client(tmp_path, batch=True).complete(MESSAGES, Verdict)
    sent = (provider.calls, len(provider.batches))

    for batch in (True, False):
        replayed = _client(tmp_path, batch=batch, mode=Mode.REPLAY).complete(MESSAGES, Verdict)
        assert replayed == recorded

    assert (provider.calls, len(provider.batches)) == sent
    assert provider.direct == []


def test_a_batched_recording_says_so_and_a_direct_one_has_its_usual_fields(tmp_path, provider):
    batched = _client(tmp_path / "batched", batch=True)
    direct = _client(tmp_path / "direct", batch=False)
    batched.complete(MESSAGES, Verdict)
    direct.complete(MESSAGES, Verdict)

    assert set(_record(batched)) == _DIRECT_FIELDS | {"sent_via"}
    assert _record(batched)["sent_via"] == "batch"
    assert set(_record(direct)) == _DIRECT_FIELDS


def test_a_batched_call_is_priced_at_half_the_direct_price(tmp_path, provider):
    batched = _client(tmp_path / "batched", batch=True)
    direct = _client(tmp_path / "direct", batch=False)
    batched.complete(MESSAGES, Verdict)
    direct.complete(MESSAGES, Verdict)

    direct_cost = _record(direct)["usage"]["cost_usd"]
    assert direct_cost > 0
    assert _record(batched)["usage"]["cost_usd"] == pytest.approx(direct_cost / 2)
    # Only the price moves; the token counts are what the provider reported.
    for name in ("prompt_tokens", "completion_tokens"):
        assert _record(batched)["usage"][name] == _record(direct)["usage"][name]


def test_a_batched_call_counts_in_the_run_spend_at_the_price_it_was_billed_at(tmp_path, provider):
    """The spend table reads the batch price off the call, not the direct one (#415)."""
    batched = _client(tmp_path / "batched", batch=True)
    direct = _client(tmp_path / "direct", batch=False)
    batched.complete(MESSAGES, Verdict)
    direct.complete(MESSAGES, Verdict)

    direct_spend = summarize_usage(direct.observed_calls).claude_run_spend_usd
    assert direct_spend > 0
    assert summarize_usage(batched.observed_calls).claude_run_spend_usd == pytest.approx(
        direct_spend / 2
    )


def _review(client: ModelClient) -> str:
    judgment = client.complete(MESSAGES, Verdict)
    finding = Finding(
        type="obligation_support",
        severity="info",
        description=judgment.rationale,
        evidence_tier=EvidenceTier.STATIC,
        produced_by=Component.STATIC_ANALYZER,
        links=[Link(kind="requirement", ref="task.md:1")],
        related_obligation="Bonds accrue using the index curve.",
    )
    return Review(
        mode="local",
        reviewed_revision="deadbeef",
        provenance=provenance_for(client),
        findings=[finding],
    ).to_canonical_json()


@pytest.mark.parametrize(("first", "second"), [(True, False), (False, True), (True, True)])
def test_two_recorded_runs_are_byte_identical_whichever_way_their_calls_were_sent(
    tmp_path, provider, first, second
):
    one = _review(_client(tmp_path, batch=first))
    two = _review(_client(tmp_path, batch=second))

    assert one == two
    assert provider.calls == 1


def test_concurrent_calls_go_out_together_as_one_batch(tmp_path, provider):
    client = _client(tmp_path, batch=True)
    questions = [[{"role": "user", "content": f"Is obligation {n} supported?"}] for n in range(20)]

    answers = map_calls(
        questions,
        lambda messages: client.complete(messages, Verdict),
        max_in_flight=client.calls_in_flight,
    )

    assert len(answers) == 20
    assert [len(batch["requests"]) for batch in provider.batches] == [20]


def test_identical_requests_waiting_together_share_one_request_in_the_batch(tmp_path, provider):
    client = _client(tmp_path, batch=True)

    first, second = map_calls(
        [MESSAGES, MESSAGES],
        lambda m: client.complete(m, Verdict),
        max_in_flight=client.calls_in_flight,
    )

    assert first == second
    assert [len(batch["requests"]) for batch in provider.batches] == [1]


def test_a_refused_batched_request_fails_without_being_asked_again(tmp_path, provider):
    provider.outcomes = ["invalid_request_error"]

    with pytest.raises(LLMError, match="status 400"):
        _client(tmp_path, batch=True).complete(MESSAGES, Verdict)

    assert len(provider.batches) == 1


@pytest.mark.parametrize("outcome", ["overloaded_error", "expired", "canceled", "missing"])
def test_a_batched_request_that_got_no_answer_is_asked_again(tmp_path, provider, outcome):
    """An overloaded provider, a batch that expired or was cancelled before the
    request ran, and a result the batch never mentioned are all transient: the
    request was fine, so it is sent again, in a batch of its own."""
    provider.outcomes = [outcome]

    verdict = _client(tmp_path, batch=True).complete(MESSAGES, Verdict)

    assert verdict.supported
    assert len(provider.batches) == 2


def test_a_batched_request_that_never_gets_an_answer_fails_rather_than_hangs(tmp_path, provider):
    provider.outcomes = ["missing"] * llm._MAX_ATTEMPTS

    with pytest.raises(LLMError, match="after 5 attempts"):
        _client(tmp_path, batch=True).complete(MESSAGES, Verdict)


def test_a_stage_on_another_provider_is_sent_directly_in_a_batched_run(tmp_path):
    seen: list[dict] = []

    def completion_fn(**kwargs):
        seen.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content='{"supported": true, "rationale": "ok"}')
                )
            ],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

    client = ModelClient(
        model="openai/gpt-5.4-mini",
        mode=Mode.RECORD,
        store=llm.TranscriptStore(tmp_path),
        completion_fn=completion_fn,
        batcher=MessageBatcher(sdk_client=object()),
    )
    client.complete(MESSAGES, Verdict)

    assert "client" not in seen[0]
    assert "sent_via" not in _record(client)


def test_batching_is_off_unless_a_run_turns_it_on():
    assert RunConfig().batch is False
    assert RunConfig().build_client().calls_in_flight is None
    assert RunConfig(batch=True).build_client().calls_in_flight == BATCH_CALLS_IN_FLIGHT


def test_check_does_not_batch(monkeypatch):
    seen: dict = {}

    def fake_run_check(_task, _base, _head, config, *_args, client=None, **_kwargs):
        seen["config"], seen["client"] = config, client
        raise cli.CliError("stopped after capturing the config")

    monkeypatch.setattr(cli, "run_check", fake_run_check)
    cli.main(["check", "--task", "t.md", "--base", "HEAD~1"])

    assert seen["config"].batch is False
    assert seen["client"].calls_in_flight is None


def test_decompose_does_not_batch(monkeypatch, tmp_path):
    seen: dict = {}

    def fake_run_decompose(*_args, client=None, **_kwargs):
        seen["client"] = client
        raise cli.CliError("stopped after capturing the client")

    monkeypatch.setattr(cli, "run_decompose", fake_run_decompose)
    cli.main(["decompose", "--task", str(tmp_path / "t.md")])

    assert seen["client"].calls_in_flight is None


class _Stop(Exception):
    pass


def test_benchmark_scoring_batches_when_its_configuration_says_to(monkeypatch, tmp_path):
    seen: dict = {}

    def fake_run_review(**kwargs):
        seen["client"] = kwargs["client"]
        raise _Stop

    monkeypatch.setattr(cli, "run_review", fake_run_review)
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")

    with pytest.raises(_Stop):
        run_case(case, config=RunConfig(batch=True, transcript_root=tmp_path / "t"))

    assert seen["client"].calls_in_flight == BATCH_CALLS_IN_FLIGHT


@pytest.mark.parametrize("batch", [True, False])
def test_the_instability_experiment_batches_when_asked(tmp_path, batch):
    seen: list[RunConfig] = []

    def factory(config: RunConfig):
        seen.append(config)
        raise _Stop

    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")
    with pytest.raises(_Stop):
        measure_instability(case, runs_per_model=2, client_factory=factory, batch=batch)

    assert seen[0].batch is batch


def test_the_default_model_is_one_that_batches():
    """Batching applies to Anthropic models only, and the default is one."""
    assert llm._needs_explicit_marker(DEFAULT_MODEL)
    assert DEFAULT_MAX_IN_FLIGHT < BATCH_CALLS_IN_FLIGHT


def test_a_client_with_batching_off_sends_directly_and_creates_no_batch(tmp_path, provider):
    """What `check` and `decompose` get: the default configuration, on the
    default Claude model, through the real provider path."""
    RunConfig(mode=Mode.RECORD, transcript_root=tmp_path).build_client().complete(MESSAGES, Verdict)

    assert len(provider.direct) == 1
    assert provider.batches == []


def test_an_injected_completion_function_is_never_batched(tmp_path):
    """It never reaches LiteLLM's HTTP client, so a recording saying it was
    batched would be false, and handing it a transport it cannot use would
    break it."""
    seen: list[dict] = []

    def completion_fn(**kwargs):
        seen.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content='{"supported": true, "rationale": "ok"}')
                )
            ],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

    client = ModelClient(
        model=DEFAULT_MODEL,
        mode=Mode.RECORD,
        store=llm.TranscriptStore(tmp_path),
        completion_fn=completion_fn,
        batcher=MessageBatcher(sdk_client=object()),
    )
    client.complete(MESSAGES, Verdict)

    assert "client" not in seen[0]
    assert "sent_via" not in _record(client)


def test_a_batched_call_answered_on_a_second_attempt_is_recorded_as_batched(tmp_path, provider):
    provider.outcomes = ["overloaded_error"]
    client = _client(tmp_path, batch=True)

    client.complete(MESSAGES, Verdict)

    assert len(provider.batches) == 2 and provider.direct == []
    assert _record(client)["sent_via"] == "batch"


def test_an_embedding_in_a_batched_run_is_sent_directly_and_says_nothing_of_batches(
    tmp_path, provider
):
    """The Message Batches API carries Claude completions only."""
    client = _client(tmp_path, batch=True)
    client._embedding_fn = constant_embedding_fn
    client._embedding_key_check = None

    client.embed(["one text"], stage="obligation linking")

    records = [json.loads(path.read_text()) for path in tmp_path.glob("*.json")]
    assert len(records) == 1
    assert "sent_via" not in records[0]
    assert provider.batches == []


def _review_arguments(tmp_path) -> dict:
    repo, base, head = _repo(tmp_path)
    return {
        "task_text": _TASK,
        "change_set": extract_change_set(repo, base, head),
        "repo": repo,
        "reviewed_revision": head,
    }


def _answering_as_the_pipeline_double(body: dict) -> str:
    """Answer a native request the way `client_dispatching(_JUDGMENTS)` does."""
    schema = body["output_format"]["schema"]
    messages = [{"role": "system", "content": body.get("system", "")}, *body["messages"]]
    kwargs = {
        "messages": messages,
        "response_format": {"json_schema": {"name": schema["title"], "schema": schema}},
    }
    responses = {**_EMPTY_BY_SCHEMA, **_JUDGMENTS}
    return json.dumps(_completed(responses[schema["title"]], **kwargs))


@pytest.mark.parametrize(("first", "second"), [(True, False), (False, True)])
def test_two_recorded_reviews_are_byte_identical_whichever_way_their_calls_were_sent(
    tmp_path, provider, first, second
):
    """The whole pipeline, recorded once each way into one transcript root:
    nothing about how a call was sent, its note or its halved price, reaches
    the review state."""
    provider.responder = _answering_as_the_pipeline_double
    arguments = _review_arguments(tmp_path)

    def review(batch: bool) -> str:
        client = _client(tmp_path / "transcripts", batch=batch)
        client._embedding_fn = constant_embedding_fn
        client._embedding_key_check = None
        return run_review(client=client, **arguments).to_canonical_json()

    one = review(first)
    calls = provider.calls
    two = review(second)

    assert calls > 0
    assert provider.calls == calls, "the second run should have replayed every call"
    assert one == two
    # The first run's calls went the way it was configured to send them.
    assert bool(provider.batches) is first and bool(provider.direct) is not first


def test_clients_built_from_one_configuration_share_one_batch(tmp_path, provider):
    """A script that builds several clients from one run's configuration still
    sends that run's waiting calls as one batch."""
    config = RunConfig(mode=Mode.RECORD, transcript_root=tmp_path, batch=True)
    clients = [config.build_client(), config.build_client()]
    questions = [
        (clients[n % 2], [{"role": "user", "content": f"Is obligation {n} supported?"}])
        for n in range(10)
    ]

    map_calls(
        questions,
        lambda item: item[0].complete(item[1], Verdict),
        max_in_flight=BATCH_CALLS_IN_FLIGHT,
    )

    assert [len(batch["requests"]) for batch in provider.batches] == [10]


@pytest.mark.parametrize("batch", [True, False])
def test_the_instability_experiments_own_client_batches_when_asked(monkeypatch, tmp_path, batch):
    """The path a script takes when it supplies no client of its own."""
    seen: dict = {}

    def fake_classify_case(_case, client, *_args, **_kwargs):
        seen["client"] = client
        raise _Stop

    monkeypatch.setattr(instability, "classify_case", fake_classify_case)
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")

    with pytest.raises(_Stop):
        instability.run_once(
            case, instability.RunKey(model=DEFAULT_MODEL, seed=None, index=0), batch=batch
        )

    assert seen["client"].calls_in_flight == (BATCH_CALLS_IN_FLIGHT if batch else None)


# Calls whose limit is about something other than the model provider, and so
# deliberately not the client's: the mutation runner's is sized for CPUs, and
# Jev is not a Claude model, so its calls are never batched.
_OWN_LIMITS = {
    ("mutation/runner.py", "_attempt("),
    ("defects/pair_mapping.py", "ask_jev"),
}


def _map_calls_sites() -> list[tuple[str, str, ast.Call]]:
    root = Path(llm.__file__).resolve().parent
    sites = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "map_calls"
            ):
                sites.append((path.relative_to(root).as_posix(), ast.unparse(node), node))
    return sites


def test_every_stage_runs_as_many_calls_at_once_as_its_client_asks():
    """The wiring. A stage that drops its client's limit sends a batching run's
    calls out eight to a batch, each batch waiting minutes, and no unit test of
    `map_calls` or the client would notice."""
    sites = _map_calls_sites()
    assert len(sites) >= 8, "the scan found too few call sites to be looking in the right place"

    missing = []
    for path, source, node in sites:
        if any(path == own and name in source for own, name in _OWN_LIMITS):
            continue
        limits = [k for k in node.keywords if k.arg == "max_in_flight"]
        if not limits or not ast.unparse(limits[0].value).endswith(".calls_in_flight"):
            missing.append(f"{path}: {source[:80]}")
    assert missing == []


def test_a_batching_client_decomposes_more_than_the_default_at_once(tmp_path):
    """The same claim, observed: a task of twenty requirements is asked about
    twenty at a time by a client that batches, and eight at a time otherwise."""
    task = "# Task\nDo things.\n\n## Constraints\n" + "".join(
        f"- The tool does thing {n}.\n" for n in range(20)
    )

    def peak_for(limit: int | None) -> int:
        client = client_dispatching({})
        client.__class__ = type("_Limited", (ModelClient,), {"calls_in_flight": limit})
        answer = client._completion_fn
        in_flight, peak, lock = [0], [0], threading.Lock()

        def watched(**kwargs):
            with lock:
                in_flight[0] += 1
                peak[0] = max(peak[0], in_flight[0])
            time.sleep(0.05)
            with lock:
                in_flight[0] -= 1
            return answer(**kwargs)

        client._completion_fn = watched
        decompose(parse_task_file(task), client)
        return peak[0]

    assert peak_for(None) <= DEFAULT_MAX_IN_FLIGHT
    assert peak_for(BATCH_CALLS_IN_FLIGHT) > DEFAULT_MAX_IN_FLIGHT


@pytest.mark.parametrize("copied_after_first_client", [True, False])
def test_a_copied_configuration_batches_on_its_own(tmp_path, copied_after_first_client):
    """Whenever the copy was made: its clients share its batcher, never the
    original's."""
    config = RunConfig(mode=Mode.RECORD, transcript_root=tmp_path, batch=True)
    if copied_after_first_client:
        original = config.build_client()
        copy = config.model_copy(update={"transcript_root": tmp_path / "other"})
    else:
        copy = config.model_copy(update={"transcript_root": tmp_path / "other"})
        original = config.build_client()

    assert copy.build_client()._batcher is copy.build_client()._batcher
    assert copy.build_client()._batcher is not original._batcher
    assert config.build_client()._batcher is original._batcher


def test_the_instability_experiments_comparisons_batch_when_its_runs_do(monkeypatch, tmp_path):
    seen: dict = {}

    def fake_run_once(*_args, **_kwargs):
        raise _Stop

    monkeypatch.setattr(instability, "run_once", fake_run_once)
    original = instability.ModelClient

    def recording_client(*args, **kwargs):
        seen["batcher"] = kwargs.get("batcher")
        return original(*args, **kwargs)

    monkeypatch.setattr(instability, "ModelClient", recording_client)
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")

    for batch in (True, False):
        with pytest.raises(_Stop):
            measure_instability(case, runs_per_model=2, batch=batch)
        assert (seen["batcher"] is not None) is batch
