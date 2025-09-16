from __future__ import annotations

import json
from pathlib import Path

from autoedit.schemas.selection import Selection
from autoedit.schemas.sequences import Sequences, Segment


def select_segments(artifacts_dir: Path) -> Selection:
    """Simple MVP selection: passthrough of detected sequences.

    Reads artifacts/sequences.json and returns the same segments as selection.
    """
    seq_path = artifacts_dir / "sequences.json"
    if not seq_path.exists():  # fallback: empty selection
        return Selection(shots=[])
    sequences = Sequences.model_validate_json(seq_path.read_text())
    return Selection(shots=[Segment(**s.model_dump()) for s in sequences.segments])

