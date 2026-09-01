"""The model's own style vocabulary, used as a spell-check rather than a rule.

`engine/acestep/genres_vocab.txt` is the list of style terms ACE-Step was
trained against — 178,571 of them, and famously not one artist name, which is
why "in the style of <artist>" does nothing and a description does everything.

What this can honestly say is narrow, and worth stating: a term that *is* in the
list is one the model has certainly seen. A term that is not may still work —
`--style` is free prose and the model reads it as prose — it simply has no
evidence behind it. So nothing here rejects anything. It marks.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from aimc.workspace import ENGINE_ROOT

VOCABULARY = ENGINE_ROOT / "acestep" / "genres_vocab.txt"


@lru_cache(maxsize=1)
def load(path: Path | None = None) -> tuple[str, ...]:
    """Every term, in file order. Empty when `engine/` has not been cloned."""
    source = path or VOCABULARY
    if not source.is_file():
        return ()
    text = source.read_text(encoding="utf-8", errors="replace")
    return tuple(line.strip() for line in text.splitlines() if line.strip())


@lru_cache(maxsize=1)
def _index() -> frozenset[str]:
    return frozenset(term.lower() for term in load())


def known(term: str) -> bool:
    """Whether the model has this exact term in its vocabulary."""
    return term.strip().lower() in _index()


def suggest(fragment: str, limit: int = 12) -> list[str]:
    """Vocabulary terms containing the fragment, shortest first.

    Shortest first because the short ones are the genre names — "acid house"
    before "acid house revival compilation" — and a style string has 512
    characters to spend.
    """
    needle = fragment.strip().lower()
    if not needle:
        return []
    hits = [t for t in load() if needle in t.lower()]
    hits.sort(key=lambda t: (len(t), t.lower()))
    return hits[:limit]


def check(style: str) -> list[tuple[str, bool]]:
    """Each comma-separated fragment of a style string, and whether it is known.

    A style is prose and most of its fragments are descriptions rather than
    genre names, so most of these come back False and that is not a fault. The
    ones that come back True are the load-bearing ones.
    """
    return [(part, known(part))
            for part in (p.strip() for p in style.split(",")) if part]
