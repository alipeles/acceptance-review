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

from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field

from acceptance.llm import DEFAULT_TRANSCRIPT_ROOT, Mode, ModelClient, TranscriptStore
from acceptance.review_state import ReviewProvenance

DEFAULT_MODEL = "anthropic/claude-sonnet-5"


class RunConfig(BaseModel):
    """Configurable model, determinism mode, seed, and temperature for a run.

    Defaults to REPLAY so the CLI and CI never issue a live call — or need an
    API key — unless a run explicitly opts into RECORD.
    """

    model_config = ConfigDict(extra="forbid")

    model: str = DEFAULT_MODEL
    mode: Mode = Mode.REPLAY
    temperature: float = 0.0
    seed: int | None = None
    transcript_root: Path = Field(default=DEFAULT_TRANSCRIPT_ROOT)

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
