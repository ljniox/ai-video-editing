from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from typing import List

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

MODULE_PATH = Path(__file__).resolve().parents[2] / "services/stt-service/app.py"


def _load_service_module():
    spec = importlib.util.spec_from_file_location("stt_service_app", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[assignment]
    return module


@pytest.fixture()
def service_module(monkeypatch):
    module = _load_service_module()
    module._MODEL_CACHE.clear()
    monkeypatch.delenv("API_KEY", raising=False)
    return module


def test_requires_api_key(service_module, monkeypatch):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(service_module.app)
    resp = client.post("/transcribe", json={"audio_url": "/tmp/missing.flac"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Unauthorized"


def test_transcribe_local_file(service_module, tmp_path, monkeypatch):
    monkeypatch.setenv("API_KEY", "secret")
    audio_file = tmp_path / "clip.flac"
    audio_file.write_bytes(b"hello world")

    expected_hash = hashlib.sha256(b"hello world").hexdigest()

    def fake_transcription(path, model_name, language):
        assert path == audio_file
        assert model_name == "medium"
        return "synthetic text", [{"start": 0.0, "end": 1.0, "text": "segment"}]

    monkeypatch.setattr(service_module, "_run_transcription", fake_transcription)

    client = TestClient(service_module.app)
    resp = client.post(
        "/transcribe",
        json={"audio_url": str(audio_file), "model": "medium", "lang": "en"},
        headers={"X-API-Key": "secret"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["text"] == "synthetic text"
    assert payload["segments"] == [{"start": 0.0, "end": 1.0, "text": "segment"}]
    assert payload["hash"] == expected_hash


@respx.mock
def test_transcribe_remote_download(service_module, monkeypatch):
    content = b"remote-audio"
    route = respx.get("https://example.com/audio.flac").mock(
        return_value=httpx.Response(200, content=content)
    )

    captured_paths: List[Path] = []

    def fake_transcription(path, model_name, language):
        captured_paths.append(path)
        assert path.exists()
        return "remote", []

    monkeypatch.setattr(service_module, "_run_transcription", fake_transcription)

    client = TestClient(service_module.app)
    resp = client.post(
        "/transcribe",
        json={"audio_url": "https://example.com/audio.flac"},
    )
    assert resp.status_code == 200
    assert route.called
    assert resp.json()["hash"] == hashlib.sha256(content).hexdigest()
    assert len(captured_paths) == 1
    temp_path = captured_paths[0]
    assert not temp_path.exists()


def test_transcribe_missing_file(service_module):
    client = TestClient(service_module.app)
    resp = client.post(
        "/transcribe",
        json={"audio_url": "/path/does/not/exist"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Audio source not found"
