"""Finding the settings file that belongs to a take."""

from __future__ import annotations

import json
from pathlib import Path


def manifest_for(audio: Path) -> Path | None:
    """The manifest that belongs to this take — not its namesake's.

    Generation writes `<stem>.json` next to the audio, which is enough as long
    as the names are unique. They are not: `pouf-seed1.mp3` and
    `pouf-seed1.wav` point at the same settings file even though they do not
    contain the same take. Two safeguards:

      * a manifest can also live at `<full filename>.json` (`x.mp3.json`), with
        no possible ambiguity — that is where a reconstruction writes;
      * a `<stem>.json` is only accepted if its `audio` field really does name
        this file.
    """
    per_file = audio.with_name(audio.name + ".json")
    if per_file.is_file():
        return per_file
    beside = audio.with_suffix(".json")
    if not beside.is_file():
        return None
    try:
        data = json.loads(beside.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return beside if data.get("audio") in (None, audio.name) else None
