"""A file named by nothing but its name, inside the folder it belongs to.

The browser never sends a path, only a name: `pouf-seed1.wav`,
`techno-pouf.json`. Resolving it is the same operation every time — join,
resolve, and check that the result has not left the folder. It used to be
written twice, once per family of routes; a path traversal fixed on one side
only would have left the other one open.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from aimc.workspace import DOWNLOADS, SONGS

# The two folders the studio reads audio from, and the only two. A source
# arrives from the browser as one of these keys and is looked up here: the
# browser therefore names a *folder we already chose*, never one of its own.
MEDIA = {"take": SONGS, "inspiration": DOWNLOADS}


def in_dir(directory: Path, name: str, missing: str) -> Path:
    """The file `name` in this folder — 404 if it is not there, or leaves it.

    `resolve()` before the check, not after: that is what makes
    `../../etc/passwd` fail rather than letting it through unresolved.
    """
    f = (directory / name).resolve()
    if not f.is_file() or directory.resolve() not in f.parents:
        raise HTTPException(404, missing)
    return f


def media_file(source: str, name: str) -> Path:
    """The path of a take or of an inspiration, validated the same way.

    One function for both because the guard must be one function: the stem
    separation and the audio route serve either kind, and a traversal fixed on
    the takes' side alone would have left the inspirations' open — the mistake
    `in_dir` was extracted to stop.
    """
    directory = MEDIA.get(source)
    if directory is None:
        raise HTTPException(400, f"unknown source: {source}")
    return in_dir(directory, name, f"{source} not found")


def song_file(name: str) -> Path:
    """The path of a take, validated — never a path that leaves songs/."""
    return media_file("take", name)


def download_file(name: str) -> Path:
    """The path of a downloaded inspiration — never one that leaves refs/downloads/."""
    return media_file("inspiration", name)
