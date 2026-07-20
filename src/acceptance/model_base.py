"""Shared base for typed, persisted schemas across the checker and benchmark.

One definition of "strict, round-trippable pydantic model" used by both
review_state.py and benchmark/case.py, so serialization behaves identically
everywhere rather than being redefined per module.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PersistableModel(BaseModel):
    """Strict fields (no silent extras), uniform to_dict()/from_dict()."""

    model_config = ConfigDict(extra="forbid")

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict):
        return cls.model_validate(data)
