from __future__ import annotations

from pathlib import Path
from typing import Optional

from autoedit.backends.base import Transcriber
from autoedit.schemas.transcript import Transcript, TranscriptSegment


class LocalTranscriber(Transcriber):
    """Local Whisper-based transcriber using faster-whisper if available.

    Falls back to a stub transcript if dependency is missing, with guidance to install.
    """

    def __init__(self, model: str = "medium") -> None:
        self.model_name = model

    def transcribe(self, audio_path: Path, language: Optional[str] = None) -> Transcript:
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except Exception as e:  # pragma: no cover - fallback path
            # Graceful fallback: return empty transcript with a hint
            hint = (
                "faster-whisper not installed. Install with 'pip install faster-whisper' "
                "or use the [full] extra: 'pip install -e .[full]'."
            )
            return Transcript(text="", segments=[], note=hint)

        model = WhisperModel(self.model_name, device="auto")
        segments_iter, info = model.transcribe(str(audio_path), language=language)

        segments = [
            TranscriptSegment(start=s.start, end=s.end, text=s.text or "") for s in segments_iter
        ]
        full_text = " ".join(s.text for s in segments).strip()
        return Transcript(text=full_text, segments=segments)

