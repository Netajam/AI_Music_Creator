"""What the studio measures about a take — always through the cache.

Each of these measurements costs a full decode of the file. They are therefore
never recomputed while the audio has not changed, and the list of takes does not
wait for them: it serves what is already known (`cache.peek`) and the browser
asks for the rest take by take.
"""

from __future__ import annotations

import contextlib
import subprocess
from pathlib import Path
from typing import Any

from aimc.audio import stream_info
from aimc.mastering import publishable, tail_amplitude
from aimc.provenance import audio_fingerprint, compare_code
from aimc.studio.library.cache import cached, peek
from aimc.studio.library.takes import read_manifest

# The energy profile's rate: we are after a shape to draw, not an analysis —
# 16 kHz mono is enough and decodes four times faster.
ENERGY_SR = 16000
LOW_HZ = 150

# The two cuts that split the spectrum into three bands. The lower one is LOW_HZ
# and not a value of its own: the mids must start exactly where the bass bars
# stop, and two constants would eventually drift apart.
#
# 2 kHz separates the body of an arrangement — bass harmonics, keys, guitars,
# the fundamentals of a voice — from what is heard as presence and air: hats,
# cymbals, sibilance. The top of the last band is the Nyquist of ENERGY_SR,
# 8 kHz: this profile says nothing above that, so a track's actual air sits
# outside what it can see.
MID_HZ = 2000


def _compute_energy(path: Path) -> dict[str, Any]:
    # numpy is only pulled in if a take is actually opened.
    import numpy as np

    from aimc.audio import decode

    raw = decode(path, rate=ENERGY_SR, channels=1)
    x = np.frombuffer(raw, dtype=np.float32)
    if x.size == 0:
        return {"duration": 0, "rms": [], "low": [], "mid": [], "high": []}

    freqs = np.fft.rfftfreq(ENERGY_SR, 1 / ENERGY_SR)
    masks = {"low": freqs < LOW_HZ,
             "mid": (freqs >= LOW_HZ) & (freqs < MID_HZ),
             "high": freqs >= MID_HZ}
    window = np.hanning(ENERGY_SR)

    rms: list[float] = []
    bands: dict[str, list[float]] = {name: [] for name in masks}
    for i in range(len(x) // ENERGY_SR):
        seg = x[i * ENERGY_SR:(i + 1) * ENERGY_SR]
        rms.append(float(np.sqrt((seg ** 2).mean())))
        spec = np.abs(np.fft.rfft(seg * window))
        for name, mask in masks.items():
            bands[name].append(float(spec[mask].sum()))

    return {"duration": len(x) / ENERGY_SR,
            "rms": [round(v, 5) for v in rms],
            **{name: _own_scale(curve) for name, curve in bands.items()}}


def _own_scale(curve: list[float]) -> list[float]:
    """A band against its own loudest second — 0 to 1.

    Each band is scaled by its own maximum, and not by a share of the three.
    Shares were tried first and read as a flat block: a share is biased by the
    width of the band, and the mids span thirteen times more spectrum than the
    bass. Measured on `all-dayggering-seed7`, the mids held between 49% and 80%
    of the total from end to end — a number that moves that little draws
    nothing.

    Against its own maximum, each band answers the question actually being
    asked: when is this one carrying the track. The price is that the three
    curves are no longer comparable with each other — a mid at 0.8 is not
    "louder" than a high at 0.4, it is closer to its own peak. Which is why they
    are drawn as three lanes and never stacked.

    These are FFT bands, not instruments: a kick and a bass line share the low
    one, a hi-hat and a cymbal the high one, and a voice is spread over the two
    upper ones. Naming what plays takes `aimc.analysis.stems`.
    """
    peak = max(curve, default=0.0) or 1.0
    return [round(v / peak, 4) for v in curve]


def energy_profile(path: Path) -> dict[str, Any]:
    """Level and three band curves per second — low, mid, high. Cached."""
    return cached(path, "energy", lambda: _compute_energy(path))


def _compute_loudness(path: Path) -> dict[str, Any]:
    out = subprocess.run(
        ["ffmpeg", "-nostats", "-i", str(path), "-af", "ebur128=peak=true",
         "-f", "null", "-"], capture_output=True, text=True).stderr
    res: dict[str, Any] = {}
    tail = out.split("Summary:")[-1] if "Summary:" in out else ""
    for key, label in (("I:", "lufs"), ("LRA:", "lra"), ("Peak:", "peak")):
        for line in tail.splitlines():
            if line.strip().startswith(key):
                with contextlib.suppress(IndexError, ValueError):
                    res[label] = float(line.split()[1])
                break
    return res


def loudness(path: Path) -> dict[str, Any]:
    return cached(path, "loudness", lambda: _compute_loudness(path))


def _compute_structure(path: Path) -> dict[str, Any]:
    # Deferred import: the analysis pulls in numpy, which the studio's startup
    # should not pay for while no take has been opened.
    from aimc.analysis import analyse

    return analyse(path)


def structure(path: Path) -> dict[str, Any]:
    """Structural analysis (sections, tempo, vocals, drops), cached."""
    return cached(path, "structure", lambda: _compute_structure(path))


def alignment(path: Path, lyrics: str | None) -> dict[str, Any] | None:
    """The lyric alignment, if one exists *and* it speaks of today's text.

    The cache is keyed on the audio — mtime and size — and not on the text. A
    manifest rewritten over an unchanged take would therefore keep serving the
    old text's alignment, silent about the fact that it no longer matches. The
    digest filed alongside the result is what makes that noticeable.

    Never computes: alignment costs a minute and a gigabyte-sized model, and is
    asked for explicitly (`/api/align`).
    """
    from aimc.analysis.lyrics import lyrics_digest

    data = peek(path, "alignment")
    if not isinstance(data, dict):
        return None
    if lyrics is None or data.get("lyrics_digest") != lyrics_digest(lyrics):
        return None
    return data


def stems(path: Path) -> dict[str, Any] | None:
    """The stem separation, if one has already been run on this audio.

    Never computes, like `alignment` and for a heavier reason: a separation
    costs about a third of the track's duration and peaks at 2.3 GB, which is
    not something a click on a take should set off. It is asked for explicitly
    (`/api/stems/{name}`), and the cache key on mtime and size is enough here —
    unlike the alignment, nothing outside the audio can make the answer stale.
    """
    data = peek(path, "stems")
    return data if isinstance(data, dict) else None


def fingerprint(path: Path) -> str | None:
    """Fingerprint of the audio content — the manifest's if it holds one.

    A take with no manifest has none recorded; we then compute it on the fly,
    cached like the other analyses, so that it can still take part in the
    comparison.
    """
    recorded: str | None = (read_manifest(path) or {}).get("fingerprint")
    if recorded:
        return recorded
    slot = cached(path, "fingerprint", lambda: {"value": audio_fingerprint(path)})
    return slot.get("value")


def _compute_readiness(path: Path) -> dict[str, Any]:
    info = stream_info(path)
    loud = loudness(path)
    verdict = publishable(info.get("codec_name"), loud.get("lufs"),
                          loud.get("peak"), tail_amplitude(path))
    verdict["codec"] = info.get("codec_name")
    verdict["measured"] = {"lufs": loud.get("lufs"), "peak": loud.get("peak"),
                           "lra": loud.get("lra")}
    return verdict


def readiness(path: Path) -> dict[str, Any]:
    """"Can this one ship?" — the verdict from `mastering.publishable`.

    The measurements are the ones the studio already makes (`loudness`, EBU
    R128), plus the tail amplitude `./master` uses. The rule and the thresholds
    come from mastering: here we only gather the numbers.
    """
    return cached(path, "ready", lambda: _compute_readiness(path))


def code_status(data: dict[str, Any] | None) -> dict[str, Any]:
    """Was this take produced by the code that is present today?"""
    recorded = (data or {}).get("code")
    out = compare_code(recorded)
    out["recorded"] = recorded
    return out
