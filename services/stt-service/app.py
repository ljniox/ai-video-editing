from __future__ import annotations

import os
from typing import Optional

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


@app.get("/healthz")
def healthz():  # pragma: no cover - simple endpoint
    return {"status": "ok"}


def _check_api_key(x_api_key: Optional[str]):
    required = os.getenv("API_KEY")
    if required and x_api_key != required:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.post("/transcribe", response_model=TranscribeResponse)
def transcribe(req: TranscribeRequest, x_api_key: Optional[str] = Header(None)):
    _check_api_key(x_api_key)
    # MVP stub: echo request; in a real service, stream audio_url and run GPU whisper
    return TranscribeResponse(text="", segments=[], hash=None)

