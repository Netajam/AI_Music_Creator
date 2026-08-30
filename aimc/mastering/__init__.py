"""Bringing a take up to distribution standards: measure, normalise, and say whether it can ship.

    targets   the targets and the `publishable` rule
    measure   EBU R128 and the state of the end of the track
    render    the filter chain and writing it out
    report    the JSON report the studio reads back

This package runs under the system python3, without the engine's environment:
it imports neither numpy nor acestep.
"""

from aimc.mastering.measure import tail_amplitude
from aimc.mastering.targets import (
    LUFS_TOLERANCE,
    TAIL_MAX,
    TARGET_LRA,
    TARGET_LUFS,
    TARGET_TP,
    publishable,
)

__all__ = [
    "LUFS_TOLERANCE", "TAIL_MAX", "TARGET_LRA", "TARGET_LUFS", "TARGET_TP", "publishable",
    "tail_amplitude",
]
