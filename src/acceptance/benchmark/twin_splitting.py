"""Twin-splitting: does the mapper give one answer to a demand stated twice? (#173)

Two obligations that state the **same demand** must receive the same answer from
the mapping stage. A test mapped to one of them and withheld from the other is an
error whichever way round it is, and — this is the point — deciding that needs no
hand-labelled ground truth. That makes it the one mapping-quality figure that can
be recomputed over committed data at any time, with no model calls.

The source is the rendered reports under `dogfood-logs/`, which are committed and
list each obligation's text with the tests mapped to it. `instability.py` (#189)
measures how far a judgement *moves* between runs; this measures whether a single
run is self-consistent about demands it stated twice.

## The confound — read before using any figure below identity

Only **byte-identical** obligation text makes "mapped to exactly one" an
unambiguous error. As the pair gets less similar, mapping a test to just one of
them stops being a mistake and starts being correct discrimination, so the split
rate rises for a mapper with no defect at all. `by_band()` therefore reports the
bands separately and never totals them, and `identical_only()` is the figure to
quote when the number has to stand on its own.

Measured 2026-08-21 over 78 reports spanning 76 distinct decompositions: 3 of 16
opportunities split on byte-identical text, and 200/428 across all candidate
pairs at similarity >= 0.55. See `docs/DR-173-mapping-twin-splitting.md`.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from itertools import combinations
from pathlib import Path

from acceptance.model_base import PersistableModel

# Words carrying no discriminating signal between two obligation statements.
_STOP = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "be",
        "been",
        "being",
        "of",
        "to",
        "in",
        "on",
        "for",
        "by",
        "with",
        "that",
        "which",
        "and",
        "or",
        "not",
        "it",
        "its",
        "this",
        "those",
        "these",
        "as",
        "at",
        "from",
        "when",
        "whether",
        "any",
        "each",
        "every",
        "no",
        "non",
        "than",
        "then",
        "same",
        "other",
        "another",
        "only",
        "just",
        "does",
        "do",
        "did",
        "has",
        "have",
        "had",
        "was",
        "were",
        "will",
        "would",
        "can",
        "may",
        "must",
        "should",
        "shall",
        "into",
        "over",
        "under",
        "about",
        "across",
        "per",
        "via",
        "but",
        "if",
    }
)

_OBLIGATION = re.compile(r"^  (\d+)\. (.+)$")
_ITEM = re.compile(r"^\s+(\d+)\.(\d+)\s+(.+?)\s*$")
_SECTION = re.compile(r"^\s+(requirements|code evidence|test evidence|open question)")


def _significant(text: str) -> frozenset[str]:
    return frozenset(
        t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP and len(t) > 2
    )


def similarity(left: str, right: str) -> float:
    """Jaccard overlap of the significant words of two obligation statements."""
    a, b = _significant(left), _significant(right)
    return len(a & b) / len(a | b) if (a | b) else 0.0


class ReportMapping(PersistableModel):
    """One rendered report: each obligation's text, and the tests mapped to it."""

    source: str
    obligations: dict[int, str]
    mapped_tests: dict[int, list[str]]


class TwinPair(PersistableModel):
    """Two obligations of one report that may state the same demand.

    `split` counts tests mapped to exactly one of the two; `shared` counts tests
    mapped to both. Only when `identical` is true is `split` certainly an error.
    """

    source: str
    left: str
    right: str
    similarity: float
    identical: bool
    shared: int
    split: int

    @property
    def opportunities(self) -> int:
        return self.shared + self.split


def parse_report(path: Path | str) -> ReportMapping:
    """Read one rendered `check` report into its obligation -> mapped-test index."""
    path = Path(path)
    obligations: dict[int, str] = {}
    mapped: dict[int, list[str]] = {}
    current: int | None = None
    in_tests = False

    for raw in path.read_text(errors="replace").splitlines():
        heading = _OBLIGATION.match(raw)
        if heading:
            current = int(heading.group(1))
            obligations[current] = heading.group(2).strip()
            mapped[current] = []
            in_tests = False
            continue
        if current is None:
            continue
        if _SECTION.match(raw):
            in_tests = raw.strip().startswith("test evidence")
            continue
        item = _ITEM.match(raw)
        if item:
            # Code evidence cites a diff hunk; only test ids carry `::`.
            if in_tests and int(item.group(1)) == current and "::" in item.group(3):
                mapped[current].append(item.group(3))
            continue
        # A wrapped obligation statement: indented prose before any section marker.
        if raw.strip() and not in_tests and raw.startswith("     ") and not mapped[current]:
            obligations[current] += " " + raw.strip()

    return ReportMapping(source=str(path), obligations=obligations, mapped_tests=mapped)


def twin_pairs(report: ReportMapping, threshold: float = 0.55) -> list[TwinPair]:
    """Every obligation pair of one report at or above `threshold` similarity."""
    pairs: list[TwinPair] = []
    for a, b in combinations(sorted(report.obligations), 2):
        left, right = report.obligations[a], report.obligations[b]
        score = similarity(left, right)
        if score < threshold:
            continue
        ta, tb = set(report.mapped_tests[a]), set(report.mapped_tests[b])
        pairs.append(
            TwinPair(
                source=report.source,
                left=left,
                right=right,
                similarity=score,
                identical=left.strip() == right.strip(),
                shared=len(ta & tb),
                split=len(ta ^ tb),
            )
        )
    return pairs


def collect(reports: Iterable[Path | str], threshold: float = 0.55) -> list[TwinPair]:
    """Twin pairs across many reports. Reports with no mapped tests are skipped."""
    out: list[TwinPair] = []
    for path in reports:
        parsed = parse_report(path)
        if len(parsed.obligations) < 2 or not any(parsed.mapped_tests.values()):
            continue
        out.extend(twin_pairs(parsed, threshold))
    return out


def split_rate(pairs: Sequence[TwinPair]) -> float | None:
    """Share of opportunities where a test reached exactly one of the two.

    `None` when no test reached either, which is absence of evidence rather than
    a rate of zero.
    """
    shared = sum(p.shared for p in pairs)
    split = sum(p.split for p in pairs)
    return split / (shared + split) if shared + split else None


def identical_only(pairs: Sequence[TwinPair]) -> list[TwinPair]:
    """The subset whose two statements are byte-identical — the unambiguous errors."""
    return [p for p in pairs if p.identical]


_BANDS: tuple[tuple[str, float, float], ...] = (
    ("0.90-0.99", 0.90, 1.00),
    ("0.80-0.89", 0.80, 0.90),
    ("0.70-0.79", 0.70, 0.80),
    ("0.60-0.69", 0.60, 0.70),
    ("0.55-0.59", 0.55, 0.60),
)


def by_band(pairs: Sequence[TwinPair]) -> dict[str, list[TwinPair]]:
    """Group by similarity, identical text first, so bands are never summed.

    A rising split rate across these bands is NOT evidence of a defect: below
    identity, mapping a test to only one of two obligations is often correct.
    """
    grouped: dict[str, list[TwinPair]] = {"identical": identical_only(pairs)}
    for name, low, high in _BANDS:
        grouped[name] = [p for p in pairs if not p.identical and low <= p.similarity < high]
    return grouped
