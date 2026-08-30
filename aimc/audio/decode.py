"""Decode an audio file to raw PCM, without going through numpy.

Four callers decode: the analysis (22 kHz stereo), the studio's energy profile
(16 kHz mono), the mastering end-of-track measurement (the last 50 ms) and the
content fingerprint (at the native rate, streamed). They shared nothing but a
copy-pasted ffmpeg command line.

This module returns bytes, never an array: `./master`, `./grab` and
`./blend-refs` run under the system python3, where numpy does not exist. It is
up to the caller that has it to convert.
"""

from __future__ import annotations

import struct
import subprocess
from pathlib import Path


def decode(path: Path | str, *, rate: int, channels: int,
           fmt: str = "f32le", from_end: float | None = None) -> bytes:
    """Raw interleaved PCM, or b"" if the file cannot be read.

    `from_end` decodes only the last few seconds (`-sseof`), which saves
    re-reading a whole track just to look at its tail.
    """
    head = ["ffmpeg", "-v", "error"]
    if from_end is not None:
        head += ["-sseof", f"-{from_end}"]
    try:
        res = subprocess.run(
            [*head, "-i", str(path), "-vn", "-ac", str(channels),
             "-ar", str(rate), "-f", fmt, "-"], capture_output=True)
    except OSError:
        return b""
    return res.stdout


def peak_amplitude(path: Path | str, *, seconds: float,
                   rate: int = 16000) -> float:
    """Peak amplitude over the last `seconds` seconds, in mono.

    Deliberately without numpy: mastering is what uses it, and it runs under the
    system python3.
    """
    raw = decode(path, rate=rate, channels=1, from_end=seconds)
    if not raw:
        return 0.0
    n = len(raw) // 4
    if n == 0:
        return 0.0
    # struct.unpack returns a tuple[Any, ...]: the type is restated here rather
    # than left to bubble up as Any through the return annotation.
    samples: tuple[float, ...] = struct.unpack(f"<{n}f", raw[: n * 4])
    return max(abs(v) for v in samples)


def open_stream(path: Path | str, fmt: str) -> subprocess.Popen[bytes] | None:
    """ffmpeg decoding at the original rate and channel count, streamed.

    Used to hash a file without loading it: a 145 s WAV is 28 MB, and the target
    machine is already tight on memory.
    """
    try:
        return subprocess.Popen(
            ["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-f", fmt, "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except OSError:
        return None
