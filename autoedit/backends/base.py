from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from autoedit.schemas.transcript import Transcript


class Transcriber(ABC):
    @abstractmethod
    def transcribe(
        self, audio_path: Path, language: Optional[str] = None
    ) -> Transcript:  # pragma: no cover - interface
        raise NotImplementedError
