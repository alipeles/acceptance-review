"""Run configuration & determinism controls (M0.5, plan §3.2 "determinism strategy").

Stage 1 resolves the determinism strategy as **fixed seed/temperature + cached
transcripts** (record-if-missing, then replay). This makes two recorded runs
over the same input reproduce byte-identical review state: identical requests
hit identical transcripts, and both requests and review state serialize
canonically (serialization.py). The alternative from §3.2 — N-sample majority
with disclosed variance — is deferred to the benchmark harness (M-B0.4), which
layers variance reporting on top of these controls rather than replacing them.

`RunConfig` is the single surface for those controls; it builds the
`ModelClient` the pipeline calls and stamps a matching `ReviewProvenance` onto
the review so a reader can tell how it was produced.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field

from acceptance.llm import DEFAULT_TRANSCRIPT_ROOT, Mode, ModelClient, TranscriptStore
from acceptance.review_state import ReviewProvenance

# LiteLLM model string. Provider-agnostic: swap freely via --model / RunConfig.
DEFAULT_MODEL = "openai/gpt-5.4-mini"

# Fixed by default so the "fixed seed/temperature + cached transcripts"
# strategy this module documents is actually in force. The value is arbitrary;
# only its fixedness matters. Leaving it None — as it was — meant half the
# documented determinism strategy was never wired up (#154). Changing it
# changes every request hash and so invalidates recorded transcripts, which is
# correct: a determinism control changed, so recordings must be re-verified.
DEFAULT_SEED = 0


class ScopeExpansionPolicy(str, Enum):
    """How tolerant the review is of changes beyond the mandate (DR-081
    decision 4). Where the acceptable-expansion line sits is a shop norm, so
    it is a policy knob, not a hardcoded verdict — it tunes the separability
    classifier (M3.5.3), not detection. Default is `strict`, matching DR-081's
    recall-forward stance (surface more, let the user dismiss)."""

    STRICT = "strict"  # flag more expansion as separable/risky
    LOOSE = "loose"  # tolerate more bundled work


class RunConfig(BaseModel):
    """Configurable model, determinism mode, seed, and temperature for a run.

    Defaults to REPLAY so the CLI and CI never issue a live call — or need an
    API key — unless a run explicitly opts into RECORD.
    """

    model_config = ConfigDict(extra="forbid")

    model: str = DEFAULT_MODEL
    mode: Mode = Mode.REPLAY
    temperature: float = 0.0
    seed: int | None = DEFAULT_SEED
    transcript_root: Path = Field(default=DEFAULT_TRANSCRIPT_ROOT)
    # A review-interpretation knob (consumed by the M3.5.3 separability
    # classifier), not a determinism control — so it deliberately does not
    # feed build_client() or provenance(). If we later want it recorded for
    # traceability, that is a deliberate addition to ReviewProvenance.
    scope_expansion_policy: ScopeExpansionPolicy = ScopeExpansionPolicy.STRICT

    def build_client(self, completion_fn: Callable[..., Any] | None = None) -> ModelClient:
        return ModelClient(
            model=self.model,
            mode=self.mode,
            store=TranscriptStore(self.transcript_root),
            temperature=self.temperature,
            seed=self.seed,
            completion_fn=completion_fn,
        )

    def provenance(self) -> ReviewProvenance:
        return ReviewProvenance(
            determinism_mode=self.mode.value,
            model=self.model,
            temperature=self.temperature,
            seed=self.seed,
        )
