from __future__ import annotations

from pathlib import Path

from autoedit.schemas.selection import Selection
from autoedit.schemas.sequences import Sequences, Segment
from autoedit.schemas.transcript import Transcript


def _overlaps(a_start: float, a_end: float, b_start: float, b_end: float) -> bool:
    return max(a_start, b_start) < min(a_end, b_end)


def select_segments(
    artifacts_dir: Path,
    speech_only: bool = False,
    min_len: float = 0.0,
    max_len: float = 0.0,
) -> Selection:
    """Selection with simple heuristics.

    - If speech_only, keeps only shots that overlap any transcript segment.
    - If min_len > 0: drops shots shorter than min_len.
    - If max_len > 0: trims shots longer than max_len (end = start + max_len).
    """
    seq_path = artifacts_dir / "sequences.json"
    if not seq_path.exists():  # fallback: empty selection
        return Selection(shots=[])
    sequences = Sequences.model_validate_json(seq_path.read_text())

    shots = [Segment(**s.model_dump()) for s in sequences.segments]

    if speech_only:
        tx_path = artifacts_dir / "transcript.json"
        if tx_path.exists():
            tx = Transcript.model_validate_json(tx_path.read_text())
            kept = []
            for seg in shots:
                has_overlap = any(
                    _overlaps(seg.start, seg.end, t.start, t.end) for t in tx.segments
                )
                if has_overlap:
                    kept.append(seg)
            shots = kept

    if min_len > 0:
        shots = [s for s in shots if (s.end - s.start) >= min_len]

    if max_len > 0:
        trimmed = []
        for s in shots:
            dur = s.end - s.start
            if dur > max_len:
                s = Segment(start=s.start, end=s.start + max_len, source=s.source)
            trimmed.append(s)
        shots = trimmed

    return Selection(shots=shots)
