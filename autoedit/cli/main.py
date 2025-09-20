from __future__ import annotations

from pathlib import Path
import os
from typing import Any, List, Optional

import typer
from rich import print
from rich.console import Console
from rich.traceback import install

from autoedit.core.ingest import ingest_media
from autoedit.core.scene_detect import detect_scenes
from autoedit.core.select import select_segments
from autoedit.exporters.mlt import export_mlt
from autoedit.schemas.sequences import Sequences
from autoedit.schemas.selection import Selection
from autoedit.schemas.transcript import Transcript
from autoedit.backends.local.transcriber import LocalTranscriber
from autoedit.backends.lightning.transcriber import (
    LightningConfig,
    LightningTranscriber,
)
from autoedit.storage import load_storage_client


install(show_locals=False)
app = typer.Typer(help="AutoEdit MVP CLI")
console = Console()


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _collect_beam_tokens() -> List[str]:
    """Return Beam API tokens discovered in the environment for round-robin usage."""
    tokens: List[str] = []
    seen: set[str] = set()

    grouped = sorted(
        (
            (name, value)
            for name, value in os.environ.items()
            if name.startswith("BEAM_API_TOKEN_") and value
        ),
        key=lambda item: item[0],
    )
    for _, value in grouped:
        if value not in seen:
            seen.add(value)
            tokens.append(value)

    csv_tokens = os.getenv("BEAM_API_KEYS")
    if csv_tokens:
        for item in csv_tokens.split(","):
            candidate = item.strip()
            if candidate and candidate not in seen:
                seen.add(candidate)
                tokens.append(candidate)

    return tokens


def _load_config(config_path: Optional[Path]) -> dict:
    path: Optional[Path] = None
    if config_path:
        path = config_path
    else:
        env_path = os.getenv("AUTOEDIT_CONFIG")
        if env_path:
            path = Path(env_path)

    if not path:
        return {}
    if not path.exists():
        raise typer.BadParameter(f"Config file not found: {path}")

    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - dependency missing
        raise typer.BadParameter(
            "PyYAML is required to read config files. Install with 'pip install PyYAML' "
            "or use the [full] extra."
        ) from exc

    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise typer.BadParameter("Config file must contain a top-level mapping")
    return data


def _resolve_storage_client(config: dict) -> Optional[Any]:
    storage_cfg = config.get("storage") if config else None
    if not storage_cfg:
        return None
    return load_storage_client(storage_cfg)


@app.command()
def ingest(
    inputs: List[Path] = typer.Argument(..., exists=True, readable=True),
    output: Path = typer.Option(..., "-o", "--output", help="Run directory, e.g. runs/demo"),
):
    """Ingest input media into a run directory and extract audio."""
    console.rule("Ingest")
    out = ingest_media(inputs, output)
    print({"created": out})


@app.command(name="cut")
def cut(
    raw_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    output: Path = typer.Option(..., "-o", "--output", help="Output sequences.json path"),
):
    """Detect scenes and write sequences.json."""
    console.rule("Scene Detection")
    segments = detect_scenes(raw_dir)
    data = Sequences(segments=segments)
    _ensure_parent(output)
    output.write_text(data.model_dump_json(indent=2))
    print(f"Wrote {output}")


@app.command()
def stt(
    audio: Path = typer.Argument(None, exists=True, dir_okay=False),
    backend: str = typer.Option(
        "local", help="Transcription backend: local|lightning (Beam remote)"
    ),
    language: Optional[str] = typer.Option(None, help="Language code, e.g., en, fr"),
    model: str = typer.Option("medium", help="Whisper model size (local)"),
    output: Path = typer.Option(..., "-o", "--output", help="Output transcript.json path"),
    audio_url: Optional[str] = typer.Option(
        None,
        help="When using backend=lightning (Beam), provide a presigned URL to audio",
    ),
    endpoint: Optional[str] = typer.Option(
        None,
        help="Beam service base URL (env: $LIGHTNING_BASE_URL while we migrate)",
    ),
    config_path: Optional[Path] = typer.Option(
        None, help="Path to config.yaml (defaults to $AUTOEDIT_CONFIG if set)"
    ),
):
    """Transcribe audio to transcript.json using the selected backend."""
    console.rule("Transcription")
    if backend == "local":
        transcriber = LocalTranscriber(model=model)
        transcript: Transcript = transcriber.transcribe(audio, language=language)
    else:
        base_url = endpoint or os.getenv("LIGHTNING_BASE_URL")
        if not base_url:
            raise typer.BadParameter(
                "Provide --endpoint or set LIGHTNING_BASE_URL for the Beam backend "
                "(alias: lightning)."
            )
        config = _load_config(config_path)
        storage_client = _resolve_storage_client(config)
        if not audio_url:
            if audio is None:
                raise typer.BadParameter(
                    "Provide an audio file path when uploading for the Beam backend."
                )
            if not storage_client:
                raise typer.BadParameter(
                    "Provide --audio-url or configure storage for the Beam backend "
                    "(see docs/CLI.md)."
                )
            upload = storage_client.upload_file(audio)
            audio_url = upload.url
        beam_tokens = _collect_beam_tokens()
        transcriber = LightningTranscriber(
            LightningConfig(
                base_url=base_url,
                api_key=os.getenv("LIGHTNING_API_KEY"),
                api_keys=beam_tokens or None,
            )
        )
        transcript = transcriber.transcribe_url(audio_url, lang=language, model=model)
    _ensure_parent(output)
    output.write_text(transcript.model_dump_json(indent=2))
    print(f"Wrote {output}")


@app.command()
def pipeline(
    inputs: List[Path] = typer.Argument(..., exists=True, readable=True),
    run_dir: Path = typer.Option(..., "-o", "--output", help="Run directory, e.g. runs/demo"),
    backend: str = typer.Option(
        "local", help="Transcription backend: local|lightning (Beam remote)"
    ),
    language: Optional[str] = typer.Option(None, help="Language code, e.g., en, fr"),
    model: str = typer.Option("medium", help="Whisper model size (local)"),
    audio_url: Optional[str] = typer.Option(
        None,
        help="When using backend=lightning (Beam), provide a presigned URL to audio",
    ),
    endpoint: Optional[str] = typer.Option(
        None,
        help="Beam service base URL (env: $LIGHTNING_BASE_URL while we migrate)",
    ),
    speech_only: bool = typer.Option(False, help="Keep only segments with detected speech"),
    min_len: float = typer.Option(0.0, help="Drop shots shorter than this (seconds)"),
    max_len: float = typer.Option(0.0, help="Trim shots longer than this (seconds)"),
    mlt_output: Optional[Path] = typer.Option(
        None, help="Optional explicit path for the generated MLT file"
    ),
    config_path: Optional[Path] = typer.Option(
        None, help="Path to config.yaml (defaults to $AUTOEDIT_CONFIG if set)"
    ),
):
    """Run the full AutoEdit pipeline in one command."""

    console.rule("AutoEdit Pipeline")

    ingest_media(inputs, run_dir)

    artifacts_dir = run_dir / "artifacts"
    raw_dir = run_dir / "raw"
    audio_path = run_dir / "audio" / "main.flac"

    # Scene detection
    sequences_path = artifacts_dir / "sequences.json"
    segments = detect_scenes(raw_dir)
    sequences = Sequences(segments=segments)
    _ensure_parent(sequences_path)
    sequences_path.write_text(sequences.model_dump_json(indent=2))

    # Transcription
    transcript_path = artifacts_dir / "transcript.json"
    config = _load_config(config_path)
    storage_client = _resolve_storage_client(config)

    if backend == "local":
        transcriber = LocalTranscriber(model=model)
        transcript: Transcript = transcriber.transcribe(audio_path, language=language)
    else:
        base_url = endpoint or os.getenv("LIGHTNING_BASE_URL")
        if not base_url:
            raise typer.BadParameter(
                "Provide --endpoint or set LIGHTNING_BASE_URL for the Beam backend "
                "(alias: lightning)."
            )
        if not audio_url:
            if not storage_client:
                raise typer.BadParameter(
                    "Provide --audio-url or configure storage for the Beam backend "
                    "(see docs/CLI.md)."
                )
            upload = storage_client.upload_file(audio_path, target_name=f"{run_dir.name}/main.flac")
            audio_url = upload.url
        beam_tokens = _collect_beam_tokens()
        transcriber = LightningTranscriber(
            LightningConfig(
                base_url=base_url,
                api_key=os.getenv("LIGHTNING_API_KEY"),
                api_keys=beam_tokens or None,
            )
        )
        transcript = transcriber.transcribe_url(audio_url, lang=language, model=model)

    _ensure_parent(transcript_path)
    transcript_path.write_text(transcript.model_dump_json(indent=2))

    # Selection
    selection = select_segments(
        artifacts_dir,
        speech_only=speech_only,
        min_len=min_len,
        max_len=max_len,
    )
    selection_path = artifacts_dir / "selection.json"
    _ensure_parent(selection_path)
    selection_path.write_text(selection.model_dump_json(indent=2))

    # Export MLT
    final_mlt = mlt_output or run_dir / "outputs" / "edit.mlt"
    _ensure_parent(final_mlt)
    export_mlt(selection, output_path=final_mlt)

    print(
        {
            "run_dir": str(run_dir),
            "sequences": str(sequences_path),
            "transcript": str(transcript_path),
            "selection": str(selection_path),
            "mlt": str(final_mlt),
        }
    )


@app.command()
def select(
    artifacts_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    output: Path = typer.Option(..., "-o", "--output", help="Output selection.json path"),
    speech_only: bool = typer.Option(False, help="Keep only segments with detected speech"),
    min_len: float = typer.Option(0.0, help="Drop shots shorter than this (seconds)"),
    max_len: float = typer.Option(0.0, help="Trim shots longer than this (seconds)"),
):
    """Apply simple selection rules and write selection.json."""
    console.rule("Selection")
    selection = select_segments(
        artifacts_dir, speech_only=speech_only, min_len=min_len, max_len=max_len
    )
    _ensure_parent(output)
    output.write_text(selection.model_dump_json(indent=2))
    print(f"Wrote {output}")


@app.command("export-mlt")
def export_mlt_cmd(
    selection_path: Path = typer.Argument(..., exists=True, dir_okay=False),
    output: Path = typer.Option(..., "-o", "--output", help="Output MLT file path (.mlt)"),
    fps: float = typer.Option(25.0, help="Profile FPS for MLT timing"),
):
    """Export MLT XML from selection.json for Kdenlive/Shotcut."""
    console.rule("Export MLT")
    selection = Selection.model_validate_json(selection_path.read_text())
    _ensure_parent(output)
    export_mlt(selection, output, fps=fps)
    print(f"Wrote {output}")


if __name__ == "__main__":
    app()
