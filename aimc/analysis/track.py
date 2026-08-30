"""The full analysis of a track, assembled from the neighbouring measurements.

This function computes nothing itself: it chains the spectrogram, the tempo, the
boundaries, the vocals and the drops, and shapes the whole thing. Everything it
produces remains a signal-processing estimate, with no model.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from aimc.analysis.sections import VOICE_THRESHOLD, boundaries, label_for, novelty
from aimc.analysis.spectral import FPS, FREQS, SR, band, load_stereo, spectrogram
from aimc.analysis.tempo import onset_flux, tempo_of
from aimc.analysis.voice import find_drops, vocal_curve

LOW_BAND = band(0, 150)

# Below this duration, a section is only an artefact of the novelty curve.
MIN_SECTION_SECONDS = 4


@dataclass(frozen=True)
class Profiles:
    """Four curves sampled once per second, aligned with each other.

    `low` and `vocal` are arrays because we take per-section means of them;
    `rms` and `bright` stay lists, which only ever get averaged pointwise and
    serialised.
    """

    low: np.ndarray
    vocal: np.ndarray
    rms: list[float]
    bright: list[float]


def _profiles(mono: np.ndarray, spec_mid: np.ndarray, voc: np.ndarray,
              seconds: int) -> Profiles:
    """Bass energy, level, vocal presence and brightness, second by second."""
    low: list[float] = []
    rms: list[float] = []
    vocal: list[float] = []
    bright: list[float] = []
    for i in range(seconds):
        a, b = int(i * FPS), int((i + 1) * FPS)
        seg = spec_mid[a:b]
        if seg.shape[0] == 0:
            low.append(0.0)
            rms.append(0.0)
            vocal.append(0.0)
            bright.append(0.0)
            continue
        low.append(float(seg[:, LOW_BAND].sum()))
        rms.append(float(np.sqrt((mono[i * SR:(i + 1) * SR] ** 2).mean())))
        vocal.append(float(voc[a:b].mean()) if b <= len(voc) else 0.0)
        mag = seg.sum(axis=0)
        bright.append(float((mag * FREQS).sum() / (mag.sum() + 1e-9)))

    low_arr = np.array(low)
    # Normalised: bass energy only means anything relative to the rest of the track.
    low_arr /= (low_arr.max() or 1)
    return Profiles(low=low_arr, vocal=np.array(vocal), rms=rms, bright=bright)


def _cut_points(nov: np.ndarray, seconds: int) -> list[int]:
    """Section boundaries in seconds, including the ends of the track."""
    marks = [0, *(int(b / FPS) for b in boundaries(nov)), seconds]
    return sorted({b for b in marks if 0 <= b <= seconds})


def _section(start: int, end: int, flux: np.ndarray, profiles: Profiles,
             fallback_bpm: float) -> dict[str, Any]:
    """The summary of one section, between two boundaries."""
    a, b = int(start * FPS), int(end * FPS)
    seg_low = profiles.low[start:end]
    seg_voc = profiles.vocal[start:end]
    # Measured once only: it is an autocorrelation over the whole section, and
    # the value serves twice — as the tempo and as the admission of measurement.
    measured = tempo_of(flux[a:b])
    return {
        "start": start, "end": end, "duration": end - start,
        "bpm": measured or fallback_bpm,
        "bpm_measured": bool(measured > 0),
        "bass": round(float(seg_low.mean()), 3),
        "vocal": round(float(seg_voc.mean()), 3),
        "has_vocal": bool(float(seg_voc.mean()) > VOICE_THRESHOLD),
        "rms": round(float(np.mean(profiles.rms[start:end])), 4),
        "brightness": round(float(np.mean(profiles.bright[start:end])), 1),
        "label": label_for(seg_low.mean(), seg_voc.mean()),
    }


def analyse(path: Path) -> dict[str, Any]:
    """Sections, tempo, vocals and drops of a track — or `{"error": ...}`."""
    mono, side = load_stereo(path)
    if mono.size == 0:
        return {"error": "audio unreadable or empty"}

    duration = len(mono) / SR
    seconds = int(duration)
    spec_mid, spec_side = spectrogram(mono), spectrogram(side)
    flux = onset_flux(spec_mid)

    profiles = _profiles(mono, spec_mid, vocal_curve(spec_mid, spec_side), seconds)
    global_bpm = tempo_of(flux)
    cuts = _cut_points(novelty(spec_mid), seconds)
    sections = [_section(start, end, flux, profiles, global_bpm)
                for start, end in zip(cuts, cuts[1:], strict=False)
                if end - start >= MIN_SECTION_SECONDS]

    return {
        "duration": round(duration, 2),
        "tempo_global": global_bpm,
        "sections": sections,
        "drops": [int(d) for d in find_drops(profiles.low)],
        "per_second": {
            "low": [round(v, 4) for v in profiles.low.tolist()],
            "vocal": [round(v, 4) for v in profiles.vocal.tolist()],
            "rms": [round(v, 5) for v in profiles.rms],
        },
    }
