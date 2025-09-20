from __future__ import annotations

import hashlib
import os
import tempfile
import uuid
from contextlib import suppress
from pathlib import Path
from typing import Dict, Optional, Tuple

import httpx
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel


class TranscribeRequest(BaseModel):
    audio_url: str
    lang: Optional[str] = None
    model: str = "medium"


class TranscribeResponse(BaseModel):
    text: str
    segments: list[dict]
    hash: Optional[str] = None


app = FastAPI(title="AutoEdit STT Service (MVP)")

_MODEL_CACHE: Dict[str, object] = {}
_DOWNLOAD_TIMEOUT_S = float(os.getenv("DOWNLOAD_TIMEOUT_S", "30"))


@app.get("/healthz")
def healthz():  # pragma: no cover - simple endpoint
    return {"status": "ok"}


def _check_api_key(x_api_key: Optional[str]):
    required = os.getenv("API_KEY")
    if required and x_api_key != required:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_audio(url: str) -> Path:
    suffix = Path(httpx.URL(url).path).suffix or ".bin"
    tmp_path = Path(tempfile.gettempdir()) / f"autoedit-{uuid.uuid4().hex}{suffix}"
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=_DOWNLOAD_TIMEOUT_S) as resp:
            resp.raise_for_status()
            with tmp_path.open("wb") as fh:
                for chunk in resp.iter_bytes(64 * 1024):
                    if chunk:
                        fh.write(chunk)
    except httpx.HTTPError as exc:
        with suppress(FileNotFoundError):
            tmp_path.unlink()
        raise HTTPException(status_code=502, detail=f"Failed to download audio: {exc}") from exc
    return tmp_path


def _resolve_audio_source(audio_url: str) -> Tuple[Path, bool]:
    lowered = audio_url.lower()
    if lowered.startswith("http://") or lowered.startswith("https://"):
        path = _download_audio(audio_url)
        return path, True
    if lowered.startswith("file://"):
        path = Path(audio_url[7:])
    else:
        path = Path(audio_url)
    if not path.exists():
        raise HTTPException(status_code=400, detail="Audio source not found")
    return path, False


def _get_model(model_name: str):
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception as exc:  # pragma: no cover - dependency missing in env
        raise HTTPException(status_code=503, detail="faster-whisper not available") from exc

    if model_name not in _MODEL_CACHE:
        device = os.getenv("STT_DEVICE", "auto")
        compute_type = os.getenv("STT_COMPUTE_TYPE")
        kwargs = {"device": device}
        if compute_type:
            kwargs["compute_type"] = compute_type
        _MODEL_CACHE[model_name] = WhisperModel(model_name, **kwargs)
    return _MODEL_CACHE[model_name]


def _run_transcription(audio_path: Path, model_name: str, language: Optional[str]):
    model = _get_model(model_name)
    segments_iter, _info = model.transcribe(str(audio_path), language=language)
    segments: list[dict] = []
    text_parts: list[str] = []
    for seg in segments_iter:  # type: ignore[attr-defined]
        payload = {
            "start": float(getattr(seg, "start", 0.0)),
            "end": float(getattr(seg, "end", 0.0)),
            "text": getattr(seg, "text", "") or "",
        }
        segments.append(payload)
        if payload["text"]:
            text_parts.append(payload["text"].strip())
    text = " ".join(text_parts).strip()
    return text, segments


@app.post("/transcribe", response_model=TranscribeResponse)
def transcribe(req: TranscribeRequest, x_api_key: Optional[str] = Header(None)):
    _check_api_key(x_api_key)

    audio_path, cleanup = _resolve_audio_source(req.audio_url)
    try:
        text, segments = _run_transcription(audio_path, req.model, req.lang)
        payload = TranscribeResponse(
            text=text,
            segments=segments,
            hash=_sha256(audio_path),
        )
    finally:
        if cleanup:
            with suppress(FileNotFoundError):
                audio_path.unlink()

    return payload
