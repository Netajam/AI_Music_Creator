"""The audio toolbox: ffmpeg and ffprobe, and nothing else.

This package is the only door onto the external tools. It depends on no model
and does not import numpy: `./master`, `./grab` and `./blend-refs` run under
the system python3, without the engine's environment.
"""

from aimc.audio.decode import decode, open_stream, peak_amplitude
from aimc.audio.probe import duration, stream_info
from aimc.audio.tools import install_hint, missing

__all__ = [
    "decode", "duration", "install_hint", "missing", "open_stream", "peak_amplitude",
    "stream_info",
]
