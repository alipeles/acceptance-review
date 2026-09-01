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

from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from acceptance.defects.pair_mapping import DEFAULT_PAIR_BATCH_SIZE
from acceptance.llm import DEFAULT_TRANSCRIPT_ROOT, Mode, ModelClient, TranscriptStore
from acceptance.review_state import DeterminismControls, LinkPrefilter, ReviewProvenance

# LiteLLM model string. Provider-agnostic: swap freely via --model / RunConfig.
DEFAULT_MODEL = "openai/gpt-5.4-mini"

# Stages that name their own model, overriding the run's (#317). A stage absent
# here runs on `model`, which is almost every stage.
#
# `decompose-summary` decides, per span of the mandate's opening summary, whether
# the obligations already derived from the bullets require that property.
# `gpt-5.4-mini` failed it in three different ways across three prompt versions:
# returning nothing, marking every span covered, and marking every span
# uncovered. Measured at about $0.011 per review for that one call.
#
# WHICH model is right for a stage is a judgement that belongs with the stage,
# not with this table's mechanism — the mechanism is what #317 delivers, and this
# entry is the one value that work measured.
DEFAULT_STAGE_MODELS = {
    "decompose-summary": "openai/gpt-5.4",
}

# Fixed by default so the "fixed seed/temperature + cached transcripts"
# strategy this module documents is actually in force. The value is arbitrary;
# only its fixedness matters. Leaving it None — as it was — meant half the
# documented determinism strategy was never wired up (#154). Changing it
# changes every request hash and so invalidates recorded transcripts, which is
# correct: a determinism control changed, so recordings must be re-verified.
DEFAULT_SEED = 0

# The pair stage's batch size lives with that stage
# (`defects/pair_mapping.py::DEFAULT_PAIR_BATCH_SIZE`) and is re-exported
# through `RunConfig` below. `DEFAULT_MAPPING_BATCH_SIZE` used to sit here and
# size the test-to-criterion mapping call (DR-164); #316 deleted that stage.

# There is no decompose batch size any more (#317). Derivation issues one call
# per requirement, and that is not a knob: it is what lets `source_quote` be an
# enum of the answering requirement's own spans, so raising it would remove the
# guarantee rather than trade accuracy for cost. See
# `requirement/obligations.py::ONE_REQUIREMENT_PER_CALL`.

# Obligation PAIRS per linking call (#144). Same determinism-control status as
# the two above.
#
# The unit is a pair, not an obligation, and that is the whole point. Asking one
# call to find every duplicate among N obligations is an all-pairs search — 276
# comparisons at N=24 — and it failed the way DR-164 predicts, by answering with
# the nearest plausible partner rather than the right one: a behaviour merged
# with the library implementing it, and an acceptance criterion attached to the
# wrong rule while its own rule sat unmerged beside it.
#
# Sweeping every pair removes the choice. Each judgment is one yes/no about two
# obligations, so "no" is as available as "yes", and no pair is ever uncompared —
# which is what partitioning the obligations themselves would have cost.
#
# It also makes inconsistency detectable. The relation is transitive by
# definition (identical truth conditions), so yes/yes/no over a triangle is not
# an intransitive relation but three answers that cannot all be right. Only a
# complete sweep can see that; inferring the third pair would destroy the
# evidence. See `docs/DR-144-pairwise-linking.md`.
#
# 25 rather than 12: a pair judgment is the smallest ask in the pipeline — two
# descriptions, one boolean — where a mapping item carries a test and an
# obligation, and a derivation item enumerates, types and quotes.
DEFAULT_LINK_PAIR_BATCH_SIZE = 25

# The model that embeds obligations for #259's linking prefilter. Separate from
# DEFAULT_MODEL: nothing is judged on an embedding, so the two are chosen on
# different grounds and swapped independently.
DEFAULT_EMBEDDING_MODEL = "voyage/voyage-3.5-lite"

# Cosine distance above which an obligation pair is not asked about (#259,
# DR-259). A determinism control in the seed's sense — it decides which
# questions reach the model — so changing it, or the embedding model, invalidates
# recorded linking transcripts.
#
# **Scale-specific to the embedding model above.** A different one needs
# recalibration, not this number.
#
# 0.10 is the under-merging side of a real trade, not a clean separator. On
# DR-259's calibration sample it kept 20/20 genuine merges and dropped 10/10
# spurious ones; on a held-out task file it kept 11 of 12, missing a genuine
# merge at 0.2257 where the two obligations paraphrased each other across levels
# of abstraction. No threshold does both — the nearest spurious merge sits at
# 0.116, below that — so this errs the way `linking.py` already errs: a missed
# merge leaves a redundant obligation the reader can see, while a spurious merge
# destroys a requirement silently. #211's link-precision measure is how the
# number gets settled properly.
DEFAULT_LINK_DISTANCE_THRESHOLD = 0.10


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
    # Per-stage overrides of `model` (#317). A determinism control of the same
    # kind as the seed — it decides which judge answers — and it reaches the
    # request the same way, through the model in the hash, so moving a stage onto
    # a different model invalidates that stage's recordings and no others.
    stage_models: dict[str, str] = Field(default_factory=lambda: dict(DEFAULT_STAGE_MODELS))
    mode: Mode = Mode.REPLAY
    temperature: float = 0.0
    seed: int | None = DEFAULT_SEED
    transcript_root: Path = Field(default=DEFAULT_TRANSCRIPT_ROOT)
    # A determinism control, but a stage-level one: it partitions the request
    # rather than parameterising the provider call, so it reaches the pair
    # stage through the pipeline instead of through build_client().
    #
    # It used to be `mapping_batch_size` and steer the test-to-criterion
    # mapper. #316 deleted that stage, and a control that reaches no stage is
    # worse than no control: it accepts a value, records nothing, and reads
    # as a knob that was turned.
    pair_batch_size: int = Field(default=DEFAULT_PAIR_BATCH_SIZE, ge=1)
    # And for obligation linking (#144), whose unit is a PAIR of obligations
    # rather than an obligation — see the constant's note.
    link_pair_batch_size: int = Field(default=DEFAULT_LINK_PAIR_BATCH_SIZE, ge=1)
    # #259's prefilter. Both are determinism controls that reach the linking
    # stage through the pipeline, like the batch sizes above, and both are
    # hashed into the linking request so a change invalidates its transcripts.
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    # Bounded by the range of cosine distance itself. 0 asks nothing; 2 asks
    # every pair and is the honest way to turn the prefilter off, which is why
    # it is not a separate boolean.
    link_distance_threshold: float = Field(default=DEFAULT_LINK_DISTANCE_THRESHOLD, ge=0.0, le=2.0)
    # A review-interpretation knob (consumed by the M3.5.3 separability
    # classifier), not a determinism control — so it deliberately does not
    # feed build_client() or provenance_for(). If we later want it recorded for
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
            embedding_model=self.embedding_model,
            stage_models=self.stage_models,
        )


def provenance_for(client: ModelClient) -> ReviewProvenance:
    """Stamp provenance from the client that issued the calls.

    Sourced from the client, not from `RunConfig`, because only the client knows
    which determinism controls the provider actually honoured — configuration
    knows what was asked for, and on a provider that discards controls those are
    different (#160). This is the single builder: the CLI pipeline and the
    benchmark hooks previously each had their own, which could disagree.

    No provider import: the client reads honoured controls off the transcripts
    it recorded or replayed, so a replay run stays free of the provider stack.
    """
    in_force = client.controls_in_force
    prefilter = client.prefilter_in_force
    return ReviewProvenance(
        determinism_mode=client.mode.value,
        model=client.model,
        controls_requested=DeterminismControls(temperature=client.temperature, seed=client.seed),
        controls_in_force=(None if in_force is None else DeterminismControls(**in_force)),
        request_partition_sizes=client.partition_sizes_in_force,
        stage_models=client.stage_models_in_force,
        link_prefilter=(None if prefilter is None else LinkPrefilter(**prefilter)),
    )
