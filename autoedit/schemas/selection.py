from __future__ import annotations

from typing import List

from pydantic import BaseModel

from .sequences import Segment


class Selection(BaseModel):
    shots: List[Segment]
