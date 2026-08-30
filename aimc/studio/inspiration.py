"""What the studio knows about a track we did not make.

An inspiration is a track fetched by `./grab` and sitting in `refs/downloads/`.
It is read with the same analysis as a take — the same sections, the same
tempo, the same band lanes, the same stems — because the analysis never cared
which folder the audio was in. What it is *not* read with is everything a take
carries and a foreign track cannot: a manifest, a seed, a fingerprint to compare
against, a verdict on whether it is fit to publish. There is no manifest to
find, no code that produced it, and it will never be published.

Hence a route of its own rather than a widened `/api/take`. Half the fields of
that answer would have come back null, and a contract that is empty half the
time is a contract nobody can rely on.

What this module adds on top of the analysis is the one thing measurement
cannot supply: the words. `measured_at` gathers everything the machine can say
about one second of the track and `measured_over` the same about a passage of
it, `picks` keeps what the listener says about either, and the two travel
together into a style reference.

Both scales are here because both questions get asked. "What is happening at
87 s" is answered by a second; "what is this drop like" is not, and reading it
off the one second the playhead happens to sit on is how a passage gets
described by its least representative instant.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from aimc.references import picks as picks_store
from aimc.studio.library.cache import peek
from aimc.studio.library.measures import energy_profile, stems, structure
from aimc.studio.library.paths import download_file
from aimc.workspace import AUDIO_EXT, DOWNLOADS, LOSSLESS_EXT, REFS, unique_path


def _entry(f: Path) -> dict[str, Any]:
    """One row of the list. Computes nothing: opening a track is what analyses it.

    `analysed` comes from `peek` and not from `structure`, deliberately — the
    same reason the takes list does not measure loudness. Eight downloads would
    otherwise cost eight full decodes before the panel could draw anything.
    """
    st = f.stat()
    saved = picks_store.read(f.name)
    return {
        "name": f.name,
        "size_mb": round(st.st_size / 1e6, 1),
        "modified": time.strftime("%d/%m %H:%M", time.localtime(st.st_mtime)),
        "lossless": f.suffix.lower() in LOSSLESS_EXT,
        "analysed": peek(f, "structure") is not None,
        "separated": peek(f, "stems") is not None,
        "picks": len(saved["picks"]),
        "source": saved["source"],
    }


def listing() -> list[dict[str, Any]]:
    """The downloaded tracks, newest first."""
    if not DOWNLOADS.is_dir():
        return []
    return [_entry(f)
            for f in sorted(DOWNLOADS.iterdir(), key=lambda p: p.stat().st_mtime,
                            reverse=True)
            if f.is_file() and f.suffix.lower() in AUDIO_EXT]


def detail(name: str) -> dict[str, Any]:
    """Everything the studio can draw about one inspiration.

    `energy` and `structure` are computed on first open and cached from then on;
    `stems` is only ever served if a separation has already been run, since one
    costs a third of the track's length.
    """
    f = download_file(name)
    saved = picks_store.read(f.name)
    return {
        "name": f.name,
        "energy": energy_profile(f),
        "structure": structure(f),
        "stems": stems(f),
        "source": saved["source"],
        "picks": saved["picks"],
    }


def _section_at(struct: dict[str, Any] | None, at: int) -> dict[str, Any] | None:
    """The section covering this second — upper bound excluded, as everywhere else.

    The rule matches the playhead's in the browser (`sectionAt`): at the exact
    second of a boundary the section that *starts* owns it. Two answers to that
    question would put a pick in one section on the graph and another one in its
    own record.
    """
    sections = (struct or {}).get("sections") or []
    for section in sections:
        if section["start"] <= at < section["end"]:
            return dict(section)
    return dict(sections[-1]) if sections and at >= sections[-1]["end"] else None


def _sections_over(struct: dict[str, Any] | None, start: int,
                   end: int) -> list[dict[str, Any]]:
    """Every section the passage touches, each with the seconds it lends to it.

    A passage is under no obligation to respect the analysis' boundaries, so
    `overlap` travels with each section. Without it, one clipped to two seconds
    would read in the record exactly like one carrying the whole passage.
    """
    out: list[dict[str, Any]] = []
    for section in (struct or {}).get("sections") or []:
        overlap = min(end, section["end"]) - max(start, section["start"])
        if overlap > 0:
            out.append({**section, "overlap": overlap})
    return out


def _at(curve: list[float], at: int) -> float | None:
    """One second of a curve — None if the curve does not reach that far."""
    return round(float(curve[at]), 4) if 0 <= at < len(curve) else None


def _mean(curve: list[float], start: int, end: int) -> float | None:
    """A curve averaged over a passage — None if the passage falls outside it.

    The mean and not the peak: what a passage is *like* is what it holds for
    most of its length, and a single loud second inside a quiet minute is a
    drop, which `structure` already names in its own field.
    """
    window = curve[max(start, 0):max(end, 0)]
    if not window:
        return None
    return round(sum(float(v) for v in window) / len(window), 4)


def _stem_shares(separated: dict[str, Any] | None,
                 read: Callable[[list[float]], float | None],
                 ) -> dict[str, Any] | None:
    """What each stem holds, read out of its own curve by `read`.

    None rather than a row of zeros when nothing has been separated: Demucs is
    the one measurement here that has to be asked for, and "no vocals in this
    passage" and "we never looked" are not the same answer.
    """
    if not separated or not separated.get("sources"):
        return None
    per_second = separated.get("per_second") or {}
    return {"model": separated.get("model"),
            "shares": {source: read(per_second.get(source) or [])
                       for source in separated["sources"]}}


# Two sections closer than this hold the same tempo: the measurement is an
# autocorrelation over a window, and it does not land on the same tenth twice.
BPM_AGREEMENT = 2.0


def _tempo_over(sections: list[dict[str, Any]],
                tempo_global: float | None) -> dict[str, Any]:
    """The tempo of a whole passage — or the admission that it has more than one.

    Never an average of tempos that disagree: 100 and 128 average to 114, a
    figure true of no second of the passage, and it is this number that goes on
    to fill the composer's BPM field. Sections that agree are averaged — they
    are one pulse measured twice — and sections that disagree yield nothing and
    say `varies`, which is itself the thing worth knowing before cutting a
    reference here.
    """
    measured = [float(s["bpm"]) for s in sections if s.get("bpm_measured")]
    if not measured:
        return {"bpm": tempo_global, "measured": False, "varies": False}
    if max(measured) - min(measured) > BPM_AGREEMENT:
        return {"bpm": None, "measured": False, "varies": True}
    return {"bpm": round(sum(measured) / len(measured), 1),
            "measured": True, "varies": False}


def measured_at(name: str, at: int) -> dict[str, Any]:
    """Everything the machine can say about one second of a track.

    Frozen into the pick that quotes it. Three sources, and they do not have the
    same standing, so each is named rather than merged into one flat verdict:
    the section comes from signal processing, the bands from a three-way split
    of the spectrum, and `stems` from Demucs — present only if a separation has
    been run, absent rather than guessed if it has not.
    """
    f = download_file(name)
    struct = structure(f)
    energy = energy_profile(f)
    return {
        "at": at,
        "section": _section_at(struct, at),
        "bands": {key: _at(energy.get(key) or [], at)
                  for key in ("low", "mid", "high")},
        "tempo_global": struct.get("tempo_global"),
        "stems": _stem_shares(stems(f), lambda curve: _at(curve, at)),
    }


def measured_over(name: str, start: int, end: int) -> dict[str, Any]:
    """Everything the machine can say about a passage, from `start` to `end`.

    The same three sources as `measured_at`, and deliberately not a superset of
    its answer: a second sits in one section, a passage crosses a list of them;
    a second has a band value, a passage has an average. Naming them the same
    way is what lets a pick quoting a passage read like a pick quoting a moment.

    `end` is excluded, as everywhere else in the studio: a passage from 87 to
    131 holds 44 seconds, and the second at 131 belongs to what comes next.
    """
    f = download_file(name)
    struct = structure(f)
    energy = energy_profile(f)
    sections = _sections_over(struct, start, end)
    return {
        "start": start, "end": end, "seconds": end - start,
        "sections": sections,
        "bands": {key: _mean(energy.get(key) or [], start, end)
                  for key in ("low", "mid", "high")},
        "tempo": _tempo_over(sections, struct.get("tempo_global")),
        "tempo_global": struct.get("tempo_global"),
        "drops": [d for d in (struct.get("drops") or []) if start <= d < end],
        "stems": _stem_shares(stems(f), lambda curve: _mean(curve, start, end)),
    }


def slug(name: str) -> str:
    """A file name turned into something safe to build a reference name out of."""
    stem = Path(name).stem.lower()
    kept = [c if c.isalnum() else "-" for c in stem]
    return "-".join(part for part in "".join(kept).split("-") if part) or "reference"


def reference_path(name: str) -> Path:
    """A free path in refs/ for the reference built from this track.

    `unique_path` here as well as inside `blend-refs`: the studio has to know the
    name it is going to serve back to the browser, and reading it out of blend's
    stdout would mean parsing a sentence written for a human.
    """
    return unique_path(REFS / f"{slug(name)}-style.wav")
