"""What is actually playing, by pulling the mix apart into four stems.

The rest of `analysis` measures bands: it can say that something is loud below
150 Hz, never whether that is a kick, a bass line, or both at once. Naming what
plays is not a thing a band split can do, and no threshold on a spectrum will
turn it into one.

So this module asks a model instead — Hybrid Demucs, through the pipeline
torchaudio already ships (`HDEMUCS_HIGH_MUSDB_PLUS`, 320 MB, 83.6 M
parameters). It is the only part of the analysis that is not signal processing,
and it is deliberately the only one: it buys the one thing signal processing
cannot give.

Four sources, and they are the model's, not ours: drums, bass, vocals, and
`other` — everything harmonic that is neither bass nor voice, which is to say
guitars, keys, pads and strings all in the same bag. The model was trained on
MUSDB, four stems, and it cannot name a guitar. Asking it which instrument
plays in `other` would be asking a question it has no vocabulary for.

`aimc.analysis.tags` supplies that vocabulary, and takes part in this pass
rather than making one of its own: `analyse(..., tag=True)` tags each `other`
chunk on its way past, in the one place it exists. What it can honestly say is
narrower than a name — read its docstring before believing a family.

We keep no audio. Each chunk is separated, reduced to one energy figure per
second per source, and thrown away: what comes back is four curves and a
verdict, a few kilobytes rather than four times the weight of the take.

Memory: the model, plus one twelve-second chunk of activations. Measured under
2 GB on the target machine — small next to a generation, and still too much to
sit beside one. The studio therefore runs it as a subprocess, like the
alignment, and refuses to start it while ACE-Step holds the machine. With
`tag=True` the tagger's 350 MB sits alongside for the length of the pass.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple

MODEL = "HDEMUCS_HIGH_MUSDB_PLUS"

# One curve per source, a value per second. Named because it is passed around
# three times and `dict[str, list[float]]` says nothing about which is which.
Energy = dict[str, list[float]]

# The model's rate, and not a choice of ours: the bundle declares 44.1 kHz and
# feeding it anything else would resample inside a network trained without one.
SR = 44100

# The audio is separated in chunks: attention aside, a whole track's activations
# do not fit in what is left of 16 GB. `MARGIN_S` is decoded and separated but
# thrown away on each side — the edges of a chunk are where the network has no
# context, and a discarded margin is cheaper to reason about than a crossfade,
# which would have to be undone before the energy per second could be summed.
CHUNK_S = 10
MARGIN_S = 1

# A source counts as playing when it holds this share of the energy for this
# many seconds. Both are thresholds on an always-four-way split: Demucs returns
# four stems whatever it is given, and a track with no bass gets a bass stem all
# the same. The verdict is what separates that residue from an instrument.
#
# Calibrated against a negative, since no take in `songs/` is instrumental and
# the positives alone would say nothing about where the line goes. Two were
# built from `babylon-reggae-seed7` by filtering out one family and leaving the
# rest real music: high-passed twice at 300 Hz, the bass stem came back at
# exactly 0.000 for all 90 seconds; low-passed twice at 500 Hz, the vocals stem
# did the same. Against that, the *weakest* genuinely playing source measured —
# `other` on the same reggae take — held 0.081 on average and cleared 0.10 for
# 55 seconds. The gap either side of these two numbers is most of the scale.
#
# Measured across four takes (reggae, techno, two Italian pop): drums 0.34–0.46,
# vocals 0.21–0.39, bass 0.19–0.25, other 0.08–0.19.
#
# What the calibration does not cover: a filtered negative is a clean one, with
# literally nothing left for the model to put in that stem. A real track that
# simply has no guitar still leaves the `other` stem full of bleed from the
# three that do play, and that residue is larger than zero by an unknown amount.
# Read a verdict of "absent" as solid and one of "present" as the weaker claim.
#
# A first attempt calibrated on synthetic probes instead — a pure 55 Hz sine for
# a bass line, pink noise bursts for a kit — and they are recorded here as the
# dead end they were: Demucs put the whole sine in `drums`, not in `bass`. A
# sine is not a bass line, and a model asked something outside what it was
# trained on answers confidently anyway.
PRESENT_SHARE = 0.10
PRESENT_SECONDS = 8


def _load(path: Path) -> tuple[Any, int]:
    """The track as a (2, samples) tensor at the model's rate."""
    import numpy as np
    import torch

    from aimc.audio import decode

    raw = decode(path, rate=SR, channels=2)
    if not raw:
        return None, 0
    inter = np.frombuffer(raw, dtype=np.float32)
    inter = inter[: len(inter) // 2 * 2].reshape(-1, 2)
    wave = torch.from_numpy(inter.T.copy())
    return wave, wave.shape[1]


def _per_second(chunk: Any, sr: int = SR) -> list[float]:
    """Mean energy (amplitude squared) of each whole second of a stem chunk."""
    import torch

    usable = chunk.shape[-1] // sr * sr
    if usable == 0:
        return []
    seconds = chunk[..., :usable].reshape(chunk.shape[0], -1, sr)
    return [float(v) for v in torch.mean(seconds ** 2, dim=(0, 2))]


class Separation(NamedTuple):
    """What one pass over the audio produced.

    A tuple of five was the alternative, and three of the five would have been
    empty whenever the tagger was not asked for — which is most of the time.
    """

    sources: list[str]
    energy: Energy
    duration: float
    # One array of 527 label scores per chunk, or empty when no tagger was
    # passed: the `other` stem for the instruments, the untouched mix for the
    # genres. Kept as scores and not as a verdict because `tags.summarise` is
    # what turns them into one, and it has no business running inside the loop.
    stem_scores: list[Any]
    mix_scores: list[Any]


def _separate(path: Path, log: Callable[[str], None],
              tagger: Any = None) -> Separation:
    """Energy per second per source, chunk by chunk, keeping no audio.

    When `tagger` is given, each chunk is also tagged before it is discarded —
    here rather than in a pass of its own, because this is the one place where
    the separated `other` exists, and re-deriving it would mean paying for the
    whole separation twice.
    """
    import torch
    from torchaudio.pipelines import HDEMUCS_HIGH_MUSDB_PLUS

    wave, total = _load(path)
    if wave is None or total == 0:
        return Separation([], {}, 0.0, [], [])

    model = HDEMUCS_HIGH_MUSDB_PLUS.get_model()
    model.eval()
    sources: list[str] = list(model.sources)
    energy: Energy = {s: [] for s in sources}
    stem_scores: list[Any] = []
    mix_scores: list[Any] = []

    # Demucs was trained on normalised input, and normalises against the whole
    # track rather than the chunk: the same passage must not be scaled
    # differently depending on which chunk it landed in.
    ref = wave.mean(0)
    mean, std = float(ref.mean()), float(ref.std()) or 1.0

    margin, step = MARGIN_S * SR, CHUNK_S * SR
    done = 0
    with torch.no_grad():
        for start in range(0, total, step):
            a, b = max(0, start - margin), min(total, start + step + margin)
            chunk = (wave[:, a:b] - mean) / std
            out = model(chunk.unsqueeze(0))[0]        # (source, channel, sample)
            # Back to the part of the chunk that was actually asked for: the
            # margins were separated for context only.
            head, tail = start - a, min(step, total - start)
            for name, stem in zip(sources, out, strict=True):
                energy[name] += _per_second(stem[:, head:head + tail])
            if tagger is not None and tail >= SR // 4:
                # Back to the original amplitude first. The model was fed
                # (wave - mean)/std, so its stems come out in that normalised
                # domain, and handing them to the tagger as they are would put
                # the stem and the mix on two different scales — every
                # difference between the two readings could then be loudness.
                other = next(s for n, s in zip(sources, out, strict=True)
                             if n == "other")
                stem_scores.append(tagger.scores(
                    other[:, head:head + tail].mean(0) * std, SR))
                mix_scores.append(tagger.scores(
                    wave[:, start:start + tail].mean(0), SR))
            del out, chunk
            done = min(total, start + step)
            log(f"  separated {done // SR}s / {total // SR}s")
    return Separation(sources, energy, total / SR, stem_scores, mix_scores)


def analyse(path: Path, log: Callable[[str], None] = lambda _: None,
            tag: bool = False) -> dict[str, Any]:
    """The four stems of a track, as presence curves and a verdict.

    `log` is called once per chunk: the studio shows this while it waits, and a
    separation that says nothing for two minutes looks like one that has hung.

    With `tag`, the same pass also asks `aimc.analysis.tags` what is playing
    inside `other` and what genre the mix sounds like — a second model and a
    second forward pass per chunk, on audio that has already been separated.
    Without it, nothing here loads the tagger and the result carries no `tags`.
    """
    tagger = None
    if tag:
        from aimc.analysis.tags import Tagger

        log("  loading the tagger")
        tagger = Tagger()

    sep = _separate(path, log, tagger)
    if not sep.sources:
        return {"error": "audio unreadable or empty"}

    # Truncated to the shortest: the last chunk can be a fraction of a second
    # short of the others, and a curve one point longer than its neighbours
    # would misplace everything drawn against it.
    n = min((len(v) for v in sep.energy.values()), default=0)
    shares = _shares(sep.sources, sep.energy, n)
    out: dict[str, Any] = {
        "model": MODEL,
        "sources": sep.sources,
        "duration": round(sep.duration, 2),
        "per_second": {s: [round(v, 4) for v in shares[s]] for s in sep.sources},
        "presence": {s: _presence(shares[s]) for s in sep.sources},
    }
    if tagger is not None:
        from aimc.analysis.tags import summarise

        out["tags"] = summarise(tagger, sep.stem_scores, sep.mix_scores)
    return out


def _shares(sources: list[str], energy: Energy, n: int) -> Energy:
    """Each source's share of the energy, second by second — four numbers summing to 1.

    Shares rather than levels, for the same reason as the balance strip: what is
    being asked is what the second is made of, and a level would say a second
    time how loud it is. A second with no energy at all gets four zeros.
    """
    out: Energy = {s: [] for s in sources}
    for i in range(n):
        total = sum(energy[s][i] for s in sources)
        for s in sources:
            out[s].append(0.0 if total <= 0 else energy[s][i] / total)
    return out


def _presence(share: list[float]) -> dict[str, Any]:
    """Is this source playing, and how much of the track does it hold?

    The numbers it stands on are returned with it: a verdict from two thresholds
    is worth exactly what the reader can check.
    """
    seconds = sum(1 for v in share if v >= PRESENT_SHARE)
    return {
        "present": seconds >= PRESENT_SECONDS,
        "seconds": seconds,
        "share": round(sum(share) / len(share), 4) if share else 0.0,
        "peak": round(max(share), 4) if share else 0.0,
    }
