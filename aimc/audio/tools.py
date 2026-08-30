"""The external tools the whole repo depends on, and what we say when they are missing.

`ffmpeg`, `ffprobe` and `yt-dlp` were checked in three places with three
different messages for the same failure. A single message, here: it is the same
failure, and the user needs the same command line to fix it.
"""

from __future__ import annotations

import shutil

# What installs each tool on the target machine (macOS + Homebrew).
INSTALLERS = {"ffmpeg": "ffmpeg", "ffprobe": "ffmpeg", "yt-dlp": "yt-dlp"}


def missing(*names: str) -> list[str]:
    """Those of these tools that are not on the PATH, in the order asked for."""
    return [n for n in names if not shutil.which(n)]


def install_hint(names: list[str]) -> str:
    """The message to show for missing tools — empty if none are missing."""
    if not names:
        return ""
    # Two tools from the same package (ffmpeg/ffprobe) do not install it twice:
    # this is a line to copy, it has to work as-is.
    packages = dict.fromkeys(INSTALLERS.get(n, n) for n in names)
    return (f"missing tool(s): {', '.join(names)}\n"
            f"  install them with:  brew install {' '.join(packages)}")
