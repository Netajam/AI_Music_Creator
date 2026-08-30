"""Placing each lyric line in time, by forced alignment.

We do not ask the model what is being sung: we give it the text and ask it
*where* that text is. That is what makes the exercise realistic on singing,
where a transcription would get the words wrong — the text, by contrast, is
known, and the take's manifest keeps it verbatim.

What comes out is still an alignment, not a truth: the model places whatever it
is given, including a line ACE-Step never sang. The score and the pace of each
line are therefore returned alongside it, so the display can doubt them.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Any

# MMS_FA speaks an alphabet of 29 tokens: a-z, the apostrophe, and the star.
# The hyphen there is the index of the *blank* — leaving it inside a word makes
# `forced_align` fail with "targets shouldn't contain blank index". So it
# separates compound words, it is never written inside one.
UNSUPPORTED = re.compile(r"[^a-z']")
SEPARATORS = re.compile(r"[-–—/]")

# The star is a token of the model, not a trick: it absorbs the audio that
# corresponds to nothing in the text. Without it, an instrumental interlude is
# filled in by stretching the neighbouring line — measured on
# `electro-pop-pouf3`, one line sprawled from 69.3 s to 92.9 s; with the star
# between lines, the same one fits in 2.6 s.
STAR = "*"

# Window of the model pass, in seconds. Attention is quadratic in duration: a
# 185 s track computed in one go peaked at 9.2 GB, on a machine that has 16 and
# where ACE-Step already claims most of them. Chunked, the emission fits in a
# few hundred megabytes, and the alignment stays global — it is the emission we
# compute in pieces, not the alignment.
WINDOW_S = 30
# The windows overlap, and we throw away half the overlap on each side: the
# edges of a window are badly conditioned, the middle is not.
OVERLAP_S = 2

# A line sung much faster or much slower than these bounds was not placed, it
# was crammed in. The bounds are deliberately wide: they only flag the
# aberration, not the nuance — the observed median is 2 to 3.4 words/s.
MIN_PACE = 0.8
MAX_PACE = 8.0

# A line entirely in square brackets labels, it is not sung: [Chorus] just like
# [strings only].
TAG = re.compile(r"^\[[^\]]+\]$")


def normalise(word: str) -> str:
    """A word as MMS_FA can read it: lowercase, unaccented, a-z and ’.

    Accents are decomposed then removed (é → e): the model's dictionary is
    romanised, and an untreated "è" would make the whole word disappear.
    """
    w = unicodedata.normalize("NFD", word.lower())
    w = "".join(c for c in w if not unicodedata.combining(c))
    return UNSUPPORTED.sub("", w.replace("’", "'")).strip("'")


def sung_lines(text: str) -> list[dict[str, Any]]:
    """The sung lines of the text, with their number and their normalised words.

    The number is that of the line in the original text, tags included: it is
    what lets the display find the line it is showing.
    """
    out: list[dict[str, Any]] = []
    for i, raw in enumerate(text.split("\n")):
        stripped = raw.strip()
        if not stripped or TAG.match(stripped):
            continue
        words = [w for w in (normalise(w)
                             for w in SEPARATORS.sub(" ", stripped).split()) if w]
        if words:
            out.append({"line": i, "text": stripped, "words": words})
    return out


def _emission(model: Any, wave: Any, rate: int) -> Any:
    """The model's emission, computed window by window then stitched back."""
    import torch

    step, over = WINDOW_S * rate, OVERLAP_S * rate
    total = wave.shape[1]
    # The model produces one frame every 20 ms: this ratio is what lets us cut
    # the overlap in frames rather than in samples.
    pieces = []
    at = 0
    with torch.inference_mode():
        while at < total:
            start = max(0, at - over)
            stop = min(total, at + step + over)
            chunk, _ = model(wave[:, start:stop])
            per_frame = (stop - start) / chunk.shape[1]
            head = 0 if start == 0 else int(round((at - start) / per_frame))
            tail = (chunk.shape[1] if stop == total
                    else int(round((min(at + step, total) - start) / per_frame)))
            pieces.append(chunk[:, head:tail])
            at += step
    return torch.cat(pieces, dim=1)


def align(audio: Path, text: str) -> dict[str, Any]:
    """Every sung line of the text, placed within the track.

    Returns a JSON payload: the lines with their start, their end, their mean
    score and a `suspect` flag, plus what it takes to know which text the
    alignment was done against.
    """
    # Deferred imports: torch weighs more than a gigabyte in memory, and nothing
    # else in `analysis` needs it. The studio should only pay for it when an
    # alignment is actually asked for.
    import numpy as np
    import torch
    import torchaudio

    from aimc.audio import decode

    lines = sung_lines(text)
    if not lines:
        return {"error": "no sung line in these lyrics", "lines": []}

    bundle = torchaudio.pipelines.MMS_FA
    rate = bundle.sample_rate
    raw = decode(audio, rate=rate, channels=1)
    samples = np.frombuffer(raw, dtype=np.float32)
    if samples.size == 0:
        return {"error": "unreadable audio", "lines": []}
    wave = torch.from_numpy(samples.copy()).unsqueeze(0)

    # A star before each line and one at the end: all the audio that is none of
    # these lines now has somewhere to go.
    tokens: list[str] = []
    for ln in lines:
        tokens.append(STAR)
        tokens += ln["words"]
    tokens.append(STAR)

    model = bundle.get_model()
    emission = _emission(model, wave, rate)
    spans = bundle.get_aligner()(emission[0], bundle.get_tokenizer()(tokens))
    seconds = wave.shape[1] / emission.shape[1] / rate

    at = 0
    for ln in lines:
        at += 1                                   # the preceding star
        got = spans[at:at + len(ln["words"])]
        at += len(ln["words"])
        start = got[0][0].start * seconds
        end = got[-1][-1].end * seconds
        score = (sum(t.score for word in got for t in word)
                 / sum(len(word) for word in got))
        pace = len(ln["words"]) / max(end - start, 1e-3)
        ln.update(start=round(start, 2), end=round(end, 2), score=round(score, 3),
                  suspect=not (MIN_PACE <= pace <= MAX_PACE))
        del ln["words"]

    return {
        "lines": lines,
        "duration": round(wave.shape[1] / rate, 2),
        "model": "MMS_FA",
        # The cache is keyed on the audio, never on the text: without this
        # digest, a rewritten manifest would be served the old one's alignment.
        "lyrics_digest": lyrics_digest(text),
    }


def lyrics_digest(text: str) -> str:
    """What it takes to recognise the text an alignment was made against."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
