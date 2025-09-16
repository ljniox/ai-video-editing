from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str


class Transcript(BaseModel):
    text: str
    segments: List[TranscriptSegment]
    note: Optional[str] = None

