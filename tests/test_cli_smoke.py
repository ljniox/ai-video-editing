from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from autoedit.cli.main import app
from autoedit.schemas.sequences import Segment
from autoedit.schemas.transcript import Transcript, TranscriptSegment


runner = CliRunner()


@pytest.fixture()
def cli_env(tmp_path, monkeypatch):
    run_dir = tmp_path / "run"
    selection_path = run_dir / "artifacts" / "selection.json"
    mlt_path = run_dir / "outputs" / "edit.mlt"
    sample_file = tmp_path / "sample.txt"
    sample_file.write_text("sample")
    audio_target = run_dir / "audio" / "main.flac"

    from autoedit.core import ingest as ingest_module

    def fake_run(cmd):
        audio_target.parent.mkdir(parents=True, exist_ok=True)
        audio_target.write_bytes(b"FAKE")
        return 0

    monkeypatch.setattr(ingest_module, "_run", fake_run)
    monkeypatch.setattr(ingest_module, "_ffprobe_duration", lambda _: 5.0)

    from autoedit.core import scene_detect as scene_module

    def fake_detect(raw_dir: Path):
        files = sorted(raw_dir.glob("*"))
        assert files, "ingest should copy files to raw/"
        return [Segment(start=0.0, end=5.0, source=str(files[0]))]

    monkeypatch.setattr(scene_module, "detect_scenes", fake_detect)

    from autoedit.backends.local.transcriber import LocalTranscriber

    def fake_transcribe(self, audio_path: Path, language=None):
        assert audio_path == audio_target
        return Transcript(
            text="hello world",
            segments=[TranscriptSegment(start=0.0, end=5.0, text="hello world")],
        )

    monkeypatch.setattr(LocalTranscriber, "transcribe", fake_transcribe)

    return {
        "run_dir": run_dir,
        "selection_path": selection_path,
        "mlt_path": mlt_path,
        "sample_file": sample_file,
        "audio_target": audio_target,
    }


def test_full_cli_smoke(cli_env):
    run_dir = cli_env["run_dir"]
    selection_path = cli_env["selection_path"]
    mlt_path = cli_env["mlt_path"]
    sample_file = cli_env["sample_file"]
    audio_target = cli_env["audio_target"]

    result = runner.invoke(app, ["ingest", str(sample_file), "-o", str(run_dir)])
    assert result.exit_code == 0, result.output

    result = runner.invoke(
        app,
        [
            "cut",
            str(run_dir / "raw"),
            "-o",
            str(run_dir / "artifacts" / "sequences.json"),
        ],
    )
    assert result.exit_code == 0, result.output

    result = runner.invoke(
        app,
        [
            "stt",
            str(audio_target),
            "--backend",
            "local",
            "-o",
            str(run_dir / "artifacts" / "transcript.json"),
        ],
    )
    assert result.exit_code == 0, result.output

    result = runner.invoke(
        app,
        ["select", str(run_dir / "artifacts"), "-o", str(selection_path)],
    )
    assert result.exit_code == 0, result.output

    selection = json.loads(selection_path.read_text())
    assert selection["shots"], "selection should contain shots"

    result = runner.invoke(
        app,
        [
            "export-mlt",
            str(selection_path),
            "-o",
            str(mlt_path),
        ],
    )
    assert result.exit_code == 0, result.output

    assert mlt_path.exists()
    content = mlt_path.read_text()
    assert "mlt" in content.lower()


def test_pipeline_command(cli_env):
    run_dir = cli_env["run_dir"]
    selection_path = cli_env["selection_path"]
    mlt_path = cli_env["mlt_path"]
    sample_file = cli_env["sample_file"]

    result = runner.invoke(
        app,
        [
            "pipeline",
            str(sample_file),
            "-o",
            str(run_dir),
            "--backend",
            "local",
        ],
    )
    assert result.exit_code == 0, result.output

    assert selection_path.exists()
    assert mlt_path.exists()

    selection = json.loads(selection_path.read_text())
    assert selection["shots"], "pipeline selection should contain shots"

    content = mlt_path.read_text()
    assert "mlt" in content.lower()
