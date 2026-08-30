""""Is this the same recording?"

The fingerprint hashes the **decoded** PCM, not the bytes of the file: the same
sound re-encoded into another container keeps the same value, whereas two takes
carrying the same name give two different ones. That is exactly the
`pouf-seed1.mp3` / `pouf-seed1.wav` mix-up (waveform correlation 0.028), which
nothing used to flag.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from aimc.audio import open_stream

# The fingerprint's decoding format. Frozen: changing it changes every
# fingerprint, and a fingerprint that can no longer be compared with the ones
# already written into the manifests is of no use at all.
#
# We decode at the original rate and channel count, as 32-bit integers.
# Resampling would make the fingerprint unstable: swresample does not cut the
# same windows depending on which decoder feeds it, and the same sound in WAV
# and in FLAC then comes out with two different values (verified). In 32 bits,
# 16- and 24-bit versions of the same signal do give the same fingerprint — bit
# depth is a property of the medium, not of the take.
FP_FORMAT = "s32le"
FP_VERSION = 1

CHUNK = 1 << 20


def audio_fingerprint(path: Path | str) -> str | None:
    """Fingerprint of the decoded audio content — independent of the container.

    Decoding before hashing is the whole point: hashing the file would make two
    encodings of the same sound into two distinct takes, when it is the sound
    that identifies a take.

    Returns `None` if the file cannot be read: a wrong fingerprint would be
    worse than no fingerprint at all.
    """
    proc = open_stream(path, FP_FORMAT)
    if proc is None or proc.stdout is None:
        return None
    h = hashlib.blake2b(digest_size=16)
    size = 0
    # The stream is captured in a variable: inside the lambda, proc.stdout
    # would go back to being IO | None as far as the type checker is concerned.
    stdout = proc.stdout
    # We hash as it streams: a 145 s WAV is 28 MB, no point holding it whole in
    # memory when the machine is already tight.
    for chunk in iter(lambda: stdout.read(CHUNK), b""):
        h.update(chunk)
        size += len(chunk)
    stdout.close()
    if proc.wait() != 0 or size == 0:
        return None
    return f"v{FP_VERSION}:{h.hexdigest()}"


def short_fingerprint(fingerprint: str | None) -> str:
    """Display form: enough digits to tell takes apart, short enough to read."""
    if not fingerprint:
        return "—"
    return fingerprint.split(":")[-1][:10]
