from __future__ import annotations

import os
from dataclasses import dataclass
from itertools import cycle
from threading import Lock
from typing import List, Optional

import requests

from autoedit.schemas.transcript import Transcript, TranscriptSegment


@dataclass
class LightningConfig:
    base_url: str
    api_key: Optional[str] = None
    timeout_s: int = 60
    api_keys: Optional[List[str]] = None


class LightningTranscriber:
    """HTTP client for the Beam Cloud Whisper service (legacy Lightning naming).

    For MVP, requires an already-uploaded audio URL. Chunking/upload is out of scope here.
    """

    def __init__(self, config: LightningConfig) -> None:
        self.config = config
        self._api_keys = [k for k in (config.api_keys or []) if k]
        self._api_cycle = cycle(self._api_keys) if self._api_keys else None
        self._api_cycle_lock = Lock() if self._api_cycle else None
        self._fallback_api_key = self.config.api_key or os.getenv("LIGHTNING_API_KEY")

    def _choose_api_key(self) -> Optional[str]:
        if self._api_cycle and self._api_cycle_lock:
            with self._api_cycle_lock:
                return next(self._api_cycle)
        return self._fallback_api_key

    def transcribe_url(
        self, audio_url: str, lang: Optional[str] = None, model: str = "medium"
    ) -> Transcript:
        headers = {}
        api_key = self._choose_api_key()
        if api_key:
            headers["X-API-Key"] = api_key
        payload = {"audio_url": audio_url, "lang": lang, "model": model}
        resp = requests.post(
            f"{self.config.base_url.rstrip('/')}/transcribe",
            json=payload,
            headers=headers,
            timeout=self.config.timeout_s,
        )
        resp.raise_for_status()
        data = resp.json()
        segments = [
            TranscriptSegment(
                start=s.get("start", 0.0), end=s.get("end", 0.0), text=s.get("text", "")
            )
            for s in data.get("segments", [])
        ]
        return Transcript(text=data.get("text", ""), segments=segments)
