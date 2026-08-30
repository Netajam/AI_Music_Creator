"""Measuring a track before and after: EBU R128, and the state of its ending."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from aimc.audio import peak_amplitude
from aimc.mastering.targets import TAIL_MAX, TAIL_WINDOW, TARGET_LRA, TARGET_LUFS, TARGET_TP

# loudnorm prints its JSON on stderr, in the middle of the rest of ffmpeg's output.
STATS_RE = re.compile(r"\{[^{}]*\"input_i\"[^{}]*\}", re.S)


def measure(path: Path) -> dict[str, Any] | None:
    """EBU R128 measurement, loudnorm's first pass (JSON output on stderr).

    Returns None when ffmpeg produced nothing usable: better to stop than to
    master from invented measurements.
    """
    try:
        out = subprocess.run(
            ["ffmpeg", "-nostats", "-i", str(path),
             "-af", f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA={TARGET_LRA}:"
                    "print_format=json",
             "-f", "null", "-"], capture_output=True, text=True)
    except OSError:
        return None
    match = STATS_RE.search(out.stderr)
    if not match:
        return None
    try:
        measured: dict[str, Any] = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return measured


def tail_amplitude(path: Path) -> float:
    """Peak amplitude over the last 50 ms — reveals an abrupt cut."""
    return peak_amplitude(path, seconds=TAIL_WINDOW)


def tail_is_clean(amplitude: float) -> bool:
    return amplitude <= TAIL_MAX
