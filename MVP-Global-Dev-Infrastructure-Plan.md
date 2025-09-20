# MVP Global Development & Infrastructure Plan

This document defines the development workflow, environment setup, architecture, cloud offload (Beam Cloud), CI/CD, and ops practices for the AutoEdit MVP.

## 0) Goals & Deliverables

- Produce a local-first MVP that ingests media, detects scenes, transcribes speech, applies simple selection rules, and exports an editable timeline (`.mlt` for Kdenlive/Shotcut). Optional direct FFmpeg render.
- Provide pluggable backends for heavy inference (local CPU vs. Beam Cloud GPU) without changing core logic.
- Ship a small CLI for reproducible runs and a predictable project folder layout for artifacts.
- Establish a minimal, practical CI/testing loop and a cloud deployment path for GPU services.

---

## 1) System Architecture (High-Level)

- Local Orchestrator (Mac Intel)
  - CLI driving ingest, scene detection, transcription (local or remote), selection, export.
  - CPU-first implementations for everything; no local GPU required.
- Remote GPU Offload (Beam Cloud)
  - One or more FastAPI-based microservices: `stt-service` (Whisper GPU), optional `diarization-service` (pyannote), optional `vision-service` (YOLO/CLIP embeddings).
  - Stateless endpoints; artifacts exchanged via signed URLs to object storage; results returned as JSON.
- Storage
  - Local: per-project working directory with JSON artifacts and proxies.
  - Cloud: S3-compatible object storage (or Beam-provided storage) for audio chunks, proxy frames, and cached model outputs.
- Interfaces & Adapters
  - Abstract interfaces: `Transcriber`, `Diarizer`, `Detector`, `Embedder` with Local and Beam implementations.
  - Configurable via YAML/env to switch backends at runtime with timeouts and fallback.

---

## 2) Repository Layout (Monorepo)

```
.
├─ autoedit/                   # Python package (orchestrator, adapters, utils)
│  ├─ cli/                     # CLI entrypoints (Typer/Click)
│  ├─ backends/
│  │  ├─ local/                # Local CPU implementations
│  │  └─ lightning/            # Remote Beam clients (HTTP) for GPU services (rename pending)
│  ├─ core/                    # ingest, scene detect, rules, timeline export
│  ├─ schemas/                 # Pydantic/JSON schemas
│  ├─ exporters/               # MLT XML, Kdenlive project, EDL/FCPXML (optional)
│  └─ __init__.py
├─ services/
│  └─ stt-service/             # FastAPI for Whisper GPU (Beam deploy)
│     ├─ app.py                # /health, /transcribe endpoints
│     ├─ requirements.txt      # faster-whisper, uvicorn, fastapi, etc.
│     └─ Dockerfile.gpu        # nvidia/cuda base, Python deps
├─ samples/                    # tiny demo media + expected outputs
├─ scripts/                    # helper scripts (chunking, hashing, dev tools)
├─ tests/                      # unit & integration tests
├─ infra/                      # IaC (optional/placeholder), GitHub Actions
├─ pyproject.toml              # build config
├─ README.md                   # quickstart & usage
└─ MVP-Global-Dev-Infrastructure-Plan.md
```

---

## 3) Local Development Setup (macOS Intel)

- Prerequisites
  - Install Xcode CLT: `xcode-select --install`
  - Install Homebrew: https://brew.sh
  - Install core tools: `brew install ffmpeg chromaprint pkg-config cmake`
- Python Environment (3.11+)
  - Create venv: `python3 -m venv .venv && source .venv/bin/activate`
  - Upgrade pip: `pip install --upgrade pip`
  - Core deps: `pip install scenedetect[opencv] faster-whisper opencv-python numpy soundfile librosa pydub lxml jinja2 pyav auto-editor webrtcvad typer pydantic requests rich`
  - Optional heavy deps (flagged features): `pip install torch torchvision torchaudio pyannote.audio ultralytics`
- Project Structure
  - Create a per-project working folder under `./runs/<project-id>/` containing: `raw/`, `audio/`, `proxies/`, `outputs/`, `artifacts/`, `logs/`.
- Makefile (optional)
  - `make setup`: create venv, install deps, pre-commit hooks
  - `make test`: run unit/integration tests
  - `make fmt` / `make lint`: format & lint

---

## 4) Configuration & Secrets

- Config File (`config.yaml`)
  - `stt_backend: local|lightning` (remote Beam backend while naming migrates)
  - `diarization_backend: none|local|lightning` (remote Beam backend)
  - `vision_backend: none|local|lightning` (remote Beam backend)
  - `lightning:
      base_url: https://<your-beam-endpoint>
      api_key: ${LIGHTNING_API_KEY}  # use Beam key; env name kept for compatibility
      timeout_s: 60`
  - `beam_api_tokens`: optional list of Beam accounts with `env` keys (see `docs/beam/accounts.md`).
  - `storage:
      provider: s3|gcs|local
      bucket: <bucket-name>
      base_url: https://... (presigned)`
- Env Vars
  - `LIGHTNING_API_KEY` (Beam API key), `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_REGION`, `S3_ENDPOINT` (if using MinIO or other S3-compatible).
  - Any env var matching `BEAM_API_TOKEN_*` is auto-discovered for round-robin GPU usage.
- Secrets Management
  - Local: `.env` (never commit), use `direnv` or `dotenv`.
  - CI: GitHub Actions secrets; deploy-time injection for Beam services.

---

## 5) Data Model & Artifacts

- Project Directory (`runs/<id>/`)
  - `raw/` original media, `audio/` extracted WAV/FLAC, `proxies/` low-res previews, `outputs/` exported timelines and renders.
  - `artifacts/` JSON files: `sequences.json`, `transcript.json`, `vision.json`, `selection.json`, `media.db.json` (catalog + hashes).
- JSON Schemas (Pydantic)
  - `Sequence`: list of segments with `{start, end, source}`.
  - `Transcript`: segments and words with `{start, end, text, speaker?}`.
  - `Vision` (optional): per-shot tags `{faces, person_score, quality, objects}`.
  - `Selection`: chosen shots with constraints applied.
- Caching Strategy
  - Cache by media content hash; skip reprocessing if unchanged.

---

## 6) Core Pipeline & CLI

- Ingest
  - Probe media (duration, fps, audio channels).
  - Extract audio (`.flac` 16 kHz mono) and optional low-res proxies.
  - CLI: `autoedit ingest <inputs> -o runs/<id>/`
- Scene Detection
  - Use PySceneDetect (content-aware threshold) to create `sequences.json`.
  - CLI: `autoedit cut runs/<id>/raw -o runs/<id>/artifacts/sequences.json`
- Transcription (Local or Beam)
  - Local: `faster-whisper` small/medium model.
  - Remote: chunk audio (5–10 min windows), upload, call `/transcribe`, merge.
  - CLI: `autoedit stt runs/<id>/audio/main.flac --backend lightning` (Beam backend until CLI rename)
- Selection (Rules Engine)
  - Heuristics: speech-gated shots, min/max shot length, optional face presence.
  - CLI: `autoedit select runs/<id>/artifacts -o selection.json`
- Export Timeline (MLT)
  - Generate MLT XML for Kdenlive/Shotcut; preserve source paths and timings.
  - CLI: `autoedit export-mlt runs/<id>/selection.json -o outputs/edit.mlt`
- Optional Render
  - Direct FFmpeg render from selection: `autoedit render runs/<id>/selection.json -o outputs/final.mp4`
- Pipeline Helper
  - Single command orchestration: `autoedit pipeline /path/to/input.mp4 -o runs/<id>/`

---

## 7) Beam Cloud GPU Services

- Approach
  - Build containerized FastAPI services that accept signed URLs to input artifacts and return JSON.
  - Deploy to Beam Cloud with GPU instances sized per model.
- `stt-service` (Whisper GPU)
  - Endpoint `POST /transcribe` with `{ audio_url, lang?, model? }`.
  - Returns `{ segments: [{ start, end, text }], text }` compatible with local schema.
  - Implementation: `faster-whisper` on GPU (CTranslate2 CUDA build) or `whisper` + PyTorch CUDA.
- Multi-account strategy: rotate requests across `BEAM_API_TOKEN_*` credentials to fan out across multiple Beam organizations (supports parallel jobs and simple failover).
- Optional `diarization-service`
  - Endpoint `POST /diarize` → speaker-labeled segments.
  - Implementation: `pyannote.audio` GPU build; configurable max duration.
- Optional `vision-service`
  - Endpoints for detection (`/detect`) and/or embeddings (`/embed`), operating on frame samples.
- Auth & Security
  - `X-API-Key` header (shared secret); rate limiting per token.
  - Validate signed URLs server-side and stream artifacts without persisting full media.
- Performance
  - Chunk long audio; allow batch requests; cache by content hash.

---

## 8) Deployment & Ops

- Containerization
  - Base image: `nvidia/cuda:12.x-cudnn-runtime-ubuntu22.04` (for GPU services).
  - Install: `python3`, `pip`, dependencies (`faster-whisper`, `fastapi`, `uvicorn[standard]`).
  - Expose port `8080`; health endpoint `/healthz`.
- Beam Cloud
  - Define Beam app/work config referencing the GPU container and environment.
  - Provide `LIGHTNING_API_KEY` (Beam API key) via platform secrets; set min/max replicas to control cost.
  - Inject additional `BEAM_API_TOKEN_*` secrets when parallel capacity or multi-account routing is required.
- Storage
  - S3/MinIO/GCS for artifacts with presigned URLs; lifecycle rules for auto-expiration.
- Observability
  - Structured logs (JSON) with request IDs.
  - Basic metrics: request counts, latency, GPU mem usage.
  - Error reporting: Sentry (optional) for both CLI and services.

---

## 9) CI/CD (GitHub Actions)

- Workflows
  - `python-ci.yml`: lint (ruff), format (black --check), type-check (pyright/mypy), tests (pytest) on PRs.
  - `services-build.yml`: build & push Docker images for GPU services on tags; scan with Trivy.
  - `release.yml`: create GitHub Release with pinned wheel versions and changelog.
- Secrets
  - `REGISTRY_USER`, `REGISTRY_TOKEN`, `LIGHTNING_API_KEY` (Beam deploy key) if needed for deploy hooks.
- Artifacts
  - Upload test coverage and small sample outputs for reproducibility.

---

## 10) Testing Strategy

- Unit Tests
  - Core modules: ingest, scene detection wrappers, selection rules, MLT exporter.
  - Backends: local and Beam clients (mock HTTP).
- Integration Tests
  - End-to-end on sample media (<= 10s) to verify artifacts chain and MLT round-trip.
- Contract Tests
  - Schema validations for service responses; fixture-based golden files.
- Performance Smoke
  - Time budget checks on typical laptop CPU to avoid regressions.

---

## 11) Security, Privacy, and Cost Controls

- Security
  - Principle of least privilege for storage; signed URLs only.
  - Do not upload raw full-resolution video unless required; prefer proxies/chunks.
- Privacy
  - Optional on-device STT for sensitive media; redact PII fields in logs.
- Cost Controls
  - Small models by default; remote offload opt-in per run.
  - Max duration per request; auto-cancel long jobs; enforce caching by content hash.

---

## 12) Timeline & Milestones

- Week 1: Scaffold + Ingest + Scene Detection
  - Repo setup, CLI skeleton, FFmpeg/PySceneDetect wrappers, `sequences.json`.
- Week 2: STT (Local) + Export MLT
  - `faster-whisper` integration, transcript merge, baseline selection, `.mlt` export.
- Week 3: Beam STT Service + Adapters
  - Containerize `stt-service`, deploy to Beam, add client + fallback.
- Week 4 (optional): Diarization / Multicam Alignment / Quality Heuristics
  - `pyannote` service, Chromaprint alignment, face/quality heuristics.

---

## 13) Quickstart (Local)

```
# Prereqs
xcode-select --install
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install ffmpeg chromaprint pkg-config cmake

# Python env
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install scenedetect[opencv] faster-whisper opencv-python numpy soundfile librosa pydub lxml jinja2 pyav auto-editor typer pydantic requests rich

# Run
autoedit ingest samples/*.mp4 -o runs/demo
autoedit cut runs/demo/raw -o runs/demo/artifacts/sequences.json
autoedit stt runs/demo/audio/main.flac --backend local -o runs/demo/artifacts/transcript.json
autoedit select runs/demo/artifacts -o runs/demo/artifacts/selection.json
autoedit export-mlt runs/demo/artifacts/selection.json -o runs/demo/outputs/edit.mlt
```

---

## 14) Appendix: Example Service Contracts

- POST `/transcribe`
  - Request: `{ "audio_url": "https://.../chunk.flac", "lang": "fr", "model": "medium" }`
  - Response: `{ "text": "...", "segments": [{"start": 1.23, "end": 3.45, "text": "..."}], "hash": "<content-hash>" }`
- POST `/diarize` (optional)
  - Request: `{ "audio_url": "https://.../chunk.flac" }`
  - Response: `{ "segments": [{"start": 0.0, "end": 2.5, "speaker": "S1"}, ...] }`

---

## 15) Risks & Mitigations

- PyTorch + CUDA compatibility drift: pin versions in Dockerfile, use tested base image.
- FAISS on macOS via pip: defer or use conda; for MVP, replace with `sklearn` NN.
- YOLO/vision latency CPU-only: make optional; start with face presence using OpenCV.
- Large uploads: always chunk + compress; prefer audio-only where possible.

---

## 16) Definition of Done (MVP)

- CLI runs end-to-end locally on a sample: produces `sequences.json`, `transcript.json`, `selection.json`, and a working `.mlt` project importable into Kdenlive/Shotcut.
- Beam STT service reachable with authenticated request; client adapter can switch between local and Beam (legacy `lightning` flag).
- Tests pass on CI; README documents setup and example run.
