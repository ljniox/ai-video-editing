# AutoEdit CLI Overview

Use the Typer-based `autoedit` CLI to run the pipeline locally or with Beam Cloud offload.

## Core Commands

```bash
autoedit ingest <inputs> -o runs/demo      # copy media, extract audio
autoedit cut runs/demo/raw -o runs/demo/artifacts/sequences.json
autoedit stt runs/demo/audio/main.flac -o runs/demo/artifacts/transcript.json
autoedit select runs/demo/artifacts -o runs/demo/artifacts/selection.json
autoedit export-mlt runs/demo/artifacts/selection.json -o runs/demo/outputs/edit.mlt
```

## Pipeline Command

```bash
autoedit pipeline /path/to/input.mp4 -o runs/demo
```

- Defaults to the local transcription backend.
- Pass `--backend lightning --audio-url <signed-url>` to call the Beam remote service.
- Backends accept familiar flags (`--language`, `--model`, `--min-len`, `--max-len`, `--speech-only`).
- Override the output path with `--mlt-output` when integrating with other tooling.

Environment requirements for Beam:
- `LIGHTNING_BASE_URL`: Base URL of the Beam endpoint (e.g., `https://app.beam.cloud/endpoint/...`).
- `LIGHTNING_API_KEY` or `BEAM_API_TOKEN_*`: Authentication tokens (the CLI automatically cycles multiple tokens when provided).
- `--config config.yaml` (or `$AUTOEDIT_CONFIG`) enables automatic uploads; the config must define a `storage` block (see `config.example.yaml`).

## Testing & CI

- Run `PYTHONPATH=. pytest` before opening a PR.
- CI runs Ruff, Black, and pytest via `.github/workflows/python-ci.yml`.
- Smoke tests monkeypatch ffmpeg/Whisper to stay fast; integration tests can be layered later.

See `README.md` for environment setup and `docs/beam/` for detailed Beam deployment guidance.
