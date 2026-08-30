"""Cutting a track into sections, and giving them a name."""

from __future__ import annotations

import numpy as np

from aimc.analysis.spectral import FPS, SR, band

# Six bands that roughly follow the way we hear an arrangement: bass, low mids,
# mids, high mids, highs, brilliance.
TIMBRE_BANDS = [(0, 120), (120, 400), (400, 1200),
                (1200, 3500), (3500, 8000), (8000, SR / 2)]

# Above this mean vocal presence, we consider the section sung.
VOICE_THRESHOLD = 0.34


def novelty(spec: np.ndarray, width_s: float = 3.0) -> np.ndarray:
    """Novelty curve: how much the sound changes from one moment to the next.

    We compare the mean timbre of the preceding `width_s` seconds with that of
    the following ones. A peak = a likely section boundary.
    """
    if spec.shape[0] == 0:
        return np.zeros(0, np.float32)
    bands = np.stack([spec[:, band(lo, hi)].sum(axis=1)
                      for lo, hi in TIMBRE_BANDS], axis=1)
    bands = np.log1p(bands)
    bands /= (np.linalg.norm(bands, axis=1, keepdims=True) + 1e-9)

    w = int(width_s * FPS)
    out = np.zeros(len(bands), np.float32)
    for i in range(w, len(bands) - w):
        before, after = bands[i - w:i].mean(axis=0), bands[i:i + w].mean(axis=0)
        out[i] = 1.0 - float(np.dot(before, after))
    return out


def boundaries(nov: np.ndarray, min_gap_s: float = 6.0) -> list[int]:
    """Novelty peaks, at least `min_gap_s` apart."""
    if len(nov) == 0:
        return []
    gap = int(min_gap_s * FPS)
    thresh = nov.mean() + 0.4 * nov.std()
    picks: list[int] = []
    for i in np.argsort(nov)[::-1]:
        if nov[i] < thresh:
            break
        if all(abs(int(i) - p) >= gap for p in picks):
            picks.append(int(i))
    return sorted(picks)


def label_for(bass: float, voice: float) -> str:
    """An indicative label, inferred from bass energy and vocal presence."""
    sung = voice > VOICE_THRESHOLD
    if bass > 0.6:
        return "drop / chorus" if sung else "instrumental drop"
    if bass < 0.2:
        return "sung intro / breakdown" if sung else "intro / breakdown"
    return "verse" if sung else "instrumental bridge"
