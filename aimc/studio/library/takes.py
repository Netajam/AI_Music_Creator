"""The takes in songs/: listing them, reading their manifest, flagging the traps."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from aimc.provenance import manifest_for, short_fingerprint
from aimc.studio.library.cache import peek
from aimc.workspace import AUDIO_EXT, LOSSLESS_EXT, SONGS

# A protocol value written into the manifest by a reconstruction. It is on disk
# for every reconstructed take: it does not move.
RECONSTRUCTED = "reconstruit"


def read_manifest(path: Path) -> dict[str, Any] | None:
    """A take's manifest, or None. A damaged JSON does not break the list."""
    manifest = manifest_for(path)
    if manifest is None:
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def manifest_kind(data: dict[str, Any] | None) -> str | None:
    """"original" (written by generation) or "reconstructed" (attached afterwards).

    The two are not worth the same: a reconstructed manifest contains guesses.
    Conflating them would recreate, in a worse form, the problem being fixed — a
    plausible and false provenance.

    These two values are a protocol, not a label: `studio.html` compares them
    as-is. Translating them again would mean revisiting the comparisons too,
    without which the "reconstructed settings" warning would silently stop
    appearing. They show up nowhere on screen: what the user reads is written in
    `studio.html`.
    """
    if data is None:
        return None
    return "reconstructed" if data.get("provenance") == RECONSTRUCTED else "original"


def _entry(f: Path) -> dict[str, Any]:
    """One row of the list: what is already known, and nothing that must be computed."""
    data = read_manifest(f)
    ready = peek(f, "ready")
    fp = (data or {}).get("fingerprint") or (peek(f, "fingerprint") or {}).get("value")
    st = f.stat()
    return {
        "name": f.name,
        "stem": f.stem,
        "size_mb": round(st.st_size / 1e6, 1),
        "modified": time.strftime("%d/%m %H:%M", time.localtime(st.st_mtime)),
        "lossless": f.suffix.lower() in LOSSLESS_EXT,
        "has_manifest": data is not None,
        "manifest_kind": manifest_kind(data),
        "fingerprint": fp,
        "fingerprint_short": short_fingerprint(fp),
        # None until the measurement has been made: "we do not know yet" is
        # neither "ready" nor "not ready".
        "ready": ready.get("ready") if ready else None,
        "missing": ready.get("missing") if ready else None,
    }


def takes() -> list[dict[str, Any]]:
    """List of takes. Computes nothing: what is missing arrives via /api/probe."""
    if not SONGS.is_dir():
        return []
    entries = [_entry(f)
               for f in sorted(SONGS.iterdir(), key=lambda p: p.stat().st_mtime,
                               reverse=True)
               if f.suffix.lower() in AUDIO_EXT]
    mark_collisions(entries)
    return entries


def mark_collisions(entries: list[dict[str, Any]]) -> None:
    """Flag two files sharing a stem that do not contain the same take.

    `pouf-seed1.mp3` and `pouf-seed1.wav` share nothing (waveform correlation
    0.028) and nothing said so: you had to run a cross-correlation to notice.

    Two takes with different names are never in collision, even when one came
    from the other: a repaint is a distinct take, not a namesake.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for e in entries:
        groups.setdefault(e["stem"], []).append(e)
    for group in groups.values():
        # A single known fingerprint, or all identical: nothing to flag. A group
        # of one file cannot have two distinct ones, so this test also covers the
        # common case.
        if len({e["fingerprint"] for e in group if e["fingerprint"]}) < 2:
            continue
        for e in group:
            others = [o["name"] for o in group if o["name"] != e["name"]]
            e["collision"] = (
                f"Same name as {', '.join(others)}, but not the same sound: "
                f"these files share a name and do not hold the same take. "
                f"Check which one you are publishing.")


def read_dir(path: Path, suffix: str) -> list[str]:
    return sorted(p.name for p in path.glob(f"*{suffix}")) if path.is_dir() else []
