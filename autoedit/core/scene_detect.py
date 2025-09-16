from __future__ import annotations

from pathlib import Path
from typing import List

from autoedit.schemas.sequences import Segment


def _ffprobe_duration(path: Path) -> float | None:
    import json
    import subprocess

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
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
        data = json.loads(result.stdout or "{}")
        dur = data.get("format", {}).get("duration")
        return float(dur) if dur is not None else None
    except Exception:
        return None


def detect_scenes(raw_dir: Path) -> List[Segment]:
    """Detect scenes in the first media file in raw_dir.

    Uses PySceneDetect if available, else returns a single full-length segment.
    """
    files = sorted([p for p in raw_dir.iterdir() if p.is_file()])
    if not files:
        return []
    source = files[0]

    try:
        from scenedetect import open_video, SceneManager
        from scenedetect.detectors import ContentDetector
    except Exception:
        dur = _ffprobe_duration(source) or 0.0
        return [Segment(start=0.0, end=max(dur, 0.0), source=str(source))]

    video = open_video(str(source))
    manager = SceneManager()
    manager.add_detector(ContentDetector())
    manager.detect_scenes(video)
    scene_list = manager.get_scene_list()

    segments: List[Segment] = []
    for start_time, end_time in scene_list:
        segments.append(
            Segment(start=start_time.get_seconds(), end=end_time.get_seconds(), source=str(source))
        )
    if not segments:
        dur = _ffprobe_duration(source) or 0.0
        segments.append(Segment(start=0.0, end=max(dur, 0.0), source=str(source)))
    return segments

