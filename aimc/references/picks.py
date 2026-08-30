"""The moments we decided to keep in a track, and what we heard in them.

A downloaded track is disposable: `./grab` fetches it again in a minute. What is
not disposable is the listening — "the drop at 87 s, round sub bass, one dry
male lead" — and until now that never left the head of whoever ran `./analyse`.
This module is where it lands.

So a pick is written next to the audio but *not* with it. `refs/downloads/` is
ignored by git, because the audio is under copyright and is not ours to keep in
a repository; `refs/picks/` is versioned, because a pick holds no audio, only a
second and a sentence. Deleting the whole of `refs/downloads/` therefore loses
nothing that matters, and that is deliberate.

The file is named after the audio in full, extension included — `Sweat.mp3.json`
and not `Sweat.json` — for the reason the studio's cache learned the hard way:
`X.mp3` and `X.wav` are two different tracks, and a name that dropped the
extension would silently hand one's picks to the other.

    read("Sweat.mp3")                -> {"track": …, "source": …, "picks": [ … ]}
    add("Sweat.mp3", 87, "…", { … }) -> the pick that was just written

A pick keeps either one second or a passage. `until` is what says which, and it
is not the same number as the ten seconds a reference will cut: see `add`.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from aimc.references.blend import SLOTS
from aimc.workspace import PICKS

# A style reference has three slots of 10 s, and that is imposed by the engine
# (see blend.py). Keeping more picks than that is fine — choosing more than
# three of them to build one reference is not, and the number is blend's, not a
# second copy of it.
MAX_PER_REFERENCE = SLOTS


def pick_file(track: str) -> Path:
    """Where the picks of this audio file live."""
    return PICKS / f"{track}.json"


def _blank(track: str) -> dict[str, Any]:
    return {"track": track, "source": None, "picks": []}


def read(track: str) -> dict[str, Any]:
    """The picks of this track — the empty shape when there are none.

    A missing file and a corrupt one are answered the same way, on purpose: the
    caller wants to display and add picks either way, and a hand-edited file
    that no longer parses must not take the panel down with it.
    """
    path = pick_file(track)
    if not path.is_file():
        return _blank(track)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _blank(track)
    if not isinstance(data, dict) or not isinstance(data.get("picks"), list):
        return _blank(track)
    data.setdefault("track", track)
    data.setdefault("source", None)
    return data


def write(data: dict[str, Any]) -> None:
    """Save, indented and readable: this file is versioned and gets read by people."""
    PICKS.mkdir(parents=True, exist_ok=True)
    pick_file(data["track"]).write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def add(track: str, at: int, note: str, measured: dict[str, Any],
        until: int | None = None) -> dict[str, Any]:
    """Keep a moment — or a passage — with what was measured there at the time.

    `until` is the end of the passage the measurements were read over, and null
    for a pick that quotes a single second. It is deliberately *not* what a
    reference will cut: that stays ten seconds from `at`, because ten seconds is
    what the engine reads (see `blend.py`). A pick keeping a 44 s section says
    two true things at once — the words describe the passage, the audio comes
    from its first ten seconds — where one number could only have said one.

    `measured` is a snapshot and not a reference: the analysis is re-run
    whenever the audio changes, and a pick that pointed at it would start
    describing something else. Frozen here, it still says what was heard even
    once the audio has been deleted.
    """
    data = read(track)
    pick = {"id": uuid.uuid4().hex[:8], "at": int(at),
            "until": int(until) if until is not None else None,
            "note": note, "measured": measured}
    data["picks"].append(pick)
    data["picks"].sort(key=lambda p: p.get("at", 0))
    write(data)
    return pick


def update(track: str, pick_id: str, note: str) -> dict[str, Any] | None:
    """Rewrite the words of one pick. Its span and its measurements do not move."""
    data = read(track)
    # Annotated rather than inferred: `data` is dict[str, Any], so without this
    # the pick returned here would be Any and the signature would promise
    # nothing.
    picks: list[dict[str, Any]] = data["picks"]
    for pick in picks:
        if pick.get("id") == pick_id:
            pick["note"] = note
            write(data)
            return pick
    return None


def remove(track: str, pick_id: str) -> bool:
    data = read(track)
    kept = [p for p in data["picks"] if p.get("id") != pick_id]
    if len(kept) == len(data["picks"]):
        return False
    data["picks"] = kept
    write(data)
    return True


def remember_source(track: str, url: str) -> None:
    """Record where a track came from, at the moment it is downloaded.

    Nothing else knows: `./grab` names the file after the video's title and
    keeps no trace of the URL, so an hour later `Sweat.mp3` is a track with no
    provenance. Written here rather than beside the audio, since this is the
    half of the pair that survives.
    """
    data = read(track)
    data["source"] = url
    write(data)


def counts() -> dict[str, int]:
    """How many picks each track has — for the list, without reading each file twice."""
    if not PICKS.is_dir():
        return {}
    out: dict[str, int] = {}
    for path in PICKS.glob("*.json"):
        track = path.name[: -len(".json")]
        out[track] = len(read(track)["picks"])
    return out
