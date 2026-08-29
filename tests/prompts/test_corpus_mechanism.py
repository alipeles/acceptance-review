"""The recorded-corpus mechanism itself (#146).

`test_disposition_prompt.py` uses the corpus to test a capability's prompt.
These test the corpus machinery: that a prompt edit is detected, that the
failure explains itself, that recording cannot bypass the assertions, and that
the committed corpus holds what it should.
"""

import json
import pathlib

import pytest

from acceptance.config import DEFAULT_MODEL, DEFAULT_SEED, ScopeExpansionPolicy
from acceptance.coverage import disposition as disposition_module
from acceptance.coverage.disposition import classify_dispositions
from acceptance.llm import Mode, ModelClient, TranscriptNotFoundError, TranscriptStore
from tests.prompts.test_disposition_prompt import _adjacent_edit_case
from tests.support import (
    APPROVED_CORPUS_MODELS,
    RECORDED_TRANSCRIPTS,
    empty_corpus_client,
    recorded_client,
    replaying_client,
)


@pytest.fixture(autouse=True)
def _no_ambient_recording(monkeypatch):
    """Neutralise an ambient ACCEPTANCE_RECORD so these behave the same for
    every developer. Defence in depth only — the test that deliberately misses
    the corpus uses `replaying_client()`, which cannot record even if this
    fixture is removed."""
    monkeypatch.delenv("ACCEPTANCE_RECORD", raising=False)


def test_editing_a_prompt_fails_with_guidance_naming_the_unverified_change(tmp_path, monkeypatch):
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
            [change],
            obligations,
            [],
            change_set,
            ScopeExpansionPolicy.LOOSE,
            replaying_client(),
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


def test_the_corpus_is_recorded_under_production_determinism_controls():
    """A corpus recorded under different settings would prove nothing about
    production behaviour — so the client and every committed transcript must
    carry the real model AND the real determinism controls.

    Seed matters as much as model: it shapes the response, and building the
    corpus client by hand once silently dropped it (#154). Building from
    `RunConfig` keeps one source of truth."""
    client = recorded_client()
    assert client.model == DEFAULT_MODEL
    assert client.seed == DEFAULT_SEED
    assert client.temperature == 0.0

    for path in sorted(RECORDED_TRANSCRIPTS.glob("*.json")):
        record = json.loads(path.read_text())
        request = record["request"]
        # A closed set, not "any model": an unlisted model in the corpus means
        # something recorded that should not have (#158).
        assert request["model"] in APPROVED_CORPUS_MODELS, path.name
        # Controls are asserted on the REQUEST, which records what the run asked
        # for and is what the hash covers — so it is uniform across providers.
        assert request["seed"] == DEFAULT_SEED, path.name
        assert request["temperature"] == 0.0, path.name
        # What the provider actually honoured is a separate, per-provider fact.
        # Anthropic refuses `seed` and accepts only `temperature=1`, so a
        # recording against it is legitimately unpinned — but it must SAY so
        # rather than let the request's values imply determinism it never had.
        assert "controls_applied" in record, (
            f"{path.name} predates provider-honoured control recording (#158); "
            "re-record it so the corpus cannot imply controls that never applied."
        )


def test_the_corpus_covers_every_approved_model_not_just_one():
    """Provider-agnosticism has to be demonstrated, not merely permitted.

    The test above checks no UNAPPROVED model is present, which a corpus holding
    a single provider satisfies trivially. This asserts the other direction:
    every approved model is actually exercised. Without it, dropping the
    Anthropic recording and updating the manifest would end provider coverage
    while the whole suite still passed — and the M0.4 claim that models can be
    swapped would quietly go back to resting on a hand-run experiment (#158).
    """
    recorded = {
        json.loads(path.read_text())["request"]["model"]
        for path in RECORDED_TRANSCRIPTS.glob("*.json")
    }

    assert recorded == set(APPROVED_CORPUS_MODELS), (
        f"corpus covers {sorted(recorded)} but the approved set is "
        f"{sorted(APPROVED_CORPUS_MODELS)}; every approved model needs a "
        "recording, or provider-agnosticism is untested for the ones missing"
    )
    assert len(recorded) > 1, "a single-provider corpus cannot show portability"


def test_a_recorded_call_completed_against_a_provider_that_rejects_our_controls():
    """Recorded proof that the live path reaches a non-OpenAI model.

    Anthropic refuses `seed` and accepts only `temperature=1`, so before #158
    the call raised before contacting the model. Asserting `drop_params=True` is
    passed only shows what we ASK for; this shows a real call actually completed
    under those dropped controls and returned a schema-valid answer.

    That is what keeps provider-agnosticism from sliding back to being verified
    by hand: the evidence is committed, and it replays offline.
    """
    completed = {}
    for path in RECORDED_TRANSCRIPTS.glob("*.json"):
        record = json.loads(path.read_text())
        if record["request"]["model"].startswith("anthropic/"):
            completed[path.name] = record

    assert completed, "no recording proves a call to a control-rejecting provider completed"
    for name, record in completed.items():
        # Requested, per the hashed request...
        assert record["request"]["seed"] == DEFAULT_SEED, name
        assert record["request"]["temperature"] == 0.0, name
        # ...refused by the provider, and recorded as refused rather than assumed.
        assert record["controls_applied"] == {"seed": None, "temperature": None}, name
        # ...and the call still produced a usable answer.
        assert json.loads(record["response"])["disposition"] in {
            "in_service",
            "separable",
            "risky",
        }, name


def test_the_default_model_is_one_the_corpus_actually_holds():
    """Ties the production default to the recorded evidence.

    Every prompt-quality test builds its request from `DEFAULT_MODEL`, so a
    default that no recording covers turns the whole prompt suite into
    `TranscriptNotFoundError`. Asserting the link makes a default change a
    deliberate act — swap it, and you must re-record — rather than silent drift.
    """
    assert DEFAULT_MODEL in APPROVED_CORPUS_MODELS

    recorded = {
        json.loads(path.read_text())["request"]["model"]
        for path in RECORDED_TRANSCRIPTS.glob("*.json")
    }
    assert DEFAULT_MODEL in recorded


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

    assert len(corpus) == len(_APPROVED_TRANSCRIPTS), (
        f"expected {len(_APPROVED_TRANSCRIPTS)} recorded transcripts, found {len(corpus)}: "
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
    client = replaying_client(completion_fn=must_not_be_called)

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
    empty_store_client = empty_corpus_client(tmp_path / "empty-corpus")

    with pytest.raises(TranscriptNotFoundError):
        classify_dispositions(
            [change],
            obligations,
            [],
            change_set,
            ScopeExpansionPolicy.LOOSE,
            empty_store_client,
        )


def test_a_known_defect_survives_an_unrelated_prompt_edit(tmp_path):
    """A recorded failing case must not be lost when some OTHER prompt changes.

    The corpus is keyed by request hash, so an edit anywhere in a prompt makes
    that request miss. The hazard is a mechanism that responds to a miss by
    quietly re-recording or falling back to a live call: the known defect would
    then stop failing, and a tracked problem would silently disappear from the
    suite. (#152 was exactly such a tracked problem, held by an
    `xfail(strict=True)` until #158 found and fixed its cause.)

    Assert the miss stays a miss: an edited prompt raises rather than healing
    itself, so the failure remains visible until someone re-records
    deliberately and re-verifies the assertions.
    """
    change, obligations, change_set = _adjacent_edit_case(tmp_path)

    # Unedited: the committed recording is found, so the case still evaluates.
    baseline = classify_dispositions(
        [change],
        obligations,
        [],
        change_set,
        ScopeExpansionPolicy.LOOSE,
        replaying_client(),
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
                [change],
                obligations,
                [],
                change_set,
                ScopeExpansionPolicy.LOOSE,
                replaying_client(),
            )

    # ...and the committed corpus is untouched by the attempt.
    assert len(list(RECORDED_TRANSCRIPTS.glob("*.json"))) == len(_APPROVED_TRANSCRIPTS)


# The exact recordings this suite replays. A count alone is not enough: if an
# approved transcript were REPLACED by a stray, the count would still be 2 and
# the guard would pass. (Corpus pollution happened twice while building #146,
# so this is an observed hazard, not a hypothetical one.)
#
# Each entry carries the marker that proves where it came from, so provenance is
# asserted per recording rather than against one hardcoded fixture. A second
# recorded capability (#144) made the single-fixture check untenable: it would
# have had to be loosened to an OR, and an OR over markers passes for a
# transcript containing neither.
#
# **The corpus grew from 7 to 25 with #317, and the growth is the change itself.**
# Derivation now issues one call per requirement rather than one per batch of
# eight, so the eleven-requirement invoice task that recorded 2 transcripts
# records 19: ten bullets, the summary step, and the calls that author
# obligations for the summary spans it left uncovered. The two `_SummarySpans`
# recordings are against `openai/gpt-5.4` rather than the run's model, which is
# the recorded evidence that a stage may name its own model.
#
# Grouped by response schema and model, and generated from what was recorded
# rather than hand-listed — the ids are request hashes, so they are not
# authorable by hand and carry no meaning beyond identity.
_APPROVED_TRANSCRIPTS = {
    # _Decomposition, openai/gpt-5.4-mini — 19 recording(s)
    "0db605cd8cd79d4e96b2b00eb0cfb97e08e363ea3fa4d8b67a5257d33d7e9b4b.json": (
        "invoice",
        "CSV",
    ),
    "0e54ccb1b994dbd7414eb804023bd7e0c747756725ee333c5b86ac8f4dcb1110.json": (
        "invoice",
        "CSV",
    ),
    "26008f3105fd2990bd6cdb6c211dd81019dcd057b732cfc9eafcadafc17d2627.json": (
        "invoice",
        "CSV",
    ),
    "386663bc208e63c446b8ed03ca6e94ed9a77f25412788158506e8106e1edbfcf.json": (
        "invoice",
        "CSV",
    ),
    "4cbdec07c03d64fcabfc8f08da97d5e37b011ca233780f4b5d063591aea3c49f.json": (
        "invoice",
        "CSV",
    ),
    "4ce568d1bd2c53de22936ccb532443a63c8be0d051581b29918660bac7b002e5.json": (
        "invoice",
        "CSV",
    ),
    "5ddc8915319828f44218b4945dcdc4c24ca3bdb2d23282deb3b54bf1919e0040.json": (
        "invoice",
        "CSV",
    ),
    "7a6f5c1d2ba5cb3abf47579535bb63764ca57e28d749bdc52edfe0bd9677118c.json": (
        "invoice",
        "CSV",
    ),
    "832eb1033ea699d8d9b9760860a508443fdfaf0838941dbdcd22133dd97409f1.json": (
        "invoice",
        "CSV",
    ),
    "949f73831132b5d9290e4d2bdc8cf21e3d1f3c79096ccfc2623fed5be734fc3f.json": (
        "invoice",
        "CSV",
    ),
    "9b3bdd7227e632dd543fc3413711b192d4cc7e74f93d1a45c2c2ba6dd30f9ee6.json": (
        "invoice",
        "CSV",
    ),
    "a362ebf22aa06b6aa78eb9646890dc29b7288195892418423bfd18d9377f06f5.json": (
        "invoice",
        "CSV",
    ),
    "b0b789be229a87b9096031e1edc0d88fa488e1f949df864be5632be1a58ce70d.json": (
        "invoice",
        "CSV",
    ),
    "c8b9491a44ea3813a5278efc85f819806bf08b4e52cb65aeeea77f11a58c6e53.json": (
        "invoice",
        "CSV",
    ),
    "cf319802ba28e5af17cd7e568c98571e98c6d134b70ea8d25d5585faf19725c8.json": (
        "invoice",
        "CSV",
    ),
    "d1118d9bc44851922064ecc3460420bba83e4136e2b905ef52fb2e5576983a6e.json": (
        "invoice",
        "CSV",
    ),
    "d63bf090aac4b8e9a3ea5d8585993dfb05256b5cf26fe21d2e24c45a06f3696a.json": (
        "invoice",
        "CSV",
    ),
    "ec291f98c787637453b50a03ea4cd48fb3a4c8adcf86b665109749585706ef3d.json": (
        "invoice",
        "CSV",
    ),
    "f86d8eb1202ac352ded60177bc2f04a2dec9e55db82eff9a140563f5c3da211e.json": (
        "invoice",
        "CSV",
    ),
    # _DispositionJudgment, anthropic/claude-sonnet-5 — 1 recording(s)
    "e601a647baf1a5f1e0f06f0123daa9d21befb9cacca0781c80905feeec5087d0.json": (
        "orders.py",
        "ship_order",
    ),
    # _DispositionJudgment, openai/gpt-5.4-mini — 2 recording(s)
    "d1f41f92c113058057149c4a995e8b7732663d26007399ee86903c038e9dcca2.json": (
        "orders.py",
        "ship_order",
    ),
    "f849fc68649871fe2ad953733b0355379f13ab0ae4928e181878d3973363000a.json": (
        "orders.py",
        "ship_order",
    ),
    # _SummarySpans, openai/gpt-5.4 — 2 recording(s)
    "94cb56e14aa637b5a3d8a71371422f5674305f7eade464a12217ac5fa2b411df.json": (
        "invoice",
        "CSV",
    ),
    "9c623b442c391c1781307a53af26e5a98ea17b8db0e86ca98a431b35eb7e2f4c.json": (
        "invoice",
        "CSV",
    ),
    # _Verdicts, openai/gpt-5.4-mini — 1 recording(s)
    "017183bb4468ccade80b41f1a5319c3662c7c53594b0350a7b6c421449cbef84.json": (
        "invoice",
        "CSV",
    ),
}


def test_the_corpus_matches_an_exact_manifest_not_merely_a_count():
    """Pin WHICH recordings are committed, not just how many."""
    present = {p.name for p in RECORDED_TRANSCRIPTS.glob("*.json")}

    assert present == set(_APPROVED_TRANSCRIPTS), (
        "the committed corpus does not match its manifest; an unapproved "
        "recording usually means something recorded when it should have replayed"
    )


def test_every_committed_transcript_is_fixture_derived():
    """Positively confirm provenance, not merely the absence of repo markers.

    `test_the_committed_corpus_holds_only_archetype_content` is a NEGATIVE
    check: a transcript from some third source contains no repo markers either,
    so it would pass. Assert each recording actually came from the fixture it is
    supposed to exercise, using the markers the manifest declares for it — so a
    recording cannot be traced to *some* fixture, only to its own."""
    for path in sorted(RECORDED_TRANSCRIPTS.glob("*.json")):
        markers = _APPROVED_TRANSCRIPTS.get(path.name)
        assert markers is not None, f"{path.name} is not in the manifest"
        record = json.loads(path.read_text())
        prompt = record["request"]["messages"][-1]["content"]
        for marker in markers:
            assert marker in prompt, (
                f"{path.name} does not carry {marker!r}, the marker its manifest "
                "entry claims; every committed recording must be traceable to a fixture"
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
        [change],
        obligations,
        [],
        change_set,
        ScopeExpansionPolicy.LOOSE,
        replaying_client(),
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
        "prompts/test_decomposition_prompt.py",
        "prompts/test_disposition_prompt.py",
        "prompts/test_linking_prompt.py",
    }, f"recorded responses spread beyond the designated capability: {sorted(users)}"


def test_corpus_clients_source_their_controls_rather_than_duplicating_them():
    """Asserting the controls equal the DEFAULTS is not enough.

    A helper that hardcoded `seed=DEFAULT_SEED` would satisfy that too, and
    would then silently drift the moment configuration changed — which is
    exactly the bug this fixed (the helper built a ModelClient by hand and
    dropped the seed entirely). Pass a NON-DEFAULT override: only a client that
    genuinely sources its controls from `RunConfig` can honour it."""
    overridden = replaying_client(model="openai/some-other-model")

    assert overridden.model == "openai/some-other-model"
    # ...while the controls not overridden still come from the shared config.
    assert overridden.seed == DEFAULT_SEED
    assert overridden.temperature == 0.0
