"""Prompt-quality tests for unit classification (#436), over REAL responses.

`tests/requirement/test_claims.py` injects the decisions, so it cannot fail when
the prompt is edited. These replay the committed corpus, so they assert what the
model actually decides. Re-record with:

    ACCEPTANCE_RECORD=1 pytest tests/prompts/test_claims_prompt.py -q

Two mandates, both under `tests/fixtures/claims/`:

- `today-then-change.md` opens with a sentence describing how the system behaves
  today and follows it with the change. Under the old parse, a sentence about
  today's behaviour under `# Task` became an obligation to keep it (#212).
- `432-issue-as-filed.md` is #432's issue body exactly as filed. The old parse
  found no requirement in it at all: its opening line has no heading and its
  Acceptance bullets sit under a heading the parser does not recognise. #436's
  Acceptance names it, so it is recorded here although it is this repository's
  own text; it is an issue body, not a diff.
"""

from __future__ import annotations

import pathlib

import pytest

from acceptance.requirement.claims import build_claims
from acceptance.requirement.task_file import parse_task_file
from tests.support import recorded_client

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures" / "claims"


def _claims(name: str):
    text = (_FIXTURES / name).read_text(encoding="utf-8")
    return text, build_claims(parse_task_file(text), recorded_client())


@pytest.fixture(scope="module")
def today_then_change():
    return _claims("today-then-change.md")


@pytest.fixture(scope="module")
def issue_432():
    return _claims("432-issue-as-filed.md")


def test_a_sentence_about_todays_behaviour_yields_no_claim(today_then_change):
    _, claim_set = today_then_change
    claimed = [claim.text for claim in claim_set.claims]

    assert not any("local time today" in text for text in claimed), claimed


def test_the_change_that_follows_it_yields_one_claim(today_then_change):
    _, claim_set = today_then_change
    claimed = [claim.text for claim in claim_set.claims]

    assert [text for text in claimed if "UTC" in text] == ["Make it\nwrite every date in UTC."], (
        claimed
    )


def _acceptance_bullets(text: str) -> list[tuple[int, int]]:
    """(start, end) offsets of each bullet under `## Acceptance`."""
    start = text.index("## Acceptance")
    bullets = []
    offset = start
    for line in text[start:].splitlines(keepends=True):
        if line.startswith("- "):
            bullets.append((offset, offset + len(line.rstrip("\n"))))
        offset += len(line)
    return bullets


def test_every_acceptance_bullet_of_432_yields_at_least_one_claim(issue_432):
    text, claim_set = issue_432
    bullets = _acceptance_bullets(text)

    assert len(bullets) == 4
    for start, end in bullets:
        inside = [c for c in claim_set.claims if start <= c.span.start and c.span.end <= end]
        assert inside, f"no claim from Acceptance bullet: {text[start:end]!r}"


def test_every_claim_of_432_is_a_verbatim_span(issue_432):
    text, claim_set = issue_432

    assert claim_set.claims
    for claim in claim_set.claims:
        assert text[claim.span.start : claim.span.end] == claim.text
