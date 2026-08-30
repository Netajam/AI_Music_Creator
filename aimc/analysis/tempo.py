"""The tempo, by autocorrelation of the spectral flux."""

from __future__ import annotations

import numpy as np

from aimc.analysis.spectral import FPS


def onset_flux(spec: np.ndarray) -> np.ndarray:
    if spec.shape[0] < 2:
        return np.zeros(0, np.float32)
    flux: np.ndarray = np.maximum(0, np.diff(spec, axis=0)).sum(axis=1)
    return flux


def fold_tempo(bpm: float, lo: float = 85.0, hi: float = 170.0) -> float:
    """Bring a tempo into a musical range by doubling or halving it.

    Autocorrelation happily locks onto the half-bar: a track at 126 BPM comes
    out at 63. Since 63 and 126 describe the same pulse, we pick the octave that
    falls in the range where dance music lives.
    """
    if bpm <= 0:
        return 0.0
    while bpm < lo:
        bpm *= 2
    while bpm > hi:
        bpm /= 2
    # float() is essential: bpm comes from an np.arange, and an np.float64
    # (like the np.bool_ from a comparison) makes json.dumps fail.
    return round(float(bpm), 1)


# Below ~12 s, autocorrelation does not have enough periods to decide: it
# returns a plausible but arbitrary figure (we saw 167 then 96 BPM on two
# neighbouring sections of a track at 126). Better to announce nothing than to
# announce something wrong.
MIN_SECONDS = 12


def tempo_of(flux: np.ndarray, lo: float = 50, hi: float = 200) -> float:
    """BPM by autocorrelation of the spectral flux, folded by octave.

    The search range is deliberately wide: restricting it to 70-180 made it miss
    the real period (63 BPM on a track at 126) and return the best candidate *in
    the range*, that is, a wrong but plausible value. Better to find the real
    period and then fold it.
    """
    if len(flux) < int(FPS * MIN_SECONDS):
        return 0.0
    f = flux - flux.mean()
    if not f.any():
        return 0.0
    ac = np.correlate(f, f, mode="full")[len(f) - 1:]
    best, best_bpm = 0.0, 0.0
    for bpm in np.arange(lo, hi + 0.5, 0.5):
        lag = int(round(FPS * 60.0 / bpm))
        if 1 <= lag < len(ac) and ac[lag] > best:
            best, best_bpm = float(ac[lag]), float(bpm)
    return fold_tempo(best_bpm)
