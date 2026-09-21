"""Rank each defect's candidate tests by similarity, so the judge can stop early (#348).

The static pair judgement asks, for every defect and every candidate test,
whether the test would fail if the code had the defect, and the answer is *no*
about 99% of the time. `defects/support.py` covers a defect at one kill, so once
a defect has one, the rest of its answers cannot move the rating. This module
decides the ORDER the judge reads a defect's tests in, so that the kill — where
there is one — comes early and the judge can stop.

## What the ranking is and is not

**It allocates attention; it decides nothing.** A defect with no kill has every
one of its tests asked about, exactly as without ranking, so a worse ranking
costs judgements and cannot change a rating. That is why the embedding model is
the one the review is already configured with rather than a code-specialised
one: `docs/experiments/rank-prefilter/FINDINGS.md` measured the configured
`voyage-3.5-lite` at 2.8 to 7.6 judgements per covered defect on three recorded
reviews, against 3.7 to 7.5 for `voyage-code-4`.

**Nothing about it reaches the judge.** The rank decides which pairs are in a
request; the request itself is built exactly as before, and it says nothing
about order, rank, or what other tests already caught.

## What is embedded

Each defect's `description` and each test's source — the two texts the judge
itself is shown, and the pair the measurement ranked on. Symmetric: no
`input_type`, because `build_embedding_request` sends none, and adding one would
move the request key under every recorded linking transcript (FINDINGS.md, the
re-score section).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from acceptance.defects.reachability import Pair
from acceptance.llm import ModelClient

__all__ = ["DEFAULT_STOP_AFTER_KILLS", "EMBED_CHUNK", "EMBED_TOKEN_BUDGET", "rank_pairs"]

# How many of a defect's tests must be recorded as catching it before the judge
# stops asking about it. One, because `support.py` covers a defect at one kill.
# Two was proposed for redundancy against DR-180's judgement instability and
# measured at 10.4 to 21.1 judgements per covered defect — a defect with exactly
# one kill never reaches a second and pays for every test (FINDINGS.md).
DEFAULT_STOP_AFTER_KILLS = 1

# The most inputs, and the most estimated tokens, one embedding request carries.
# Both fixed, so the split is a pure function of the input list and a replay
# finds every transcript. A count alone is not enough: test sources vary by two
# orders of magnitude, and 128 long ones overrun a provider's per-request token
# cap where 128 short ones do not. Tokens are estimated at four characters each,
# which only has to be good enough to stay well under the cap.
EMBED_CHUNK = 128
EMBED_TOKEN_BUDGET = 60_000

# Shown to the embedding model for a test whose source could not be read, the
# same stand-in the judge's prompt uses. An empty input is rejected by providers.
_NO_SOURCE = "(source unavailable)"


def _similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Cosine similarity; a zero vector ranks last rather than dividing by zero.

    Written here rather than imported from `requirement/linking.py`, whose
    `cosine_distance` is the same arithmetic: linking imports the run
    configuration, which imports this stage, so the import would be circular.
    """
    dot = sum(x * y for x, y in zip(left, right))
    norms = math.sqrt(sum(x * x for x in left)) * math.sqrt(sum(y * y for y in right))
    return dot / norms if norms else -1.0


def _chunks(texts: list[str]) -> list[list[str]]:
    """Consecutive runs of `texts`, each within both request limits.

    A single text over the token budget still goes, alone: it is one test's
    source, and leaving it out would leave that test unranked.
    """
    chunks: list[list[str]] = []
    current: list[str] = []
    spent = 0
    for text in texts:
        cost = max(1, len(text) // 4)
        if current and (len(current) >= EMBED_CHUNK or spent + cost > EMBED_TOKEN_BUDGET):
            chunks.append(current)
            current, spent = [], 0
        current.append(text)
        spent += cost
    if current:
        chunks.append(current)
    return chunks


def _embed(texts: list[str], client: ModelClient, stage: str) -> list[Sequence[float]]:
    vectors: list[Sequence[float]] = []
    for chunk in _chunks(texts):
        vectors.extend(client.embed(chunk, stage=stage))
    return vectors


def rank_pairs(
    pairs: Sequence[Pair], client: ModelClient, stage: str
) -> dict[tuple[str, str], int]:
    """Each pair's 1-based rank among its own defect's pairs, most similar first.

    Ties — identical vectors, or a test repeated — break on test id, so the
    ranking is a pure function of the embeddings and never of input order.

    The texts are de-duplicated and sorted before embedding, so the request is
    determined by WHAT is ranked and not by the order pairs arrived in; two runs
    over the same defects and tests replay the same transcript.
    """
    if not pairs:
        return {}
    descriptions = {pair.defect.id: pair.defect.description or pair.defect.id for pair in pairs}
    sources = {pair.test.test_id: pair.test.source or _NO_SOURCE for pair in pairs}
    texts = sorted(set(descriptions.values()) | set(sources.values()))
    vector_of = dict(zip(texts, _embed(texts, client, stage)))

    by_defect: dict[str, list[Pair]] = {}
    for pair in pairs:
        by_defect.setdefault(pair.defect.id, []).append(pair)

    ranks: dict[tuple[str, str], int] = {}
    for defect_id, defect_pairs in by_defect.items():
        anchor = vector_of[descriptions[defect_id]]
        ordered = sorted(
            defect_pairs,
            key=lambda pair: (
                -_similarity(anchor, vector_of[sources[pair.test.test_id]]),
                pair.test.test_id,
            ),
        )
        for position, pair in enumerate(ordered, start=1):
            ranks[pair.key] = position
    return ranks
