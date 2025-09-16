from __future__ import annotations

from pathlib import Path
from typing import List, Optional

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


install(show_locals=False)
app = typer.Typer(help="AutoEdit MVP CLI")
console = Console()


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


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
    audio: Path = typer.Argument(..., exists=True, dir_okay=False),
    backend: str = typer.Option("local", help="Transcription backend: local|lightning"),
    language: Optional[str] = typer.Option(None, help="Language code, e.g., en, fr"),
    model: str = typer.Option("medium", help="Whisper model size (local)"),
    output: Path = typer.Option(..., "-o", "--output", help="Output transcript.json path"),
):
    """Transcribe audio to transcript.json using the selected backend."""
    console.rule("Transcription")
    if backend == "local":
        transcriber = LocalTranscriber(model=model)
        transcript: Transcript = transcriber.transcribe(audio, language=language)
    else:
        raise typer.BadParameter("Only 'local' backend implemented in CLI for now.")
    _ensure_parent(output)
    output.write_text(transcript.model_dump_json(indent=2))
    print(f"Wrote {output}")


@app.command()
def select(
    artifacts_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    output: Path = typer.Option(..., "-o", "--output", help="Output selection.json path"),
):
    """Apply simple selection rules and write selection.json."""
    console.rule("Selection")
    selection = select_segments(artifacts_dir)
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
