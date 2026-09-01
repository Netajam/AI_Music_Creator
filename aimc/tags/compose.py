"""Assembling a style and a negative, and noticing when you repeat yourself.

Two things this holds that a blank prompt does not.

The **512-character limit**: the CLI rejects a longer `--style`, and only after
the preset has loaded, so it is worth knowing while writing rather than after.

And the **variety count**. Ninety of the first hundred presets asked for "a low
male voice" and the same ninety forbade female vocals; the tempo range was wide,
the genres were genuinely different, and underneath all of them was one
songwriter in ten costumes. `docs/variety.md` records what that cost. So this
reads the presets already in the workspace and says what they have been asking
for, before you ask for it again.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

STYLE_MAX = 512     # the CLI's own limit, in aimc/generation/command/catalog.py

# Menus, not rules. Each exists because a blank field invites the same answer
# every time, which is the mechanism variety.md describes.
VOICES = (
    "instrumental, no voice",
    "low male voice, close to the microphone",
    "high male voice, strained",
    "female lead vocal, breathy",
    "female lead vocal, belted",
    "two voices in harmony",
    "a choir",
    "spoken word",
    "sung-spoken, half-rapped",
    "child voice",
    "wordless vocal, used as an instrument",
)

PRODUCTION = (
    "warm analogue tape, room ambience",
    "dry and close, almost no reverb",
    "enormous reverb, submerged",
    "lo-fi, hiss and vinyl crackle",
    "modern loud digital master",
    "live take, one room, bleed between microphones",
    "gated and compressed, eighties",
    "sparse and wide, a lot of space",
)

MOODS = (
    "euphoric", "melancholic", "menacing", "tender", "furious",
    "hypnotic", "playful", "grieving", "triumphant", "resigned", "anxious",
)


@dataclass
class Style:
    """The parts of a style string, kept separate until the moment of writing."""

    genre: str = ""
    era: str = ""
    instruments: list[str] = field(default_factory=list)
    voice: str = ""
    production: str = ""
    mood: str = ""
    extra: list[str] = field(default_factory=list)

    def parts(self) -> list[str]:
        return [p for p in (self.genre, self.era, *self.instruments, self.voice,
                            self.production, self.mood, *self.extra) if p]

    def render(self) -> str:
        return ", ".join(self.parts())

    @property
    def length(self) -> int:
        return len(self.render())

    @property
    def over(self) -> int:
        """Characters past the limit; zero or negative means it fits."""
        return self.length - STYLE_MAX + 1


# A negative says what the model must avoid. These are the groups that have
# actually earned their place; nothing is applied unless it is chosen.
NEGATIVES = {
    "voice": "vocals, singing, lyrics, spoken word",
    "female lead": "female lead vocals, falsetto",
    "male lead": "male lead vocals",
    "modern EDM": "EDM drop, riser, sidechain pumping, festival build-up",
    "clutter": "busy arrangement, cluttered mix, too many instruments",
    "guitars": "distorted guitar, guitar solo",
    "orchestra": "orchestra, strings section, cinematic swell",
    "speed": "fast tempo, double time, breakbeat",
    "lo-fi": "lo-fi, muddy mix, tape hiss",
    "trap": "trap hi-hats, 808 slides, autotune",
}

# Counted per preset, not per word. "voix masculine grave" is one preset asking
# for a male voice, and counting its words instead would report it as two
# half-facts — which is how a run of ninety hides inside a percentage.
VOICE_KINDS: dict[str, re.Pattern[str]] = {
    "a male voice": re.compile(
        r"\b(male|masculine?|homme|baritone|baryton|tenor|t[ée]nor)\b", re.I),
    "a female voice": re.compile(
        r"\b(female|f[ée]minine?|femme|soprano|falsetto)\b", re.I),
    "no voice": re.compile(r"\b(instrumental|no voice|sans voix)\b", re.I),
    "spoken word": re.compile(r"\b(spoken|parl[ée]|rap(?:ped)?)\b", re.I),
    "a choir": re.compile(r"\b(choir|chorale|ch[oœ]ur)\b", re.I),
}


def usage(presets: Path, limit: int = 300) -> tuple[Counter, int]:
    """How many presets here ask for each kind of voice.

    One preset contributes at most one to each kind, which is what
    docs/variety.md counted when it found ninety of a hundred asking for a low
    male voice. Counting words instead splits "voix masculine" into two and
    reports a run of ninety as a pair of forty-fives.
    """
    counts: Counter = Counter()
    seen = 0
    if not presets.is_dir():
        return counts, 0
    for path in sorted(presets.rglob("*.json"))[:limit]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict) or "style" not in data:
            continue
        seen += 1
        if data.get("instrumental"):
            counts["no voice"] += 1
            continue
        for kind, pattern in VOICE_KINDS.items():
            if pattern.search(str(data.get("style", ""))):
                counts[kind] += 1
    return counts, seen


def preset(style: Style, negative: str, bpm: int | None, key: str,
           duration: int, language: str, instrumental: bool,
           lyrics: str | None) -> dict[str, object]:
    """The preset this composes to — the same shape every other preset has."""
    out: dict[str, object] = {"style": style.render()}
    if negative:
        out["negative"] = negative
    out["language"] = language
    if bpm:
        out["bpm"] = bpm
    if key:
        out["key"] = key
    out["duration"] = duration
    if instrumental:
        out["instrumental"] = True
    elif lyrics:
        out["lyrics"] = lyrics
    return out
