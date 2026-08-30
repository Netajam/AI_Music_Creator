"""The signal-processing foundation: decoding and spectrogram.

The whole rest of the analysis starts from these frames. The constants live
here because they hold together: changing HOP changes FPS, which changes the
frame width of every window, in the tempo as well as in the sections.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from aimc.audio import decode

SR = 22050
N_FFT = 2048
HOP = 512
FPS = SR / HOP                       # ~43 frames per second

FREQS = np.fft.rfftfreq(N_FFT, 1 / SR)


def load_stereo(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Returns (mono, side). `side` = (L-R)/2, zero if the source is mono."""
    raw = decode(path, rate=SR, channels=2)
    if not raw:
        return np.zeros(0, np.float32), np.zeros(0, np.float32)
    inter = np.frombuffer(raw, dtype=np.float32)
    inter = inter[: len(inter) // 2 * 2].reshape(-1, 2)
    left, right = inter[:, 0], inter[:, 1]
    return (left + right) / 2, (left - right) / 2


def spectrogram(x: np.ndarray) -> np.ndarray:
    if len(x) < N_FFT:
        return np.zeros((0, N_FFT // 2 + 1), np.float32)
    frames = 1 + (len(x) - N_FFT) // HOP
    win = np.hanning(N_FFT).astype(np.float32)
    out = np.empty((frames, N_FFT // 2 + 1), np.float32)
    for i in range(frames):
        out[i] = np.abs(np.fft.rfft(x[i * HOP:i * HOP + N_FFT] * win))
    return out


def band(lo: float, hi: float) -> np.ndarray:
    """Mask of the bins between `lo` and `hi` Hz — the same band, written once."""
    return (FREQS >= lo) & (FREQS < hi)
