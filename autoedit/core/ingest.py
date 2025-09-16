from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from rich import print


LAYOUT_DIRS = ["raw", "audio", "proxies", "outputs", "artifacts", "logs"]


def _run(cmd: List[str]) -> int:
    try:
        return subprocess.call(cmd)
    except FileNotFoundError:
        return 127


def _ffprobe_duration(path: Path) -> float | None:
    try:
        import json as _json
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        data = _json.loads(result.stdout or "{}")
        dur = data.get("format", {}).get("duration")
        return float(dur) if dur is not None else None
    except Exception:
        return None


def init_run_dir(run_dir: Path) -> Dict[str, str]:
    run_dir.mkdir(parents=True, exist_ok=True)
    created = {}
    for d in LAYOUT_DIRS:
        p = run_dir / d
        p.mkdir(exist_ok=True)
        created[d] = str(p)
    return created


def ingest_media(inputs: List[Path], run_dir: Path) -> Dict[str, str]:
    """Copy inputs to raw/, extract audio to audio/main.flac (first input)."""
    created = init_run_dir(run_dir)

    raw_dir = run_dir / "raw"
    audio_dir = run_dir / "audio"
    artifacts_dir = run_dir / "artifacts"

    copied = []
    for path in inputs:
        dest = raw_dir / path.name
        if path.resolve() != dest.resolve():
            shutil.copy2(path, dest)
        else:
            # already in place
            pass
        copied.append(dest)

    # Extract audio from the first input
    if copied:
        src = copied[0]
        audio_out = audio_dir / "main.flac"
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-vn",
            "-c:a",
            "flac",
            str(audio_out),
        ]
        code = _run(cmd)
        if code != 0:
            print("[yellow]ffmpeg not found or failed; skipping audio extraction.[/yellow]")

    # Write minimal media db
    media_db = {
        "inputs": [str(p) for p in copied],
        "durations": {str(p): _ffprobe_duration(p) for p in copied},
    }
    (artifacts_dir / "media.db.json").write_text(json.dumps(media_db, indent=2))

    return created

