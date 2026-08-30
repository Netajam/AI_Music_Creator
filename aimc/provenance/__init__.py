"""The identity of a take: what it contains, and the code that produced it.

Two fingerprints, two different questions. `audio_fingerprint` answers "is this
the same recording?", `compare_code` answers "is this the code that produced
this take?". `manifest_for` finds a take's settings file without being fooled by
a namesake.

Nothing but the standard library, ffmpeg and git: this package is imported both
by generation (inside the engine's environment) and by the studio.
"""

from aimc.provenance.code import code_fingerprint, compare_code
from aimc.provenance.fingerprint import audio_fingerprint, short_fingerprint
from aimc.provenance.manifest import manifest_for

__all__ = [
    "audio_fingerprint", "code_fingerprint", "compare_code", "manifest_for", "short_fingerprint",
]
