"""The terminal rendering of an analysis.

Separate from the computation: same numbers, another output.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

CAVEAT = (
    "\n  Signal-processing estimates, with no model: read them as hints.\n"
    "  The vocal detection mistakes a centred synth for singing, and a mono\n"
    "  track defeats it entirely.\n")


def _section_line(s: dict[str, Any]) -> str:
    voice = "yes" if s["has_vocal"] else "—"
    # The asterisk marks a tempo carried over from the global one for want of a
    # section long enough to measure it — without it, the figure would read as a
    # measurement.
    bpm = f"{s['bpm']:.0f}" + ("" if s.get("bpm_measured", True) else "*")
    return (f"  {s['start']:>4}s {s['end']:>4}s {bpm:>6} "
            f"{s['bass']:>6.2f} {voice:>6}  {s['label']}")


def render(path: Path, data: dict[str, Any]) -> str:
    """The analysis as readable text."""
    lines = [
        f"\n  {path.name}",
        f"  {data['duration']:.1f} s · global tempo ~{data['tempo_global']:.0f} BPM",
    ]
    if data["drops"]:
        lines.append(f"  drops detected: {', '.join(f'{d} s' for d in data['drops'])}")
    lines.append(f"\n  {'from':>5} {'to':>5} {'BPM':>6} {'bass':>6} {'vocal':>6}  section")
    lines.append("  " + "-" * 62)
    lines += [_section_line(s) for s in data["sections"]]
    if any(not s.get("bpm_measured", True) for s in data["sections"]):
        lines.append("\n  * section too short to measure a tempo: "
                     "global value carried over.")
    lines.append(CAVEAT)
    return "\n".join(lines)
