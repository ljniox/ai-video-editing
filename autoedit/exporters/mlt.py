from __future__ import annotations

from pathlib import Path

from autoedit.schemas.selection import Selection


def _sec_to_frames(sec: float, fps: float) -> int:
    return max(int(round(sec * fps)), 0)


def export_mlt(selection: Selection, output_path: Path, fps: float = 25.0) -> None:
    """Write a minimal MLT XML compatible with Kdenlive/Shotcut.

    Assumes all shots reference the same source file (MVP constraint).
    """
    if not selection.shots:
        output_path.write_text("""<mlt><playlist id=\"playlist0\"></playlist></mlt>""")
        return

    sources = list({s.source for s in selection.shots})
    source = sources[0]

    # Warn if multiple sources; only the first is used in this minimal exporter.
    # A richer exporter could add multiple producers & playlists.

    entries = []
    for s in selection.shots:
        start_f = _sec_to_frames(s.start, fps)
        end_f = _sec_to_frames(s.end, fps)
        if end_f <= start_f:
            continue
        entries.append(
            f'  <entry producer="producer0" in="{start_f}" out="{max(end_f - 1, start_f)}" />'
        )

    xml = f"""
<mlt title="autoedit" version="7.8.0">
 <profile
  description="HD 1080p {fps} fps"
  frame_rate_num="{int(fps)}"
  frame_rate_den="1"
  width="1920"
  height="1080"
  colorspace="709"/>
 <producer id="producer0">
  <property name="resource">{source}</property>
  <property name="mlt_service">avformat</property>
 </producer>
 <playlist id="playlist0">
{chr(10).join(entries)}
 </playlist>
 <tractor id="tractor0">
  <track producer="playlist0" />
 </tractor>
</mlt>
"""
    output_path.write_text(xml.strip() + "\n")
