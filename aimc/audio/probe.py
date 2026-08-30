"""What ffprobe can tell us about an audio file.

Four modules asked ffprobe for a duration, with four different error handlers:
one set a timeout, the others did not; one caught a missing ffprobe, the others
let the exception through. A single version here, the most careful of the four.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

# ffprobe returns immediately on a local file; the timeout is only there so the
# studio does not freeze on a network mount that has stopped responding.
TIMEOUT = 30


def _ffprobe(*args: str) -> str | None:
    """ffprobe's standard output, or None if the call gave nothing usable."""
    try:
        res = subprocess.run(["ffprobe", "-v", "error", *args],
                             capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None
    return res.stdout if res.returncode == 0 else None


def duration(path: Path | str) -> float | None:
    """Actual duration in seconds, or None if the file cannot be read."""
    out = _ffprobe("-show_entries", "format=duration",
                   "-of", "default=noprint_wrappers=1:nokey=1", str(path))
    if out is None:
        return None
    try:
        return float(out.strip())
    except ValueError:
        return None


def stream_info(path: Path | str) -> dict[str, Any]:
    """Codec, rate, channels and duration of the first stream — empty dict if unreadable.

    The duration comes from `format` and not from the stream: a WAV does not
    declare one at the stream level, and that is precisely the format we handle
    the most.
    """
    out = _ffprobe("-show_entries",
                   "stream=codec_name,sample_rate,channels,bits_per_raw_sample",
                   "-show_entries", "format=duration", "-of", "json", str(path))
    if out is None:
        return {}
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {}
    stream: dict[str, Any] = (data.get("streams") or [{}])[0]
    stream["duration"] = float(data.get("format", {}).get("duration", 0) or 0)
    return stream
