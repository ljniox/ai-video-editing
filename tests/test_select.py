from pathlib import Path

from autoedit.core.select import select_segments


def write(p: Path, s: str):
    p.write_text(s)


def test_select_speech_only(tmp_path: Path):
    art = tmp_path / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    # sequences: two segments
    write(
        art / "sequences.json",
        """
{"segments": [
  {"start": 0.0, "end": 1.0, "source": "/a.mp4"},
  {"start": 1.0, "end": 2.0, "source": "/a.mp4"}
]}
""".strip(),
    )
    # transcript: only overlaps second segment
    write(
        art / "transcript.json",
        """
{"text":"hi there","segments": [
  {"start": 1.2, "end": 1.8, "text": "hi"}
]}
""".strip(),
    )

    sel = select_segments(art, speech_only=True)
    assert len(sel.shots) == 1
    shot = sel.shots[0]
    assert shot.start == 1.0 and shot.end == 2.0

    # min/max heuristics
    sel2 = select_segments(art, speech_only=True, min_len=1.1, max_len=0.5)
    # min_len filters out 1s segment; expect 0 left
    assert len(sel2.shots) == 0
