from pathlib import Path

from autoedit.exporters.mlt import export_mlt
from autoedit.schemas.selection import Selection
from autoedit.schemas.sequences import Segment


def test_mlt_multisource(tmp_path: Path):
    sel = Selection(
        shots=[
            Segment(start=0.0, end=1.0, source="/a.mp4"),
            Segment(start=1.0, end=2.0, source="/b.mp4"),
            Segment(start=2.0, end=3.0, source="/a.mp4"),
        ]
    )
    out = tmp_path / "edit.mlt"
    export_mlt(sel, out, fps=25.0)
    xml = out.read_text()
    # two producers present
    assert xml.count('<producer id="producer0">') == 1
    assert xml.count('<producer id="producer1">') == 1
    # three entries
    assert xml.count("<entry producer=") == 3
