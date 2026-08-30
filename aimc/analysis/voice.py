"""Vocal presence and incoming bass — the two markers we look for by eye.

These are hints, not detections: the limits of each estimate are written down
with it, because trusting them further than they allow is the mistake they
invite.
"""

from __future__ import annotations

import numpy as np

from aimc.analysis.spectral import band

# The band where a lead vocal lives. Below it we catch the bass and the kick,
# which are centred too; above it, the cymbals.
VOCAL_BAND = band(300, 3500)

# Loudness must only serve to rule out silence, not to weight: multiplying by
# sqrt(loud) (median ~0.17) flattened the whole curve and no section made it
# past the threshold.
GATE_FLOOR = 0.35


def _centre_dominance(mid: np.ndarray, side: np.ndarray) -> np.ndarray:
    """Share of the signal that sits in the centre — a lead vocal survives there alone."""
    centre: np.ndarray = mid / (mid + side + 1e-9)
    return centre


def _tonality(bins: np.ndarray) -> np.ndarray:
    """A voice is harmonic: its spectrum is far from flat."""
    b = bins + 1e-9
    flat = np.exp(np.log(b).mean(axis=1)) / b.mean(axis=1)
    tonal: np.ndarray = 1.0 - np.clip(flat, 0, 1)
    return tonal


def _silence_gate(mid: np.ndarray) -> np.ndarray:
    """0 in silence, 1 as soon as something is happening."""
    loud = mid / (np.median(mid) + 1e-9)
    gate: np.ndarray = np.clip(loud / GATE_FLOOR, 0, 1)
    return gate


def vocal_curve(spec_mid: np.ndarray, spec_side: np.ndarray) -> np.ndarray:
    """Vocal presence, estimated from centre dominance in 300-3500 Hz.

    A lead vocal is almost always centred: it survives in (L+R) and disappears
    in (L-R). We restrict the measurement to the vocal band to avoid the bass
    and the kick, which are centred too.

    Limits: a mono track gives a zero `side` and therefore a maximal score
    everywhere; a synth centred in the same band will be counted as a voice.
    Read it as a hint, not a detection.
    """
    if spec_mid.shape[0] == 0:
        return np.zeros(0, np.float32)
    bins = spec_mid[:, VOCAL_BAND]
    mid = bins.sum(axis=1)
    side = (spec_side[:, VOCAL_BAND].sum(axis=1) if spec_side.shape[0]
            else np.zeros_like(mid))

    score = _centre_dominance(mid, side) * _tonality(bins) * _silence_gate(mid)
    # Robust normalisation: the 95th percentile rather than the maximum, which a
    # single peak would be enough to blow out.
    scale = np.percentile(score, 95) or 1.0
    curve: np.ndarray = np.clip(score / scale, 0, 1).astype(np.float32)
    return curve


def find_drops(low_per_s: np.ndarray, min_gap_s: int = 12) -> list[int]:
    """Seconds where the bass drops in all at once after a lull."""
    drops: list[int] = []
    for i in range(4, len(low_per_s) - 3):
        before = low_per_s[i - 4:i].mean()
        after = low_per_s[i:i + 3].mean()
        is_drop = after > 0.55 and after - before > 0.28
        if is_drop and all(abs(i - d) >= min_gap_s for d in drops):
            drops.append(i)
    return drops
