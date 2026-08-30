"""Attaching a manifest to an orphaned take, without inventing its provenance.

The whole point is not to fabricate the plausible, false provenance we are
trying to avoid: what is not known stays null, and the manifest says of itself
that it was reconstructed.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from aimc.audio import stream_info
from aimc.studio.library import fingerprint
from aimc.workspace import LYRICS, PRESETS

# <base>-seed<N>[-<timestamp>]: the name generation gives.
SEED_RE = re.compile(r"^(?P<base>.+?)-seed(?P<seed>\d+)(?:-(?P<stamp>[\d-]+))?$")

RECONSTRUCTED_WARNING = (
    "Settings reconstructed after the fact, not written by song.py. The seed is "
    "a guess read from the file name, and the version of the code that produced "
    "this take is unknown: running this command again will not necessarily "
    "reproduce it.")


class ReconstructRequest(BaseModel):
    preset: str | None = None
    lyrics: str | None = None
    seed: int | None = None
    bpm: int | None = None
    duration: float | None = None
    keyscale: str | None = None
    caption: str | None = None
    note: str | None = None
    confirm: bool = False


def _guess_preset(base: str) -> tuple[str | None, str | None]:
    """A preset is only suggested if a preset carries exactly this name.

    Suggesting "techno-pouf" because the file is called "pouf" would fabricate
    precisely the plausible, false provenance we are avoiding.
    """
    if (PRESETS / f"{base}.json").is_file():
        return f"{base}.json", None
    return None, (f'No preset is called "{base}": the file name is not enough '
                  f"to find it, so it has to be picked by hand.")


def deduce(path: Path) -> dict[str, Any]:
    """What can honestly be deduced from an orphaned take — and nothing more.

    The name gives a seed, the file gives a duration and a rate.
    """
    info = stream_info(path)
    out: dict[str, Any] = {
        "seed": None, "preset": None, "preset_note": None,
        "duration": round(info.get("duration") or 0) or None,
        "sample_rate": info.get("sample_rate"),
        "channels": info.get("channels"),
        "codec": info.get("codec_name"),
        "fingerprint": fingerprint(path),
    }
    m = SEED_RE.match(path.stem)
    if m:
        out["seed"] = int(m.group("seed"))
        out["preset"], out["preset_note"] = _guess_preset(m.group("base"))
    return out


def read_lyrics(name: str | None) -> tuple[str | None, str]:
    """The declared path and the text of the lyrics — path validated as elsewhere."""
    if not name:
        return None, ""
    src = (LYRICS / name).resolve()
    if not src.is_file() or LYRICS.resolve() not in src.parents:
        return None, ""
    return f"lyrics/{name}", src.read_text(encoding="utf-8")


def _stated_params(r: ReconstructRequest,
                   guessed: dict[str, Any]) -> dict[str, Any]:
    """What the user typed, completed by what could be deduced from the file.

    What was typed wins, including when it says "no": a field left empty stays
    empty, it does not get filled in by the deduction.
    """
    return {
        "seed": r.seed if r.seed is not None else guessed.get("seed"),
        "bpm": r.bpm,
        "keyscale": r.keyscale or "",
        "duration": r.duration if r.duration is not None else guessed.get("duration"),
        "caption": r.caption or "",
    }


def reconstructed_manifest(audio: Path, r: ReconstructRequest,
                           guessed: dict[str, Any]) -> dict[str, Any]:
    """The manifest of an orphaned take, marked for what it is.

    Two fields say "unknown" rather than invent:

      * `command` stays null — no command was observed, and fabricating one
        would make it indistinguishable from a command actually run;
      * `code` stays null, which makes the version comparison
        (`provenance.compare_code`) answer "we do not know" instead of "it
        matches".
    """
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    preset = r.preset or guessed.get("preset")
    lyrics_file, lyrics_text = read_lyrics(r.lyrics)
    params = _stated_params(r, guessed)
    deduced = [k for k in ("seed", "duration", "preset") if guessed.get(k) is not None]
    return {
        "audio": audio.name,
        "created": now,
        "provenance": "reconstruit",
        "reconstructed": {
            "at": now, "by": "studio", "warning": RECONSTRUCTED_WARNING,
            "deduced": deduced, "note": r.note or None,
        },
        "command": None,
        "preset": f"presets/{preset}" if preset else None,
        "lyrics_file": lyrics_file,
        "lyrics": lyrics_text,
        "device": None,
        "lm_backend": None,
        "models": None,
        "params": params,
        "config": {"audio_format": guessed.get("codec") or ""},
        "fingerprint": guessed.get("fingerprint"),
        "code": None,
        "audio_probe": {k: guessed.get(k) for k in
                        ("sample_rate", "channels", "codec", "duration")},
    }
