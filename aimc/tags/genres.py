"""The genre database: what a genre actually is, rather than what we assume.

`refs/waxonia/` holds one JSON per genre — its aliases, the place and year it
came from, what it descends from, the tempo band it really occupies, and the
tracks a curator picked for it. Ninety-one of them at the time of writing.

Everything here tolerates the file not being there. A clone of the public repo
has no `refs/waxonia/`, and the composer still works without it: you lose the
facts, not the tool.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from aimc.workspace import REFS

DATABASE = REFS / "waxonia"


@dataclass(frozen=True)
class Genre:
    """One genre, reduced to what a style string can actually use."""

    slug: str
    name: str
    aliases: tuple[str, ...] = ()
    description: str = ""
    place: str = ""
    year: int | None = None
    bpm_min: int | None = None
    bpm_max: int | None = None
    lineage: tuple[tuple[str, str], ...] = ()      # (genre slug, what it inherited)
    curators: tuple[str, ...] = ()
    tracks: tuple[tuple[str, str], ...] = ()       # (artist, title)
    keywords: frozenset[str] = field(default_factory=frozenset)

    @property
    def bpm(self) -> str:
        if self.bpm_min is None or self.bpm_max is None:
            return "unrecorded"
        return f"{self.bpm_min}–{self.bpm_max}"

    @property
    def mid_bpm(self) -> int | None:
        """The middle of the band — a defensible starting tempo, not a rule."""
        if self.bpm_min is None or self.bpm_max is None:
            return None
        return (self.bpm_min + self.bpm_max) // 2

def _curators(raw: object) -> tuple[str, ...]:
    """`curatedBy` is a list of names, of dicts with a name, or absent."""
    if not isinstance(raw, list):
        return ()
    out = []
    for entry in raw:
        if isinstance(entry, str):
            out.append(entry)
        elif isinstance(entry, dict):
            name = entry.get("name") or entry.get("displayName") or entry.get("slug")
            if name:
                out.append(str(name))
    # A genre may name the same desk once per playlist it appears in. One
    # mention is the fact; the repetition is bookkeeping.
    return tuple(dict.fromkeys(out))


def _genre(data: dict) -> Genre:
    # bpm and origin are dicts when present and null when the database does not
    # know — which is not the same as zero, and must not become one.
    bpm = data.get("bpm") or {}
    origin = data.get("origin") or {}
    aliases = tuple(str(a) for a in data.get("aliases") or ())
    name = str(data.get("name") or data.get("slug") or "")
    curators = _curators(data.get("curatedBy"))
    tracks = tuple((str(t.get("artist", "")), str(t.get("title", "")))
                   for t in data.get("tracks") or () if isinstance(t, dict))
    lineage = tuple((str(step.get("genre", "")), str(step.get("inherited", "")))
                    for step in data.get("lineage") or () if isinstance(step, dict))
    keywords = {w.lower() for w in (name, data.get("slug", ""), *aliases,
                                    origin.get("place", ""), *curators) if w}
    return Genre(
        slug=str(data.get("slug") or ""),
        name=name,
        aliases=aliases,
        description=str(data.get("description") or ""),
        place=str(origin.get("place") or ""),
        year=origin.get("year"),
        bpm_min=bpm.get("min"),
        bpm_max=bpm.get("max"),
        lineage=lineage,
        curators=curators,
        tracks=tracks,
        keywords=frozenset(keywords),
    )


def load(database: Path | None = None) -> list[Genre]:
    """Every genre in the database, by name. Empty when there is no database."""
    folder = database or DATABASE
    if not folder.is_dir():
        return []
    genres = []
    for path in sorted(folder.glob("*.json")):
        if path.stem.startswith("_"):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue      # one unreadable file is not worth losing ninety over
        if isinstance(data, dict):
            genres.append(_genre(data))
    return sorted(genres, key=lambda g: g.name.lower())


def search(genres: list[Genre], query: str) -> list[Genre]:
    """Genres whose name, alias, city or curator contains the query.

    Substring rather than fuzzy: "house" should find deep house and acid house
    and nothing surprising, and a typo should find nothing rather than something
    plausible-looking.
    """
    q = query.strip().lower()
    if not q:
        return genres
    return [g for g in genres if any(q in k for k in g.keywords)]


def curators(genres: list[Genre]) -> dict[str, list[Genre]]:
    """Curator -> the genres they curated. Only some genres have one."""
    out: dict[str, list[Genre]] = {}
    for g in genres:
        for name in g.curators:
            listed = out.setdefault(name, [])
            if g not in listed:
                listed.append(g)
    return dict(sorted(out.items()))
