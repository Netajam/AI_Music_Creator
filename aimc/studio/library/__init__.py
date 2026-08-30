"""What the studio knows about the takes sitting on disk.

    paths     a file named by nothing but its name, validated
    cache     the expensive analyses, invalidated when the audio changes
    takes     the list of takes and their manifests
    measures  energy, loudness, structure, stems, fingerprint, publishability

Everything that costs a decode goes through the cache, and nothing here decides
anything: the rules live in `mastering` and `analysis`.
"""

from aimc.studio.library.measures import (
    alignment,
    code_status,
    energy_profile,
    fingerprint,
    loudness,
    readiness,
    stems,
    structure,
)
from aimc.studio.library.paths import in_dir, song_file
from aimc.studio.library.takes import manifest_kind, read_dir, read_manifest, takes

__all__ = [
    "alignment", "code_status", "energy_profile", "fingerprint", "in_dir", "loudness",
    "manifest_kind",
    "read_dir", "read_manifest", "readiness", "song_file", "stems", "structure",
    "takes",
]
