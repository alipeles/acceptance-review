"""The recorded-corpus mechanism itself (#146).

`test_disposition_prompt.py` uses the corpus to test a capability's prompt.
These test the corpus machinery: that a prompt edit is detected, that the
failure explains itself, that recording cannot bypass the assertions, and that
the committed corpus holds what it should.
"""

import json
import pathlib

import pytest

from acceptance.config import DEFAULT_MODEL, ScopeExpansionPolicy
from acceptance.coverage import disposition as disposition_module
from acceptance.coverage.disposition import classify_dispositions
from acceptance.llm import Mode, ModelClient, TranscriptNotFoundError, TranscriptStore
from tests.prompts.test_disposition_prompt import _adjacent_edit_case
from tests.support import RECORDED_TRANSCRIPTS, recorded_client, replaying_client


@pytest.fixture(autouse=True)
def _no_ambient_recording(monkeypatch):
    """Neutralise an ambient ACCEPTANCE_RECORD so these behave the same for
    every developer. Defence in depth only — the test that deliberately misses
    the corpus uses `replaying_client()`, which cannot record even if this
    fixture is removed."""
    monkeypatch.delenv("ACCEPTANCE_RECORD", raising=False)


def test_editing_a_prompt_fails_with_guidance_naming_the_unverified_change(
    tmp_path, monkeypatch
):
    """The enforcement mechanism, end to end.

    `request_key` hashes the whole request including the system prompt, so
    editing a prompt is a cache miss. Simulate exactly that -- append a line to
    the disposition prompt -- and assert the resulting failure identifies
    itself as an unverified prompt change and gives the re-record command. A
    cryptic hash-not-found error would leave a developer with no idea why a
    prompt edit broke an unrelated-looking test."""
    change, obligations, change_set = _adjacent_edit_case(tmp_path)
    monkeypatch.setattr(
        disposition_module,
        "_SYSTEM_PROMPT",
        disposition_module._SYSTEM_PROMPT + "\nAn edit that changes the request hash.",
    )

    with pytest.raises(TranscriptNotFoundError) as excinfo:
        classify_dispositions(
            [change], obligations, [], change_set,
            ScopeExpansionPolicy.LOOSE, replaying_client(),
        )

    message = str(excinfo.value)
    assert "prompt was edited and has not been re-verified" in message
    assert "ACCEPTANCE_RECORD=1 pytest tests/prompts" in message


def test_recording_returns_the_fresh_response_so_assertions_run_on_it(tmp_path):
    """Recording must not be a silent "store and move on" step.

    In RECORD mode the freshly obtained response is returned to the caller, so
    the test's own assertions run against it -- which is what makes a degraded
    prompt fail rather than quietly overwrite the corpus. Proven by recording a
    response that is deliberately WRONG and observing it reach the caller: a
    test asserting the right answer would fail on it.
    """
    change, obligations, change_set = _adjacent_edit_case(tmp_path)
    client = ModelClient(
        model=DEFAULT_MODEL,
        mode=Mode.RECORD,
        store=TranscriptStore(tmp_path / "scratch-corpus"),
        completion_fn=lambda **kw: _fake_disposition("in_service"),
    )

    result = classify_dispositions(
        [change], obligations, [], change_set, ScopeExpansionPolicy.STRICT, client
    )[0]

    # The wrong answer surfaced to the caller rather than being swallowed, so an
    # assertion of the CORRECT answer would have failed here.
    assert result.disposition.value == "in_service"
    assert result.disposition.value != "risky"


def _fake_disposition(value: str):
    from types import SimpleNamespace

    content = json.dumps({"disposition": value, "rationale": "recorded for the test"})
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )


def test_the_committed_corpus_holds_only_archetype_content():
    """A transcript embeds the entire request, so recording a dogfood run would
    commit this repo's own diffs and task text into test fixtures. Assert the
    committed corpus contains none of our source paths."""
    corpus = sorted(RECORDED_TRANSCRIPTS.glob("*.json"))
    assert corpus, "the committed corpus is empty"

    ours = ("src/acceptance/", "tests/test_", "tests/prompts/", "current-task.md")
    for path in corpus:
        body = path.read_text()
        for marker in ours:
            assert marker not in body, f"{path.name} embeds this repo's own content: {marker}"


def test_the_corpus_is_recorded_against_the_model_the_tool_actually_runs():
    """A corpus recorded against some other model would prove nothing about
    production behaviour. Both the client and every committed transcript must
    name the tool's real default model."""
    assert recorded_client().model == DEFAULT_MODEL

    for path in sorted(RECORDED_TRANSCRIPTS.glob("*.json")):
        record = json.loads(path.read_text())
        assert record["request"]["model"] == DEFAULT_MODEL, path.name


def test_the_corpus_replays_rather_than_calling_live_by_default():
    """Replay is the default so the ordinary suite needs no API key and makes
    no network call; recording is opt-in via ACCEPTANCE_RECORD."""
    assert recorded_client().mode is Mode.REPLAY


def test_recording_is_opt_in_through_the_environment(monkeypatch):
    monkeypatch.setenv("ACCEPTANCE_RECORD", "1")
    assert recorded_client().mode is Mode.RECORD


def test_the_corpus_holds_exactly_the_transcripts_the_tests_replay():
    """Guard against silent corpus pollution.

    Recording writes into the committed corpus, so anything that flips a test
    into RECORD mode — a bug, a stray env var, a defect injected while probing
    a test — can leave an extra transcript behind that nobody notices. A stray
    entry is worse than clutter: it can satisfy a lookup that SHOULD have
    missed, silently disabling the prompt-edit detection this whole mechanism
    rests on. (Observed exactly once while developing #146.)

    Pinning the count makes an unintended recording a visible failure. Update
    it deliberately when adding a genuine prompt-quality case.
    """
    corpus = sorted(RECORDED_TRANSCRIPTS.glob("*.json"))

    assert len(corpus) == 2, (
        f"expected 2 recorded transcripts, found {len(corpus)}: "
        f"{[p.name for p in corpus]}. An unexpected entry usually means "
        "something recorded when it should have replayed."
    )


def test_the_prompt_corpus_replays_with_no_live_call_at_all(tmp_path):
    """Assert the BEHAVIOUR, not the mode enum.

    `test_the_corpus_replays_rather_than_calling_live_by_default` only checks
    that the mode is REPLAY — a replay path that still reached the network
    would satisfy it. Prove it properly: give the client a completion_fn that
    raises if called, and replay a committed transcript through it.
    """
    def must_not_be_called(**kwargs):
        raise AssertionError("replay made a live call")

    change, obligations, change_set = _adjacent_edit_case(tmp_path)
    client = ModelClient(
        model=DEFAULT_MODEL,
        mode=Mode.REPLAY,
        store=TranscriptStore(RECORDED_TRANSCRIPTS),
        completion_fn=must_not_be_called,
    )

    result = classify_dispositions(
        [change], obligations, [], change_set, ScopeExpansionPolicy.LOOSE, client
    )[0]

    # Reached a real recorded answer without the network being touched.
    assert result.disposition.value == "separable"


def test_the_prompt_quality_test_actually_consumes_a_committed_transcript(tmp_path):
    """Guard against the prompt-quality test passing for the wrong reason.

    It could be satisfied by something other than the corpus — a stub, a
    fast-path — and still look green. Prove the corpus is load-bearing by
    pointing the same call at an EMPTY store: it must then fail to find a
    transcript, which it could not do if it were not reading one.
    """
    change, obligations, change_set = _adjacent_edit_case(tmp_path)
    empty_store_client = ModelClient(
        model=DEFAULT_MODEL,
        mode=Mode.REPLAY,
        store=TranscriptStore(tmp_path / "empty-corpus"),
    )

    with pytest.raises(TranscriptNotFoundError):
        classify_dispositions(
            [change], obligations, [], change_set,
            ScopeExpansionPolicy.LOOSE, empty_store_client,
        )


def test_a_known_defect_survives_an_unrelated_prompt_edit(tmp_path):
    """A recorded failing case must not be lost when some OTHER prompt changes.

    The corpus is keyed by request hash, so an edit anywhere in a prompt makes
    that request miss. The hazard is a mechanism that responds to a miss by
    quietly re-recording or falling back to a live call: the known defect would
    then stop failing, and a tracked problem would silently disappear from the
    suite — the opposite of what `xfail(strict=True)` is protecting.

    Assert the miss stays a miss: an edited prompt raises rather than healing
    itself, so the failure remains visible until someone re-records
    deliberately and re-verifies the assertions.
    """
    change, obligations, change_set = _adjacent_edit_case(tmp_path)

    # Unedited: the committed recording is found, so the case still evaluates.
    baseline = classify_dispositions(
        [change], obligations, [], change_set,
        ScopeExpansionPolicy.LOOSE, replaying_client(),
    )[0]
    assert baseline.disposition.value == "separable"

    # An unrelated prompt edit must NOT be papered over by re-recording or a
    # live call — the case fails loudly instead of quietly changing answer.
    with pytest.MonkeyPatch.context() as patched:
        patched.setattr(
            disposition_module,
            "_SYSTEM_PROMPT",
            disposition_module._SYSTEM_PROMPT + "\nAn unrelated edit elsewhere in the prompt.",
        )
        with pytest.raises(TranscriptNotFoundError):
            classify_dispositions(
                [change], obligations, [], change_set,
                ScopeExpansionPolicy.LOOSE, replaying_client(),
            )

    # ...and the committed corpus is untouched by the attempt.
    assert len(list(RECORDED_TRANSCRIPTS.glob("*.json"))) == 2


# The exact recordings this suite replays. A count alone is not enough: if an
# approved transcript were REPLACED by a stray, the count would still be 2 and
# the guard would pass. (Corpus pollution happened twice while building #146,
# so this is an observed hazard, not a hypothetical one.)
_APPROVED_TRANSCRIPTS = {
    "5d4c699ad02e164da251d12c2d0afb109cfca9725f6719b9f01ee3bbbb28edd5.json",
    "6fc8c23a3f1d1b963f2cd78d8838b9dacd321130022a9dec85530bc0eda1b879.json",
}


def test_the_corpus_matches_an_exact_manifest_not_merely_a_count():
    """Pin WHICH recordings are committed, not just how many."""
    present = {p.name for p in RECORDED_TRANSCRIPTS.glob("*.json")}

    assert present == _APPROVED_TRANSCRIPTS, (
        "the committed corpus does not match its manifest; an unapproved "
        "recording usually means something recorded when it should have replayed"
    )


def test_every_committed_transcript_is_archetype_derived():
    """Positively confirm provenance, not merely the absence of repo markers.

    `test_the_committed_corpus_holds_only_archetype_content` is a NEGATIVE
    check: a transcript from some third source contains no repo markers either,
    so it would pass. Assert each recording actually came from the archetype
    fixture it is supposed to exercise."""
    for path in sorted(RECORDED_TRANSCRIPTS.glob("*.json")):
        record = json.loads(path.read_text())
        prompt = record["request"]["messages"][-1]["content"]
        assert "orders.py" in prompt and "ship_order" in prompt, (
            f"{path.name} is not derived from the 08-unrequested-change-risky-adjacent "
            "archetype; every committed recording must be traceable to a fixture"
        )


def test_replay_needs_no_api_key(tmp_path, monkeypatch):
    """The ordinary suite must run with no credentials at all.

    Proving "no live call" is not the same as proving "no API key required" —
    a client that read a key at construction would satisfy the former and still
    break a contributor with no credentials configured."""
    for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AZURE_API_KEY"):
        monkeypatch.delenv(var, raising=False)

    change, obligations, change_set = _adjacent_edit_case(tmp_path)
    result = classify_dispositions(
        [change], obligations, [], change_set,
        ScopeExpansionPolicy.LOOSE, replaying_client(),
    )[0]

    assert result.disposition.value == "separable"


def test_only_the_designated_capability_uses_recorded_responses():
    """Confirms the SCOPE EXCLUSION was not violated (#153).

    The task excluded converting the rest of the suite to recorded responses.
    That is a prohibition, and confirming it was not breached is part of
    acceptance — so assert the recorded-corpus helpers are used only under
    tests/prompts, and every other capability test still uses the injected
    helpers."""
    tests_root = pathlib.Path(__file__).resolve().parents[1]
    users = {
        path.relative_to(tests_root).as_posix()
        for path in tests_root.rglob("test_*.py")
        if "recorded_client(" in path.read_text() or "replaying_client(" in path.read_text()
    }

    assert users == {
        "prompts/test_corpus_mechanism.py",
        "prompts/test_disposition_prompt.py",
    }, f"recorded responses spread beyond the designated capability: {sorted(users)}"
