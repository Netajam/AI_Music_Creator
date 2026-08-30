"""The analysis cache: expensive to compute, invalidated as soon as the audio changes.

Kept apart from the measurements it holds, and deliberately so: when the two
lived together, the cache called the measurement which called the cache back,
and the dependency graph went in circles with nothing requiring it. Here the
cache knows no measurement — it is handed a function and files away what it
returns.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar, cast

from aimc.workspace import CACHE

# `cached` returns exactly what `produce` produced: without this type parameter,
# every caller would fall back to Any and their return annotation would no
# longer promise anything.
T = TypeVar("T")

log = logging.getLogger("studio")


def _key(path: Path) -> str:
    """Per-file cache key: the folder it sits in, then its name, extension included.

    Keying on the stem alone made `pouf-seed1.mp3` and `pouf-seed1.wav` evict
    each other on every lookup — two files with the same name that are precisely
    two different takes, which is what the fingerprint exists to show.

    The folder joined the key when the studio started analysing inspirations as
    well as takes, and for the same reason one step out: `cached` sweeps every
    slot sharing a key, so `songs/X.wav` and `refs/downloads/X.wav` would have
    deleted each other's analyses on every open — including a stem separation
    that costs a minute to rebuild.
    """
    return f"{path.parent.name}-{path.name.replace('.', '_')}"


# The cache is invalidated by the audio (mtime + size), not by the code: an
# analysis whose *text* changes — section labels, reasons for not being
# publishable — would therefore keep serving the old version indefinitely. This
# number is the way out: bumping it by one expires the whole cache.
#
# Bump it when a cached analysis changes what it returns. The cost is one
# recomputation per take, on demand, without blocking the list (see `peek`).
#
#   2 — the interface moving to English: `structure` returned French labels and
#       `ready` returned French reasons.
#   3 — `energy` gained its band balance: a profile cached at version 2 holds a
#       bass curve and nothing about the mids and the highs.
#   4 — the key gained the folder (see `_key`). Nothing about the *contents*
#       changed here, so this bump buys nothing on its own; it is the record of
#       a rename that leaves entries written under the old key unmatched by any
#       glob. They are dead weight in a folder that is derived, gitignored and
#       safe to delete outright — `rm -rf .studio-cache` is the whole cleanup.
CACHE_VERSION = 4


def _slot(path: Path, kind: str) -> Path:
    """Cache file invalidated as soon as the audio changes (mtime + size)."""
    CACHE.mkdir(exist_ok=True)
    st = path.stat()
    return (CACHE /
            f"{_key(path)}-{kind}-v{CACHE_VERSION}-{st.st_mtime_ns}-{st.st_size}.json")


def cached(path: Path, kind: str, produce: Callable[[], T]) -> T:
    """The cached value, or the one `produce` computes — and which we file away."""
    slot = _slot(path, kind)
    if slot.exists():
        try:
            # The cache is JSON written by `produce` itself: it has its shape by
            # construction, but json.loads cannot know that.
            return cast(T, json.loads(slot.read_text()))
        except json.JSONDecodeError:
            slot.unlink(missing_ok=True)
    data = produce()
    try:
        slot.write_text(json.dumps(data))
    except TypeError as exc:            # unserialisable type: we serve it anyway
        log.warning("cache %s skipped: %s", kind, exc)
        return data
    for old in CACHE.glob(f"{_key(path)}-{kind}-*.json"):
        if old != slot:
            old.unlink(missing_ok=True)
    return data


def store(path: Path, kind: str, data: Any) -> None:
    """File away a value computed elsewhere — by a subprocess, typically.

    `cached` only knows how to produce on demand, inside the calling process.
    Lyric alignment, by contrast, runs in a separate `./analyse --align`,
    precisely so that torch's gigabyte and a half is handed back to the system
    at the end. The result therefore comes back through a file, and enters here.
    """
    slot = _slot(path, kind)
    slot.write_text(json.dumps(data))
    for old in CACHE.glob(f"{_key(path)}-{kind}-*.json"):
        if old != slot:
            old.unlink(missing_ok=True)


def peek(path: Path, kind: str) -> Any:
    """A value already in cache, or None — never computes.

    This is what lets the list of takes appear immediately: it serves what is
    known, and the browser asks for the rest take by take (`/api/probe`) without
    blocking the display.
    """
    try:
        slot = _slot(path, kind)
    except OSError:
        return None
    if not slot.exists():
        return None
    try:
        return json.loads(slot.read_text())
    except json.JSONDecodeError:
        return None
