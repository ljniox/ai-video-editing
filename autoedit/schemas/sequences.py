from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class Segment(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    source: str


class Sequences(BaseModel):
    segments: List[Segment]

