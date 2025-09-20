# AutoEdit MVP

Local-first auto-edit pipeline that ingests media, detects scenes, transcribes speech, applies simple selection rules, and exports an MLT timeline for Kdenlive/Shotcut. Optional GPU offload now targets Beam Cloud services (superseding the previous Lightning AI setup).

## Quickstart (Local)

- Prereqs (macOS):
  - `xcode-select --install`
  - Install Homebrew then: `brew install ffmpeg chromaprint pkg-config cmake`
- Python env:
  - `python3 -m venv .venv && source .venv/bin/activate`
  - `pip install --upgrade pip`
  - `pip install -e .[full]`

Example run (with your own media):

```
# Create a run folder and ingest inputs
autoedit ingest /path/to/input.mp4 -o runs/demo

# Detect scenes (fallback creates one full-length segment if PySceneDetect unavailable)
autoedit cut runs/demo/raw -o runs/demo/artifacts/sequences.json

# Transcribe (local) to JSON (requires faster-whisper for real results)
autoedit stt runs/demo/audio/main.flac --backend local -o runs/demo/artifacts/transcript.json

# Select segments (simple passthrough for MVP)
autoedit select runs/demo/artifacts -o runs/demo/artifacts/selection.json

# Export Kdenlive/Shotcut MLT timeline
autoedit export-mlt runs/demo/artifacts/selection.json -o runs/demo/outputs/edit.mlt
```

## Pipeline Shortcut

Run the entire workflow with one command (defaults to the local backend):

```
autoedit pipeline /path/to/input.mp4 -o runs/demo
```

Use flags like `--backend lightning`, `--language`, `--min-len`, or `--max-len` to customise behaviour. Remote Beam runs require the environment variables described below (`LIGHTNING_BASE_URL`, `LIGHTNING_API_KEY`, `BEAM_API_TOKEN_*`).

If you do not already have a presigned audio URL, provide a config file with storage credentials and the CLI will upload the audio automatically:

```
autoedit pipeline /path/to/input.mp4 -o runs/demo --backend lightning --endpoint https://beam.example --config config.yaml
```

## Layout

```
.
├─ autoedit/
│  ├─ cli/
│  ├─ backends/
│  │  ├─ base.py
│  │  ├─ local/
│  │  └─ lightning/           # Beam Cloud remote client (rename pending)
│  ├─ core/
│  ├─ schemas/
│  └─ exporters/
├─ services/
│  └─ stt-service/
├─ samples/
├─ scripts/
├─ tests/
└─ infra/
```

See `MVP-Global-Dev-Infrastructure-Plan.md` for the full plan.

Beam Cloud integration notes live under `docs/beam/` (start with `docs/beam/getting-started.md`). Use `docs/beam/accounts.md` to wire multiple Beam accounts via environment variables.
